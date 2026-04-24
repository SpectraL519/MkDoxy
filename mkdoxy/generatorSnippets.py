import logging
import pathlib
import re

import yaml
from mkdocs.structure import pages

from mkdoxy.doxygen import Doxygen
from mkdoxy.finder import Finder
from mkdoxy.generatorBase import GeneratorBase
from mkdoxy.node import Node

log: logging.Logger = logging.getLogger("mkdocs")

regexIncorrect = r"(?s)(?<!```yaml\n)(^::: doxy)(\.(?P<project>[a-zA-Z0-9_]+))?[\.]?[\s]*\n(?P<yaml>.*?)\s*\n(?:(?=\n)|(?=:::)|\Z)"  # https://regex101.com/r/IYl25b/2  # noqa: E501
regexLong = r"(?s)(?<!```yaml\n)(^::: doxy\.(?P<project>[a-zA-Z0-9_]+)\.(?P<argument>[a-zA-Z0-9_.]+))\s*\n(?P<yaml>.*?)(?:(?:(?:\r*\n)(?=\n))|(?=:::)|`|\Z)"  # https://regex101.com/r/lIgOij/4  # noqa: E501
regexShort = r"(?s)(?<!```yaml\n)(^::: doxy\.(?P<project>[a-zA-Z0-9_]+)\.(?P<argument>[a-zA-Z0-9_.]+))\s*\n(?:(?=\n)|(?=:::)|\Z)"  # https://regex101.com/r/QnqxRc/2  # noqa: E501


class GeneratorSnippets:
    def __init__(
        self,
        markdown: str,
        generatorBase: dict[str, GeneratorBase],
        doxygen: dict[str, Doxygen],
        projects: dict[str, dict[str, any]],
        useDirectoryUrls: bool,
        page: pages.Page,
        config: dict,
        debug: bool = False,
    ):
        self.markdown = markdown
        self.generatorBase = generatorBase
        self.doxygen = doxygen
        self.projects = projects
        self.useDirectoryUrls = useDirectoryUrls
        self.page = page
        self.config = config
        self.debug = debug
        self.finder = Finder(doxygen, debug)

        self.doxy_arguments = {
            "code": self.doxyCode,
            "function": self.doxyFunction,
            "namespace.function": self.doxyNamespaceFunction,
            "class": self.doxyClass,
            "class.method": self.doxyClassMethod,
            "class.list": self.doxyClassList,
            "class.index": self.doxyClassIndex,
            "class.hierarchy": self.doxyClassHierarchy,
            "namespace.list": self.doxyNamespaceList,
            "concept": self.doxyConcept,
            "concept.list": self.doxyConceptList,
            "file.list": self.doxyFileList,
        }

        # fix absolute path
        path = pathlib.PurePath(self.page.url).parts
        self.pageUrlPrefix = "".join("../" for _ in range(len(path) - 1))

    def generate(self):
        if self.is_doxy_inactive(self.config):
            return self.markdown  # doxygen is inactive return unchanged markdown

        try:
            matches = re.finditer(regexIncorrect, self.markdown, re.MULTILINE)
            for match in reversed(list(matches)):
                snippet = match.group()
                project_name = match.group("project") or "<project_name>"

                snippet_config = self.config.copy()
                snippet_config.update(self.try_load_yaml(match.group("yaml"), project_name, snippet, self.config))

                if self.is_doxy_inactive(snippet_config):
                    continue

                replacement = (
                    self.incorrect_argument(project_name, "", snippet_config, snippet)
                    if self.is_project_exist(project_name)
                    else self.incorrect_project(project_name, snippet_config, snippet)
                )
                self.replace_markdown(match.start(), match.end(), replacement)

            matches = re.finditer(regexShort, self.markdown, re.MULTILINE)
            for match in reversed(list(matches)):
                snippet = match.group()
                argument = match.group("argument").lower()
                project_name = match.group("project")

                snippet_config = self.config.copy()
                snippet_config.update(self.try_load_yaml(match.group("yaml"), project_name, snippet, self.config))

                if self.is_doxy_inactive(snippet_config):
                    continue

                replaceStr = self.call_doxy_by_name(snippet, project_name, argument, snippet_config)
                self.replace_markdown(match.start(), match.end(), replaceStr)

            matches = re.finditer(regexLong, self.markdown, re.MULTILINE)
            for match in reversed(list(matches)):
                snippet = match.group()
                argument = match.group("argument").lower()
                project_name = match.group("project")
                # log.debug(f"\nArgument: {argument}")

                # config has been updated by yaml
                snippet_config = self.config.copy()
                snippet_config.update(self.try_load_yaml(match.group("yaml"), project_name, snippet, self.config))

                replaceStr = self.call_doxy_by_name(snippet, project_name, argument, snippet_config)
                self.replace_markdown(match.start(), match.end(), replaceStr)
            return self.markdown
        except Exception as e:
            basename = pathlib.Path(__file__).name
            log.error(f"Error in {self.page.url} page. Incorrect doxy snippet or error in file {basename}")
            log.error(f"Error: {e}")
            return self.markdown

    def try_load_yaml(self, yaml_raw: str, project: str, snippet: str, config: dict) -> dict:
        try:
            return yaml.safe_load(yaml_raw)
        except yaml.YAMLError:
            log.error(f"YAML error in {project} project on page {self.page.url}")
            self.doxyError(
                project,
                config,
                "YAML error",
                "Check your YAML syntax",
                "YAML snippet:",
                yaml_raw,
                "yaml",
                snippet,
            )
            return {}

    def incorrect_project(
        self,
        project: str,
        config: dict,
        snippet: str,
    ) -> str:
        return self.doxyError(
            project,
            config,
            f"Incorrect project name: {project}",
            "Project name have to contain [a-zA-Z0-9_]",
            "A list of available projects:",
            "\n".join(self.projects.keys()),
            "yaml",
            snippet,
        )

    def incorrect_argument(self, project: str, argument: str, config: dict, snippet: str) -> str:
        return self.doxyError(
            project,
            config,
            f"Incorrect argument: {argument}" if argument else f"Add argument to snippet: {project}",
            f"Argument have to be based on this diagram → **:::doxy.{project}.<argument\\>**",
            "A list of available arguments:",
            "\n".join(self.doxy_arguments.keys()),
            "yaml",
            snippet,
        )

    def replace_markdown(self, start: int, end: int, replacement: str):
        self.markdown = self.markdown[:start] + replacement + "\n" + self.markdown[end:]

    def _setLinkPrefixNode(self, node: Node, linkPrefix: str):
        node.project.linkPrefix = linkPrefix

    def _setLinkPrefixNodes(self, nodes: list[Node], linkPrefix: str):
        if nodes:
            nodes[0].project.linkPrefix = linkPrefix

    def is_project_exist(self, project: str):
        return project in self.projects

    def is_doxy_inactive(self, config: dict):
        return config.get("disable_doxy_snippets", False)

    def call_doxy_by_name(self, snippet, project: str, argument: str, config: dict) -> str:
        if argument not in self.doxy_arguments:
            return self.incorrect_argument(project, argument, config, snippet)
        callback = self.doxy_arguments[argument]
        return callback(snippet, project, config)

    def checkConfig(self, snippet, project: str, config, required_params: [str]) -> bool:
        """
        returns false if config is correct
        return error message if project not exist or find problem in config
        """
        return next(
            (
                self.doxyError(
                    project,
                    config,
                    f"Missing parameter: {param}",
                    "This parameter is required",
                    "Required parameters:",
                    "\n".join(required_params),
                    "yaml",
                    snippet,
                )
                for param in required_params
                if not config.get(param)
            ),
            False,
        )

    ### Create documentation generator callbacks

    def doxyError(
        self,
        project,
        config: dict,
        title: str,
        description: str,
        code_header: str = "",
        code: str = "",
        code_language: str = "",
        snippet_code: str = "",
    ) -> str:
        log.error(f"  -> {title} -> page: {self.page.canonical_url}")
        if project not in self.projects:
            project = list(self.projects)[0]
        return self.generatorBase[project].error(
            config, title, description, code_header, code, code_language, snippet_code
        )

    def doxyCode(self, snippet, project: str, config):
        errorMsg = self.checkConfig(snippet, project, config, ["file"])
        if errorMsg:
            return errorMsg
        node = self.finder.doxyCode(project, config.get("file"))
        if node is None:
            return self.doxyNodeIsNone(project, config, snippet)

        if isinstance(node, Node):
            progCode = self.codeStrip(
                node.programlisting,
                node.code_language,
                config.get("start", 1),
                config.get("end", 0),
            )
            if progCode is False:
                return self.doxyError(
                    project,
                    config,
                    f"Parameter start: {config.get('start')} is greater than end: {config.get('end')}",
                    f"{snippet}",
                    "yaml",
                )
            self._setLinkPrefixNode(node, self.pageUrlPrefix + project + "/")
            return self.generatorBase[project].code(node, config, progCode)
        return self.doxyError(
            project,
            config,
            f"Did not find File: `{config.get('file')}`",
            "Check your file name",
            f"Available files in {project} project:",
            "\n".join(node),
            "yaml",
            snippet,
        )

    def codeStrip(self, codeRaw, codeLanguage: str, start: int = 1, end: int = None):
        lines = codeRaw.split("\n")

        if end and start > end:
            return False

        out = "".join(line + "\n" for num, line in enumerate(lines) if num >= start and (num <= end or end == 0))
        return f"```{codeLanguage} linenums='{start}'\n{out}```"

    def doxyFunction(self, snippet, project: str, config: dict):
        errorMsg = self.checkConfig(snippet, project, config, ["name"])
        if errorMsg:
            return errorMsg

        node = self.finder.doxyFunction(project, config.get("name"))
        if node is None:
            return self.doxyNodeIsNone(project, config, snippet)

        if isinstance(node, Node):
            self._setLinkPrefixNode(node, self.pageUrlPrefix + project + "/")
            return self.generatorBase[project].function(node, config)
        return self.doxyError(
            project,
            config,
            "Incorrect function configuration",
            f"Did not find Function with name: `{config.get('name')}`",
            "Available functions:",
            "\n".join(node),
            "yaml",
            snippet,
        )

    def doxyClass(self, snippet, project: str, config: dict):
        errorMsg = self.checkConfig(snippet, project, config, ["name"])
        if errorMsg:
            return errorMsg

        node = self.finder.doxyClass(project, config.get("name"))
        if node is None:
            return self.doxyNodeIsNone(project, config, snippet)

        if isinstance(node, Node):
            self._setLinkPrefixNode(node, self.pageUrlPrefix + project + "/")
            return self.generatorBase[project].member(node, config)
        return self.doxyError(
            project,
            config,
            "Incorrect class configuration",
            f"Did not find Class with name: `{config.get('name')}`",
            "Available classes:",
            "\n".join(node),
            "yaml",
            snippet,
        )

    def doxyClassMethod(self, snippet, project: str, config):
        errorMsg = self.checkConfig(snippet, project, config, ["name", "method"])
        if errorMsg:
            return errorMsg

        node = self.finder.doxyClassMethod(project, config.get("name"), config.get("method"))
        if node is None:
            return self.doxyNodeIsNone(project, config, snippet)

        if isinstance(node, Node):
            self._setLinkPrefixNode(node, self.pageUrlPrefix + project + "/")
            return self.generatorBase[project].function(node, config)
        return self.doxyError(
            project,
            config,
            "Incorrect class method configuration",
            f"Did not find Class with name: `{config.get('name')}` and method: `{config.get('method')}`",
            "Available classes and methods:",
            "\n".join(node),
            "yaml",
            snippet,
        )

    def doxyClassList(self, snippet, project: str, config):
        errorMsg = self.checkConfig(snippet, project, config, [])
        if errorMsg:
            return errorMsg
        nodes = self.doxygen[project].root.children
        self._setLinkPrefixNodes(nodes, self.pageUrlPrefix + project + "/")
        return self.generatorBase[project].annotated(nodes, config)

    def doxyClassIndex(self, snippet, project: str, config):
        errorMsg = self.checkConfig(snippet, project, config, [])
        if errorMsg:
            return errorMsg
        nodes = self.doxygen[project].root.children
        self._setLinkPrefixNodes(nodes, self.pageUrlPrefix + project + "/")
        return self.generatorBase[project].classes(nodes, config)

    def doxyClassHierarchy(self, snippet, project: str, config):
        errorMsg = self.checkConfig(snippet, project, config, [])
        if errorMsg:
            return errorMsg
        nodes = self.doxygen[project].root.children
        self._setLinkPrefixNodes(nodes, self.pageUrlPrefix + project + "/")
        return self.generatorBase[project].hierarchy(nodes, config)

    def doxyNamespaceList(self, snippet, project: str, config):
        errorMsg = self.checkConfig(snippet, project, config, [])
        if errorMsg:
            return errorMsg
        nodes = self.doxygen[project].root.children
        self._setLinkPrefixNodes(nodes, self.pageUrlPrefix + project + "/")
        return self.generatorBase[project].namespaces(nodes, config)

    def doxyNamespaceFunction(self, snippet, project: str, config):
        errorMsg = self.checkConfig(snippet, project, config, ["namespace", "name"])
        if errorMsg:
            return errorMsg

        node = self.finder.doxyNamespaceFunction(project, config.get("namespace"), config.get("name"))
        if node is None:
            return self.doxyNodeIsNone(project, config, snippet)

        if isinstance(node, Node):
            self._setLinkPrefixNode(node, self.pageUrlPrefix + project + "/")
            return self.generatorBase[project].function(node, config)
        return self.doxyError(
            project,
            config,
            "Incorrect namespace function configuration",
            f"Did not find Namespace with name: `{config.get('namespace')}` and function: `{config.get('name')}`",
            "Available classes and methods:",
            "\n".join(node),
            "yaml",
            snippet,
        )

    def doxyFileList(self, snippet, project: str, config):
        errorMsg = self.checkConfig(snippet, project, config, [])
        if errorMsg:
            return errorMsg
        nodes = self.doxygen[project].files.children
        self._setLinkPrefixNodes(nodes, self.pageUrlPrefix + project + "/")
        return self.generatorBase[project].fileindex(nodes, config)

    def doxyConcept(self, snippet, project: str, config: dict):
        errorMsg = self.checkConfig(snippet, project, config, ["name"])
        if errorMsg:
            return errorMsg

        node = self.finder.doxyConcept(project, config.get("name"))
        if node is None:
            return self.doxyNodeIsNone(project, config, snippet)

        if isinstance(node, Node):
            self._setLinkPrefixNode(node, self.pageUrlPrefix + project + "/")
            return self.generatorBase[project].member(node, config)
        return self.doxyError(
            project,
            config,
            "Incorrect concept configuration",
            f"Did not find Concept with name: `{config.get('name')}`",
            "Available concepts:",
            "\n".join(node),
            "yaml",
            snippet,
        )

    def doxyConceptList(self, snippet, project: str, config):
        errorMsg = self.checkConfig(snippet, project, config, [])
        if errorMsg:
            return errorMsg

        # Build a combined list: namespaces with concepts + top-level concepts
        doxy = self.doxygen[project]
        namespaced_refids: set = set()

        def _collect_from_ns(nodes):
            for n in nodes:
                if n.is_concept:
                    namespaced_refids.add(n.refid)
                if n.is_namespace:
                    _collect_from_ns(n.children)

        def _has_concepts(node):
            for child in node.children:
                if child.is_concept:
                    return True
                if child.is_namespace and _has_concepts(child):
                    return True
            return False

        def _find_ns_by_name(name, search_nodes=None):
            if search_nodes is None:
                search_nodes = doxy.root.children
            for n in search_nodes:
                if n.is_namespace and n.name_long == name:
                    return n
                if n.is_namespace:
                    found = _find_ns_by_name(name, n.children)
                    if found:
                        return found
            return None

        for n in doxy.root.children:
            if n.is_namespace:
                _collect_from_ns(n.children)

        if namespaced_refids:
            # Doxygen < 1.9.5: namespaces already have concept children
            top_level = [c for c in doxy.concepts.children if c.refid not in namespaced_refids]
            ns_with_concepts = [n for n in doxy.root.children if n.is_namespace and _has_concepts(n)]
            nodes = ns_with_concepts + top_level
        else:
            # Doxygen >= 1.9.5: match concepts to namespaces by FQN
            top_level = []
            ns_concepts = {}
            for c in doxy.concepts.children:
                name = c.name_long or c.name or ""
                if "::" in name:
                    ns_name = name.rsplit("::", 1)[0]
                    ns_concepts.setdefault(ns_name, []).append(c)
                else:
                    top_level.append(c)

            ns_nodes = []
            processed_ns = set()
            for ns_name, concepts in ns_concepts.items():
                ns_node = _find_ns_by_name(ns_name)
                if ns_node and ns_node.refid not in processed_ns:
                    existing_refids = {ch.refid for ch in ns_node.children if ch.is_concept}
                    for c in concepts:
                        if c.refid not in existing_refids:
                            ns_node.add_child(c)
                    processed_ns.add(ns_node.refid)
                    top_ns = ns_node
                    while top_ns._parent and top_ns._parent.is_namespace:
                        top_ns = top_ns._parent
                    if top_ns.refid not in {n.refid for n in ns_nodes}:
                        ns_nodes.append(top_ns)
                else:
                    top_level.extend(concepts)
            nodes = ns_nodes + top_level

        self._setLinkPrefixNodes(nodes, self.pageUrlPrefix + project + "/")
        return self.generatorBase[project].concepts(nodes, config)

    def doxyNodeIsNone(self, project: str, config: dict, snippet: str) -> str:
        return self.doxyError(
            project,
            config,
            f"Could not find coresponding snippet for project {project}",
            f"Config: {config}",
            "yaml",
            snippet,
        )


### Create documentation generator callbacks END


class SnippetClass:
    def __init__(self, config):
        self.config = config

    def default(self):
        return ""
