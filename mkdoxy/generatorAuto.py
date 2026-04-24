import logging
import os

from mkdocs.structure import files

from mkdoxy.constants import Kind
from mkdoxy.doxygen import Doxygen
from mkdoxy.generatorBase import GeneratorBase
from mkdoxy.node import Node

log: logging.Logger = logging.getLogger("mkdocs")

ADDITIONAL_FILES = {
    "Namespace ListNamespace List": "namespaces.md",
    "Namespace Members": "namespace_members.md",
    "Namespace Member Functions": "namespace_member_functions.md",
    "Namespace Member Variables": "namespace_member_variables.md",
    "Namespace Member Typedefs": "namespace_member_typedefs.md",
    "Namespace Member Enumerations": "namespace_member_enums.md",
    "Class Index": "classes.md",
    "Class Hierarchy": "hierarchy.md",
    "Class Members": "class_members.md",
    "Class Member Functions": "class_member_functions.md",
    "Class Member Variables": "class_member_variables.md",
    "Class Member Typedefs": "class_member_typedefs.md",
    "Class Member Enumerations": "class_member_enums.md",
}


def generate_link(name, url, end="\n") -> str:
    def normalize(name):
        return "\\" + name if name.startswith("__") else name

    return f"- [{normalize(name)}]({url}){end}"


# def generate_link(name, url) -> str:
# 	return f"\t\t- '{name}': '{url}'\n"


class GeneratorAuto:
    def __init__(
        self,
        generatorBase: GeneratorBase,
        tempDoxyDir: str,
        siteDir: str,
        apiPath: str,
        doxygen: Doxygen,
        useDirectoryUrls: bool,
    ):
        self.generatorBase = generatorBase
        self.tempDoxyDir = tempDoxyDir
        self.siteDir = siteDir
        self.apiPath = apiPath
        self.doxygen = doxygen
        self.useDirectoryUrls = useDirectoryUrls
        self.fullDocFiles = []
        self.debug = generatorBase.debug
        os.makedirs(os.path.join(self.tempDoxyDir, self.apiPath), exist_ok=True)

    def save(self, path: str, output: str):
        pathRel = os.path.join(self.apiPath, path)
        self.fullDocFiles.append(files.File(pathRel, self.tempDoxyDir, self.siteDir, self.useDirectoryUrls))
        with open(os.path.join(self.tempDoxyDir, pathRel), "w", encoding="utf-8") as file:
            file.write(output)

    def fullDoc(self, defaultTemplateConfig: dict):
        self.annotated(self.doxygen.root.children, defaultTemplateConfig)
        self.fileindex(self.doxygen.files.children, defaultTemplateConfig)
        self.members(self.doxygen.root.children, defaultTemplateConfig)
        self.members(self.doxygen.groups.children, defaultTemplateConfig)
        self.files(self.doxygen.files.children, defaultTemplateConfig)
        self.namespaces(self.doxygen.root.children, defaultTemplateConfig)
        self.classes(self.doxygen.root.children, defaultTemplateConfig)
        self.hierarchy(self.doxygen.root.children, defaultTemplateConfig)
        self.concepts_page(defaultTemplateConfig)
        self.concept_members(self.doxygen.concepts.children, defaultTemplateConfig)
        self.modules(self.doxygen.groups.children, defaultTemplateConfig)
        self.pages(self.doxygen.pages.children, defaultTemplateConfig)
        # self.examples(self.doxygen.examples.children) # TODO examples
        self.relatedpages(self.doxygen.pages.children)
        self.index(
            self.doxygen.root.children,
            [Kind.FUNCTION, Kind.VARIABLE, Kind.TYPEDEF, Kind.ENUM],
            [Kind.CLASS, Kind.STRUCT, Kind.INTERFACE],
            "Class Members",
            defaultTemplateConfig,
        )
        self.index(
            self.doxygen.root.children,
            [Kind.FUNCTION],
            [Kind.CLASS, Kind.STRUCT, Kind.INTERFACE],
            "Class Member Functions",
            defaultTemplateConfig,
        )
        self.index(
            self.doxygen.root.children,
            [Kind.VARIABLE],
            [Kind.CLASS, Kind.STRUCT, Kind.INTERFACE],
            "Class Member Variables",
            defaultTemplateConfig,
        )
        self.index(
            self.doxygen.root.children,
            [Kind.TYPEDEF],
            [Kind.CLASS, Kind.STRUCT, Kind.INTERFACE],
            "Class Member Typedefs",
            defaultTemplateConfig,
        )
        self.index(
            self.doxygen.root.children,
            [Kind.ENUM],
            [Kind.CLASS, Kind.STRUCT, Kind.INTERFACE],
            "Class Member Enums",
            defaultTemplateConfig,
        )
        self.index(
            self.doxygen.root.children,
            [Kind.FUNCTION, Kind.VARIABLE, Kind.TYPEDEF, Kind.ENUM],
            [Kind.NAMESPACE],
            "Namespace Members",
            defaultTemplateConfig,
        )
        self.index(
            self.doxygen.root.children,
            [Kind.FUNCTION],
            [Kind.NAMESPACE],
            "Namespace Member Functions",
            defaultTemplateConfig,
        )
        self.index(
            self.doxygen.root.children,
            [Kind.VARIABLE],
            [Kind.NAMESPACE],
            "Namespace Member Variables",
            defaultTemplateConfig,
        )
        self.index(
            self.doxygen.root.children,
            [Kind.TYPEDEF],
            [Kind.NAMESPACE],
            "Namespace Member Typedefs",
            defaultTemplateConfig,
        )
        self.index(
            self.doxygen.root.children,
            [Kind.ENUM],
            [Kind.NAMESPACE],
            "Namespace Member Enums",
            defaultTemplateConfig,
        )
        self.index(
            self.doxygen.files.children,
            [Kind.FUNCTION],
            [Kind.FILE],
            "Functions",
            defaultTemplateConfig,
        )
        self.index(
            self.doxygen.files.children,
            [Kind.DEFINE],
            [Kind.FILE],
            "Macros",
            defaultTemplateConfig,
        )
        self.index(
            self.doxygen.files.children,
            [Kind.VARIABLE, Kind.UNION, Kind.TYPEDEF, Kind.ENUM],
            [Kind.FILE],
            "Variables",
            defaultTemplateConfig,
        )

    def annotated(self, nodes: [Node], config: dict = None):
        path = "annotated.md"
        output = self.generatorBase.annotated(nodes, config)
        self.save(path, output)

    def programlisting(self, node: [Node], config: dict = None):
        path = f"{node.refid}_source.md"

        output = self.generatorBase.programlisting(node, config)
        self.save(path, output)

    def fileindex(self, nodes: [Node], config: dict = None):
        path = "files.md"

        output = self.generatorBase.fileindex(nodes, config)
        self.save(path, output)

    def namespaces(self, nodes: [Node], config: dict = None):
        path = "namespaces.md"

        output = self.generatorBase.namespaces(nodes, config)
        self.save(path, output)

    def page(self, node: Node, config: dict = None):
        path = f"{node.name}.md"

        output = self.generatorBase.page(node, config)
        self.save(path, output)

    def pages(self, nodes: [Node], config: dict = None):
        for node in nodes:
            self.page(node, config)

    def relatedpages(self, nodes: [Node], config: dict = None):
        path = "pages.md"

        output = self.generatorBase.relatedpages(nodes)
        self.save(path, output)

    def example(self, node: Node, config: dict = None):
        path = f"{node.refid}.md"

        output = self.generatorBase.example(node, config)
        self.save(path, output)

    def examples(self, nodes: [Node], config: dict = None):
        for node in nodes:
            if node.is_example:
                if node.has_programlisting:
                    print(f"Generating example {node.name}...")
                self.example(node, config)

        path = "examples.md"

        output = self.generatorBase.examples(nodes, config)
        self.save(path, output)

    def classes(self, nodes: [Node], config: dict = None):
        path = "classes.md"

        output = self.generatorBase.classes(nodes, config)
        self.save(path, output)

    def _has_concepts_recursive(self, node: Node) -> bool:
        """Check if a node (or its descendants) contains any concept children."""
        for child in node.children:
            if child.is_concept:
                return True
            if child.is_namespace and self._has_concepts_recursive(child):
                return True
        return False

    def _filter_concept_tree(self, node: Node) -> Node:
        """Create a shallow copy of a namespace node keeping only concepts and
        sub-namespaces that (recursively) contain concepts.  This prevents the
        template from rendering namespaces that have no concept descendants."""
        from copy import copy

        filtered = copy(node)
        new_children = []
        for child in node.children:
            if child.is_concept:
                new_children.append(child)
            elif child.is_namespace and self._has_concepts_recursive(child):
                new_children.append(self._filter_concept_tree(child))
        filtered._children = new_children
        return filtered

    def _find_namespace_by_name(self, name: str, nodes=None):
        """Find a namespace node by its fully qualified name in the root tree."""
        if nodes is None:
            nodes = self.doxygen.root.children
        for n in nodes:
            if n.is_namespace and n.name_long == name:
                return n
            if n.is_namespace:
                found = self._find_namespace_by_name(name, n.children)
                if found:
                    return found
        return None

    def _build_concept_nodes(self) -> list:
        """Build a combined node list for the concept list page.

        Returns namespace nodes from root (that recursively contain concepts)
        plus top-level concepts that are not inside any namespace.  This gives
        the concepts template a hierarchy it can render like the Class List.

        Handles two Doxygen versions:
        - < 1.9.5: concepts are variables inside files, reclassified as concepts,
          namespaces may have them as children via innerconcept-like mechanism.
        - >= 1.9.5: concepts are native compounds in index.xml but namespaces
          do NOT have innerconcept elements. We match by FQN prefix.
        """
        # First try: check if namespaces already have concept children (Doxygen < 1.9.5 path)
        namespaced_refids: set = set()

        def _collect_from_ns(nodes):
            for n in nodes:
                if n.is_concept:
                    namespaced_refids.add(n.refid)
                if n.is_namespace:
                    _collect_from_ns(n.children)

        for n in self.doxygen.root.children:
            if n.is_namespace:
                _collect_from_ns(n.children)

        if namespaced_refids:
            # Doxygen < 1.9.5 path: namespaces already have concepts as children
            top_level = [c for c in self.doxygen.concepts.children if c.refid not in namespaced_refids]
            ns_with_concepts = [
                self._filter_concept_tree(n)
                for n in self.doxygen.root.children if n.is_namespace and self._has_concepts_recursive(n)
            ]
            return ns_with_concepts + top_level

        # Doxygen >= 1.9.5 path: match concepts to namespaces by FQN
        # concept.name contains FQN like "gl::traits::c_arithmetic"
        top_level = []
        ns_concepts: dict = {}  # namespace_fqn -> [concept_node, ...]

        for c in self.doxygen.concepts.children:
            name = c.name_long or c.name or ""
            if "::" in name:
                ns_name = name.rsplit("::", 1)[0]
                ns_concepts.setdefault(ns_name, []).append(c)
            else:
                top_level.append(c)

        # Find matching namespace nodes and inject concepts as children
        ns_nodes = []
        processed_ns = set()
        for ns_name, concepts in ns_concepts.items():
            ns_node = self._find_namespace_by_name(ns_name)
            if ns_node and ns_node.refid not in processed_ns:
                # Add concepts to namespace if not already there
                existing_refids = {ch.refid for ch in ns_node.children if ch.is_concept}
                for c in concepts:
                    if c.refid not in existing_refids:
                        ns_node.add_child(c)
                processed_ns.add(ns_node.refid)
                # Walk up to find top-level namespace
                top_ns = ns_node
                while top_ns._parent and top_ns._parent.is_namespace:
                    top_ns = top_ns._parent
                if top_ns.refid not in {n.refid for n in ns_nodes}:
                    ns_nodes.append(top_ns)
            else:
                # Namespace not found in root tree — treat as top-level
                top_level.extend(concepts)

        # Filter namespace trees to only show concept-relevant nodes
        filtered_ns = [self._filter_concept_tree(n) for n in ns_nodes]
        return filtered_ns + top_level

    def concepts_page(self, config: dict = None):
        path = "concepts.md"

        nodes = self._build_concept_nodes()
        output = self.generatorBase.concepts(nodes, config)
        self.save(path, output)

    def concept_members(self, nodes: [Node], config: dict = None):
        for node in nodes:
            if node.is_concept:
                self.member(node, config)

    def modules(self, nodes: [Node], config: dict = None):
        path = "modules.md"

        output = self.generatorBase.modules(nodes, config)
        self.save(path, output)

    def hierarchy(self, nodes: [Node], config: dict = None):
        path = "hierarchy.md"

        output = self.generatorBase.hierarchy(nodes, config)
        self.save(path, output)

    def member(self, node: Node, config: dict = None):
        path = node.filename

        output = self.generatorBase.member(node, config)
        self.save(path, output)

        if node.is_language or node.is_group or node.is_file or node.is_dir:
            self.members(node.children, config)

    def file(self, node: Node, config: dict = None):
        path = node.filename

        output = self.generatorBase.file(node, config)
        self.save(path, output)

        if node.is_file and node.has_programlisting:
            self.programlisting(node, config)

        if node.is_file or node.is_dir:
            self.files(node.children, config)

    def members(self, nodes: [Node], config: dict = None):
        for node in nodes:
            if node.is_parent or node.is_group or node.is_file or node.is_dir:
                self.member(node, config)

    def files(self, nodes: [Node], config: dict = None):
        for node in nodes:
            if node.is_file or node.is_dir:
                self.file(node, config)

    def index(
        self,
        nodes: [Node],
        kind_filters: Kind,
        kind_parents: [Kind],
        title: str,
        config: dict = None,
    ):
        path = title.lower().replace(" ", "_") + ".md"

        output = self.generatorBase.index(nodes, kind_filters, kind_parents, title, config)
        self.save(path, output)

    def _generate_recursive(self, output_summary: str, node: Node, level: int):
        if node.kind.is_parent():
            output_summary += str(" " * level + generate_link(f"{node.kind.value} {node.name}", f"{node.refid}.md"))
            for child in node.children:
                self._generate_recursive(output_summary, child, level + 2)

    def _generate_recursive_files(self, output_summary: str, node: Node, level: int, config: dict = None):
        if config is None:
            config = []
        if node.kind.is_file() or node.kind.is_dir():
            output_summary += str(" " * int(level + 2) + generate_link(node.name, f"{node.refid}.md", end=""))

            if node.kind.is_file():
                output_summary += f" [[source code]]({node.refid}_source.md) \n"
            else:
                output_summary += "\n"

            for child in node.children:
                self._generate_recursive_files(output_summary, child, level + 2, config)

    def _generate_recursive_examples(self, output_summary: str, node: Node, level: int):
        if node.kind.is_example():
            output_summary += str(" " * level + generate_link(node.name, f"{node.refid}.md"))
            for child in node.children:
                self._generate_recursive_examples(output_summary, child, level + 2)

    def _generate_recursive_groups(self, output_summary: str, node: Node, level: int):
        if node.kind.is_group():
            output_summary += str(" " * level + generate_link(node.title, f"{node.refid}.md"))
            for child in node.children:
                self._generate_recursive_groups(output_summary, child, level + 2)

    def _generate_recursive_pages(self, output_summary: str, node: Node, level: int):
        if node.kind.is_page():
            output_summary += str(" " * level + generate_link(node.title, f"{node.refid}.md"))
            for child in node.children:
                self._generate_recursive_pages(output_summary, child, level + 2)

    def summary(self, defaultTemplateConfig: dict):
        offset = 0
        output_summary = "" + str(" " * (offset + 2) + generate_link("Related Pages", "pages.md"))
        for node in self.doxygen.pages.children:
            self._generate_recursive_pages(output_summary, node, offset + 4)

        output_summary += str(" " * (offset + 2) + generate_link("Modules", "modules.md"))
        for node in self.doxygen.groups.children:
            self._generate_recursive_groups(output_summary, node, offset + 4)

        output_summary += str(" " * (offset + 2) + generate_link("Class List", "annotated.md"))
        for node in self.doxygen.root.children:
            self._generate_recursive(output_summary, node, offset + 4)

        if self.doxygen.concepts.children:
            output_summary += str(" " * (offset + 2) + generate_link("Concept List", "concepts.md"))
            for node in self.doxygen.concepts.children:
                if node.kind.is_concept():
                    output_summary += str(" " * (offset + 4) + generate_link(f"concept {node.name}", f"{node.refid}.md"))

        for key, val in ADDITIONAL_FILES.items():
            output_summary += str(" " * (offset + 2) + generate_link(key, val))

        output_summary += str(" " * (offset + 2) + generate_link("Files", "files.md", end="\n"))
        for node in self.doxygen.files.children:
            self._generate_recursive_files(output_summary, node, offset + 4, defaultTemplateConfig)

        # output_summary += str(' ' * (offset + 2) + generate_link('Examples', 'examples.md'))
        # for node in self.doxygen.examples.children:
        # 	self._generate_recursive_examples(node, offset + 4)

        output_summary += str(" " * (offset + 2) + generate_link("File Variables", "variables.md"))
        output_summary += str(" " * (offset + 2) + generate_link("File Functions", "functions.md"))
        output_summary += str(" " * (offset + 2) + generate_link("File Macros", "macros.md"))

        self.save("links.md", output_summary)
