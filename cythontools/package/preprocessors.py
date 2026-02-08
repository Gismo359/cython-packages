"""
TODO@Daniel:
  This module needs a complete rewrite

  Planned changes include:
   - Using `pluggy` for managing preprocessors
   - Writing or reusing a third party python/cython parser
     instead of `ast` and `Cython.Compiler` (see `MainPreprocessor.process_pyx_module`)
   - Replace `SourceEditor` with a solution that doesn't require
     rebuilding the whole source code after each preprocessor
"""

from __future__ import annotations

from typing import Protocol
from dataclasses import dataclass, field

from cythontools.package.common import ModuleDef


def default_preprocessors() -> list[BasePreprocessor]:
    return [MainPreprocessor()]


@dataclass(frozen=True, kw_only=True)
class CodeRange:
    start_line: int
    start_col: int
    stop_line: int
    stop_col: int
    value: str

    def __post_init__(self):
        if self.start > self.stop:
            raise ValueError("Code range has invalid start/stop positions")

    @property
    def start(self) -> tuple[int, int]:
        return self.start_line, self.start_col

    @property
    def stop(self) -> tuple[int, int]:
        return self.stop_line, self.stop_col


@dataclass(frozen=True, kw_only=True)
class SourceEditor:
    source: str
    ranges: list[CodeRange] = field(default_factory=list)

    def build(self):
        source_lines = self.source.splitlines(keepends=True)
        ranges: list[CodeRange] = sorted(self.ranges)
        for a, b in zip(ranges[:-1], ranges[1:]):
            if a.stop < b.start:
                raise ValueError("Overlapping code ranges are not allowed.")

        code = ""
        last = (0, 0)
        for range in ranges:
            start_line, start_col = last
            stop_line, stop_col = range.start

            if lines := source_lines[start_line : stop_line + 1]:
                lines[-1] = lines[-1][:stop_col]
                lines[0] = lines[0][start_col:]

            code += "".join(lines)
            code += range.value

            last = range.stop

        last_line, last_col = last
        if lines := source_lines[last_line:]:
            lines[0] = lines[0][last_col:]
            code += "".join(lines)

        if not code.endswith("\n"):
            code += "\n"

        return code


class BasePreprocessor(Protocol):
    def process_package(self, package: list[ModuleDef]) -> list[ModuleDef]:
        new_package = []
        for module in package:
            new_module = self.process_module(module)
            new_package.append(new_module if new_module is not None else module)
        return new_package

    def process_module(self, module: ModuleDef) -> ModuleDef:
        if module.py_source is not None:
            return self.process_py_module(module)
        if module.pyx_source is not None:
            return self.process_pyx_module(module)
        if module.pxd_source is not None:
            return self.process_pxd_module(module)

    def process_py_module(self, module: ModuleDef) -> ModuleDef:
        pass

    def process_pyx_module(self, module: ModuleDef) -> ModuleDef:
        pass

    def process_pxd_module(self, module: ModuleDef) -> ModuleDef:
        pass


class MainPreprocessor(BasePreprocessor):
    def process_py_module(self, module: ModuleDef) -> ModuleDef:
        assert module.py_source is not None

        import ast

        source_editor = SourceEditor(source=module.py_source)

        root = ast.parse(module.py_source)
        for stmt in root.body:
            if not isinstance(stmt, ast.If):
                continue

            if not isinstance(stmt.test, ast.Compare):
                continue

            if len(stmt.test.ops) != 1:
                continue

            if len(stmt.test.comparators) != 1:
                continue

            (operator,) = stmt.test.ops
            if not isinstance(operator, ast.Eq):
                continue

            lhs = stmt.test.left
            (rhs,) = stmt.test.comparators
            if not isinstance(lhs, ast.Name):
                lhs, rhs = rhs, lhs

            if not isinstance(lhs, ast.Name):
                continue

            if not isinstance(rhs, ast.Constant):
                continue

            if not isinstance(rhs.value, str):
                continue

            if rhs.value != "__main__":
                continue

            source_editor.ranges.append(
                CodeRange(
                    start_line=stmt.lineno - 1,
                    start_col=stmt.col_offset,
                    stop_line=stmt.test.end_lineno - 1,
                    stop_col=stmt.test.end_col_offset,
                    value="def __cythontools_main__()",
                )
            )

        return module.with_source(
            py_source=source_editor.build(), __main__="__cythontools_main__"
        )

    def process_pyx_module(self, module: ModuleDef) -> ModuleDef:
        assert module.pyx_source is not None

        # NOTE@Daniel:
        #   The Cython AST modules do not provide a meaningful end_pos()
        #   There is no way to get the length (in source code) of any `Node`
        #
        #   Currently, this is not a big issue but will hinder more complicated
        #   parsers
        #
        #   Possible workarounds include:
        #    - Using other internal Cython API to re-parse some `Nodes`
        #    - Using a third party parser which offers better API

        from Cython.Compiler.ExprNodes import PrimaryCmpNode, NameNode, UnicodeNode
        from Cython.Compiler.Nodes import IfStatNode, IfClauseNode, StatListNode
        from Cython.Compiler import ModuleNode
        from Cython.Compiler.TreeFragment import parse_from_strings

        source_editor = SourceEditor(source=module.pyx_source)

        root: ModuleNode = parse_from_strings(module.module_name, module.pyx_source)
        if not isinstance(root.body, StatListNode):
            return

        for child in root.body.stats:
            if not isinstance(child, IfStatNode):
                continue

            if not isinstance(child.if_clauses, list):
                continue

            if not len(child.if_clauses) == 1:
                continue

            (if_clause,) = child.if_clauses
            if not isinstance(if_clause, IfClauseNode):
                continue

            if not isinstance(if_clause.condition, PrimaryCmpNode):
                continue

            if if_clause.condition.operator != "==":
                continue

            lhs = if_clause.condition.operand1
            rhs = if_clause.condition.operand2

            if not isinstance(lhs, NameNode):
                lhs, rhs = rhs, lhs

            if not isinstance(lhs, NameNode):
                continue

            if lhs.name != "__name__":
                continue

            if not isinstance(rhs, UnicodeNode):
                continue

            if rhs.value != "__main__":
                continue

            source_editor.ranges.append(
                CodeRange(
                    start_line=child.pos[1] - 1,
                    start_col=child.pos[2],
                    stop_line=rhs.pos[1] - 1,
                    stop_col=rhs.pos[2] + 10,
                    value="def __cythontools_main__()",
                )
            )

        return module.with_source(pyx_source=source_editor.build())
