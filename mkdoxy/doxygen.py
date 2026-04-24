import logging
import os
import re
from xml.etree import ElementTree
from typing import Union

from mkdoxy.cache import Cache
from mkdoxy.constants import Kind, Visibility
from mkdoxy.node import Node
from mkdoxy.project import ProjectContext
from mkdoxy.xml_parser import XmlParser

log: logging.Logger = logging.getLogger("mkdocs")

SortingCfg = Union[bool, dict[str, bool]]


class Doxygen:
    def __init__(self, index_path: str, parser: XmlParser, cache: Cache, sorting_cfg: SortingCfg = True):
        self.debug = parser.debug
        self.sorting_cfg = sorting_cfg

        path_xml = os.path.join(index_path, "index.xml")
        if self.debug:
            log.info(f"Loading XML from: {path_xml}")
        xml = ElementTree.parse(path_xml).getroot()

        self.parser = parser
        self.ctx = ProjectContext(cache)

        self.root = Node("root", None, self.ctx, self.parser, None)
        self.groups = Node("root", None, self.ctx, self.parser, None)
        self.files = Node("root", None, self.ctx, self.parser, None)
        self.pages = Node("root", None, self.ctx, self.parser, None)
        self.examples = Node("root", None, self.ctx, self.parser, None)
        self.concepts = Node("root", None, self.ctx, self.parser, None)

        for compound in xml.findall("compound"):
            kind = Kind.from_str(compound.get("kind"))
            refid = compound.get("refid")
            if kind.is_language():
                node = Node(
                    os.path.join(index_path, f"{refid}.xml"),
                    None,
                    self.ctx,
                    self.parser,
                    self.root,
                )
                node._visibility = Visibility.PUBLIC
                self.root.add_child(node)
            if kind == Kind.GROUP:
                node = Node(
                    os.path.join(index_path, f"{refid}.xml"),
                    None,
                    self.ctx,
                    self.parser,
                    self.root,
                )
                node._visibility = Visibility.PUBLIC
                self.groups.add_child(node)
            if kind in [Kind.FILE, Kind.DIR]:
                node = Node(
                    os.path.join(index_path, f"{refid}.xml"),
                    None,
                    self.ctx,
                    self.parser,
                    self.root,
                )
                node._visibility = Visibility.PUBLIC
                self.files.add_child(node)
            if kind == Kind.PAGE:
                node = Node(
                    os.path.join(index_path, f"{refid}.xml"),
                    None,
                    self.ctx,
                    self.parser,
                    self.root,
                )
                node._visibility = Visibility.PUBLIC
                self.pages.add_child(node)
            if kind == Kind.EXAMPLE:
                node = Node(
                    os.path.join(index_path, f"{refid}.xml"),
                    None,
                    self.ctx,
                    self.parser,
                    self.root,
                )
                node._visibility = Visibility.PUBLIC
                self.examples.add_child(node)
            if kind == Kind.CONCEPT:
                node = Node(
                    os.path.join(index_path, f"{refid}.xml"),
                    None,
                    self.ctx,
                    self.parser,
                    self.root,
                )
                node._visibility = Visibility.PUBLIC
                self.concepts.add_child(node)

        if self.debug:
            log.info("Deduplicating data... (may take a minute!)")
        for child in self.root.children.copy():
            self._fix_duplicates(child, self.root, [])

        for child in self.groups.children.copy():
            self._fix_duplicates(child, self.groups, [Kind.GROUP])

        for child in self.files.children.copy():
            self._fix_duplicates(child, self.files, [Kind.FILE, Kind.DIR])

        for child in self.examples.children.copy():
            self._fix_duplicates(child, self.examples, [Kind.EXAMPLE])

        for child in self.concepts.children.copy():
            self._fix_duplicates(child, self.concepts, [Kind.CONCEPT])

        # For Doxygen < 1.9.5, concepts are emitted as variables inside file compounds.
        # After node parsing reclassifies them, collect them into the concepts list.
        self._collect_concepts_from_files()

        # For Doxygen >= 1.9.5, @ingroup on concepts is not reflected in the
        # group XML (Doxygen bug).  Parse source files to recover the mapping.
        self._fix_concept_groups()

        self._fix_parents(self.files)

        if self.debug:
            log.info("Sorting...")
        self._recursive_sort(self.root)
        self._recursive_sort(self.groups)
        self._recursive_sort(self.files)
        self._recursive_sort(self.pages)
        self._recursive_sort(self.examples)
        self._recursive_sort(self.concepts)

    def _fix_parents(self, node: Node):
        if node.is_dir or node.is_root:
            for child in node.children:
                if child.is_file:
                    child._parent = node
                if child.is_dir:
                    self._fix_parents(child)

    def _collect_concepts_from_files(self):
        """Collect concept nodes from file/root trees into the concepts list.

        For Doxygen < 1.9.5, concepts are emitted as variable members inside
        file compounds. After Node parsing reclassifies them as Kind.CONCEPT,
        this method finds them and adds them to self.concepts so they appear
        in the concept list and get their own pages.
        """
        existing_refids = {c.refid for c in self.concepts.children}

        def _find_concepts(nodes):
            for node in nodes:
                if node.kind == Kind.CONCEPT and node.refid not in existing_refids:
                    existing_refids.add(node.refid)
                    self.concepts.add_child(node)
                if node.has_children:
                    _find_concepts(node.children)

        _find_concepts(self.files.children)
        _find_concepts(self.root.children)

    def _fix_concept_groups(self):
        """Fix missing concept-to-group associations for Doxygen >= 1.9.5.

        Doxygen >= 1.9.5 treats concepts as native compounds but does NOT
        add them to group XML even when the source uses @ingroup.  This
        method reads the source file referenced by each concept's <location>
        element, looks for @ingroup / \\ingroup in the comment block
        preceding the concept definition, and adds the concept node as a
        child of the matching group.
        """
        if not self.concepts.children or not self.groups.children:
            return

        # Build a map: group compoundname -> group Node (recursively)
        group_map: dict[str, "Node"] = {}

        def _build_group_map(nodes):
            for n in nodes:
                if n.is_group:
                    group_map[n._name] = n
                    _build_group_map(n.children)

        _build_group_map(self.groups.children)

        if not group_map:
            return

        # Regex matching @ingroup or \ingroup followed by one or more group names
        ingroup_re = re.compile(r'[@\\]ingroup\s+([\w\s]+)')

        # Cache of already-read source files: filepath -> list of lines
        file_cache: dict[str, list[str]] = {}

        for concept in self.concepts.children:
            if not concept.is_concept:
                continue

            # Check if this concept is already a child of some group
            already_in_group = False
            for g in group_map.values():
                if any(c.refid == concept.refid for c in g.children):
                    already_in_group = True
                    break
            if already_in_group:
                continue

            # Get source file and line from XML <location>
            src_file = concept._location.plain()
            src_line = concept._location.line()
            if not src_file or src_line <= 0:
                continue

            # Try to resolve the file path
            if not os.path.isabs(src_file):
                # Try relative to CWD (where mkdocs runs)
                if not os.path.isfile(src_file):
                    continue

            # Read file (cached)
            if src_file not in file_cache:
                try:
                    with open(src_file, "r", encoding="utf-8", errors="replace") as f:
                        file_cache[src_file] = f.readlines()
                except OSError:
                    continue

            lines = file_cache[src_file]

            # Scan backwards from the concept definition line to find @ingroup
            # ONLY in the immediately preceding comment block.  We walk upward
            # from the line before the definition until we leave the comment
            # (hit a non-comment, non-blank line that isn't part of the block).
            found_groups: list[str] = []
            idx = src_line - 2  # 0-indexed, one line before the definition
            # Skip blank lines / template lines between comment and concept
            while idx >= 0:
                stripped = lines[idx].strip()
                if not stripped or stripped.startswith("template"):
                    idx -= 1
                    continue
                break

            # Now walk the comment block (support both /* */ and /// styles)
            in_block = False
            while idx >= 0:
                stripped = lines[idx].strip()
                # Detect end of C-style block comment (reading bottom-up)
                if stripped.endswith("*/") or stripped.startswith("*") or stripped.startswith("/**") or stripped.startswith("/*!"):
                    in_block = True
                # Detect C++ style comment
                if stripped.startswith("///") or stripped.startswith("//!"):
                    in_block = True

                if not in_block:
                    break

                m = ingroup_re.search(stripped)
                if m:
                    found_groups.extend(m.group(1).split())

                # If we hit start of a block comment, stop
                if stripped.startswith("/**") or stripped.startswith("/*!") or stripped.startswith("/*"):
                    break

                idx -= 1

            for gname in found_groups:
                gname = gname.strip()
                if gname in group_map:
                    group_node = group_map[gname]
                    # Avoid duplicates
                    if not any(c.refid == concept.refid for c in group_node.children):
                        group_node.add_child(concept)
                        if self.debug:
                            log.info(f"  -> Added concept '{concept.name}' to group '{gname}'")

    def _should_sort(self, node: Node) -> bool:
        if isinstance(self.sorting_cfg, bool):
            return self.sorting_cfg

        if isinstance(self.sorting_cfg, dict):
            if node.is_class_or_struct:
                return self.sorting_cfg.get("classes", True)
            if node.is_namespace:
                return self.sorting_cfg.get("namespaces", True)
            if node.is_file or node.is_dir:
                return self.sorting_cfg.get("files", True)
            if node.is_group:
                return self.sorting_cfg.get("groups", True)

            return self.sorting_cfg.get("default", True)

        return True

    def _recursive_sort(self, node: Node):
        if self._should_sort(node):
            node.sort_children()

        for child in node.children:
            self._recursive_sort(child)

    def _is_in_root(self, node: Node, root: Node):
        return any(node.refid == child.refid for child in root.children)

    def _remove_from_root(self, refid: str, root: Node):
        for i, child in enumerate(root.children):
            if child.refid == refid:
                root.children.pop(i)
                return

    def _fix_duplicates(self, node: Node, root: Node, filter: [Kind]):
        for child in node.children:
            if len(filter) > 0 and child.kind not in filter:
                continue
            if self._is_in_root(child, root):
                self._remove_from_root(child.refid, root)
            self._fix_duplicates(child, root, filter)

    def printStructure(self):
        if not self.debug:
            return
        print("\n")
        log.info("Print root")
        for node in self.root.children:
            self.print_node(node, "")
        print("\n")

        log.info("Print groups")
        for node in self.groups.children:
            self.print_node(node, "")
        print("\n")

        log.info("Print files")
        for node in self.files.children:
            self.print_node(node, "")
        print("\n")

        log.info("Print concepts")
        for node in self.concepts.children:
            self.print_node(node, "")

    def print_node(self, node: Node, indent: str):
        if self.debug:
            log.info(f"{indent} {node.kind} {node.name}")
        for child in node.children:
            self.print_node(child, f"{indent}  ")
