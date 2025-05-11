from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field

from Cython import Utils


def needs_update(input_paths: list[Path], output_paths: list[Path]):
    inputs_modified = max(Utils.modification_time(path) for path in input_paths)
    outputs_modified = max(Utils.modification_time(path) for path in output_paths)
    return inputs_modified > outputs_modified


def update_file(path: Path, content: str):
    if path.exists() and path.read_text() == content:
        return

    path.write_text(content)


@dataclass(frozen=True, kw_only=True)
class ModuleDef:
    is_package: bool
    module_name: str
    initializer_name: str

    c_path: Path

    py_source: str | None = None
    pyx_source: str | None = None
    pxd_source: str | None = None

    custom_globals: dict = field(default_factory=dict)

    @property
    def py_path(self) -> Path:
        return self.c_path.with_suffix(".py")

    @property
    def pyx_path(self) -> Path:
        return self.c_path.with_suffix(".pyx")

    @property
    def pxd_path(self) -> Path:
        return self.c_path.with_suffix(".pxd")

    @property
    def last_modified(self) -> float:
        paths = [self.py_path, self.pyx_path, self.pxd_path]
        sources = [self.py_source, self.pyx_source, self.pxd_source]

        required_files = [
            path for path, source in zip(paths, sources) if source is not None
        ]
        return max(map(Utils.modification_time, required_files))

    def with_source(
        self,
        py_source: str | None = None,
        pyx_source: str | None = None,
        pxd_source: str | None = None,
        **kwargs,
    ) -> ModuleDef:
        if py_source is None:
            py_source = self.py_source

        if pyx_source is None:
            pyx_source = self.pyx_source

        if pxd_source is None:
            pxd_source = self.pxd_source

        custom_globals = self.custom_globals.copy()
        custom_globals.update(**kwargs)

        return ModuleDef(
            is_package=self.is_package,
            module_name=self.module_name,
            initializer_name=self.initializer_name,
            c_path=self.c_path,
            py_source=py_source,
            pyx_source=pyx_source,
            pxd_source=pxd_source,
            custom_globals=custom_globals,
        )

    def save(self):
        if self.py_source is not None:
            update_file(self.py_path, self.py_source)

        if self.pyx_source is not None:
            update_file(self.pyx_path, self.pyx_source)

        if self.pxd_source is not None:
            update_file(self.pxd_path, self.pxd_source)
