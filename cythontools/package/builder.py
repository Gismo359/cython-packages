from __future__ import annotations

from types import ModuleType
from pathlib import Path
from setuptools import Extension
from dataclasses import dataclass, field

from cythontools.package.common import ModuleDef
from cythontools.package.core import cythonize_package
from cythontools.package.preprocessors import (
    BasePreprocessor,
    default_preprocessors,
)


@dataclass(frozen=True, kw_only=True)
class CythonBuilder:
    # TODO@Daniel: Add more options as needed
    preprocessors: list[BasePreprocessor] = field(default_factory=default_preprocessors)
    working_path: Path = Path("./build/generated/")
    language_level: int = 3
    annotate_html: bool = False
    annotate_coverage: bool = False
    check_timestamps: bool = True
    verbose: bool = False
    quiet: bool = False

    def build(
        self,
        package_name: str,
        package_paths: list[Path] | Path,
    ) -> list[ModuleDef]:
        return cythonize_package(
            package_name=package_name,
            package_paths=package_paths,
            preprocessors=self.preprocessors,
            working_path=self.working_path,
            language_level=self.language_level,
            annotate_html=self.annotate_html,
            annotate_coverage=self.annotate_coverage,
            check_timestamps=self.check_timestamps,
            verbose=self.verbose,
            quiet=self.quiet,
        )

    def as_build_ext(self):
        pass

    def make_extension_from_path(
        self,
        package_paths: str | Path | list[str | Path],
        name: str | None = None,
        include_dirs: list[str] | None = None,
        define_macros: list[tuple[str, str | None]] | None = None,
        undef_macros: list[str] | None = None,
        library_dirs: list[str] | None = None,
        libraries: list[str] | None = None,
        runtime_library_dirs: list[str] | None = None,
        extra_objects: list[str] | None = None,
        extra_compile_args: list[str] | None = None,
        extra_link_args: list[str] | None = None,
        export_symbols: list[str] | None = None,
        swig_opts: list[str] | None = None,
        depends: list[str] | None = None,
        language: str | None = None,
        optional: bool | None = None,
        *,
        py_limited_api: bool = False,
    ):
        if isinstance(package_paths, (str, Path)):
            package_paths = [package_paths]

        package_paths: list[Path] = list({Path(path) for path in package_paths})
        if name is None:
            names = {path.stem for path in package_paths}
            assert len(names) == 1, "Cannot infer package name"

            (name,) = names

        module_specs = self.build(name, package_paths)
        sources = [module_spec.c_path for module_spec in module_specs]

        if define_macros is None:
            define_macros = []

        define_macros.append(("CYTHON_NO_PYINIT_EXPORT", None))

        return Extension(
            name,
            sources,
            include_dirs=include_dirs,
            define_macros=define_macros,
            undef_macros=undef_macros,
            library_dirs=library_dirs,
            libraries=libraries,
            runtime_library_dirs=runtime_library_dirs,
            extra_objects=extra_objects,
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
            export_symbols=export_symbols,
            swig_opts=swig_opts,
            depends=depends,
            language=language,
            optional=optional,
            py_limited_api=py_limited_api,
        )

    def make_extension_from_package(
        self,
        package: ModuleType,
        name: str | None = None,
        include_dirs: list[str] | None = None,
        define_macros: list[tuple[str, str | None]] | None = None,
        undef_macros: list[str] | None = None,
        library_dirs: list[str] | None = None,
        libraries: list[str] | None = None,
        runtime_library_dirs: list[str] | None = None,
        extra_objects: list[str] | None = None,
        extra_compile_args: list[str] | None = None,
        extra_link_args: list[str] | None = None,
        export_symbols: list[str] | None = None,
        swig_opts: list[str] | None = None,
        depends: list[str] | None = None,
        language: str | None = None,
        optional: bool | None = None,
        *,
        py_limited_api: bool = False,
    ):
        package_paths = list({Path(path) for path in package.__path__})
        name = name or package.__name__

        return self.make_extension_from_path(
            package_paths=package_paths,
            name=name,
            include_dirs=include_dirs,
            define_macros=define_macros,
            undef_macros=undef_macros,
            library_dirs=library_dirs,
            libraries=libraries,
            runtime_library_dirs=runtime_library_dirs,
            extra_objects=extra_objects,
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
            export_symbols=export_symbols,
            swig_opts=swig_opts,
            depends=depends,
            language=language,
            optional=optional,
            py_limited_api=py_limited_api,
        )
