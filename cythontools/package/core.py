from __future__ import annotations

import hashlib

from pathlib import Path

from Cython import Utils
from Cython.Compiler.Main import compile

from cythontools.package.common import ModuleDef
from cythontools.package.preprocessors import BasePreprocessor


def build_initializer_name(module_name: str, is_package: bool) -> str:
    md5 = hashlib.md5(f"{module_name}:{is_package}".encode()).hexdigest()
    return f"_{md5}"


def cythonize_module(
    module_def: ModuleDef,
    language_level: int = 3,
    annotate_html: bool = False,
    annotate_coverage: bool = False,
    check_timestamps: bool = True,
    verbose: bool = False,
    quiet: bool = False,
) -> bool:
    """
    Runs the Cython compiler on a module to generate the `*.c` source files.
    The outputs are postprocessed, so they can be compiled in a shared library together.

    NOTE:
      Cython will generate a `PyInit_{module_name}` function which is normally used by
      the interpreter to initialize the extension. We replace all of these to avoid conflicts
      when linking.

      We don't need to keep the `PyInit_*` convention since we will be calling them manually,
      the interpeter won't even know they exist.

    NOTE:
      Cython generates `extern int __pyx_module_is_main_*` in case the module has
      been embedded as the `__main__` module. Due to conflicts, we make them `static`,
      so their symbols don't reach the linker (and might get optimized away entirely).

      Currently, we do not support this functionality. Instead, you should either use
      `pyproject.toml` scripts (preferred) or preprocess with `MainPreprocessor`

    :param module_def: A `ModuleDef` which has already been preprocessed and saved
    :param language_level: Major python version to assume in cython - must be 2 or 3, defaults to 3
    :param annotate_html: Generate html annotations which show python usage after cythonization, defaults to False
    :param annotate_coverage: Include coverage information in annotated html files, defaults to False, implies `annotate_html=True`
    :param check_timestamps: Cythonize only if changes are detected, defaults to True
    :param verbose: Include debug logs, defaults to False
    :param quiet: Do not emit logs, defaults to False
    :return: Whether the module was dirty, i.e. needed compilation
    """
    try:
        input_last_modified = module_def.last_modified
        output_last_modified = Utils.modification_time(module_def.c_path)
        if annotate_html:
            output_last_modified = max(
                output_last_modified,
                Utils.modification_time(module_def.c_path.with_suffix(".html")),
            )
        dirty = output_last_modified < input_last_modified or not check_timestamps
    except OSError:
        dirty = True

    if not dirty:
        return dirty

    compile(
        str(module_def.py_path),
        full_module_name=module_def.module_name,
        output_file=module_def.c_path,
        module_name=module_def.module_name,
        language_level=language_level,
        annotate=annotate_html,
        annotate_coverage_xml=annotate_coverage,
        verbose=verbose,
        quiet=quiet,
    )

    if module_def.is_package:
        stem = module_def.c_path.parent.stem
    else:
        stem = module_def.c_path.stem

    old_initializer = f"PyInit_{stem}"
    new_initializer = module_def.initializer_name

    old_text = module_def.c_path.read_text(encoding="utf8")
    new_text: str = old_text.replace(
        f"{old_initializer}",
        f"{new_initializer}",
        count=3 if module_def.is_package else 2,
    )

    new_text: str = new_text.replace(
        f"extern int __pyx_module_is_main_{stem};\nint __pyx_module_is_main_{stem} = ",
        f"static int __pyx_module_is_main_{stem} = ",
        count=1,
    )

    if old_text != new_text:
        module_def.c_path.write_text(new_text, encoding="utf8")

    return dirty


def cythonize_package(
    package_name: str,
    package_paths: list[Path] | Path,
    preprocessors: list[BasePreprocessor] | None = None,
    working_path: Path = Path("./build/generated/"),
    language_level: int = 3,
    annotate_html: bool = False,
    annotate_coverage: bool = False,
    check_timestamps: bool = True,
    verbose: bool = False,
    quiet: bool = False,
) -> list[ModuleDef]:
    """
    Cythonize and patch python files in a package.
    This includes these main steps (in order):
    1. Run `preprocessors` on the package
    2. Cythonize each module to generate a `*.c` file
    3. Patch each `*.c` file to replace their `PyInit_*` functions
    4. Generate `bootstrap.pyx` and `bootstrap.h`

    NOTE:
      Namespace packages are compiled together as if they were a normal package.

    NOTE:
      Preprocessors are free to cythonize the modules on their own.
      The content of the files is irrelivant, so long as cython can compile it.

    NOTE:
      If present, the `__cythontools_main__` module-level function
      will be used when executing the module directly, e.g. `python -m cythontools.package`.

      The only exception is the top-most package, i.e. `python -m cythontools`
      *will not* work. This is because it is the only module imported
      with the interpreters's builtin extension `Loader`.

      The `MainPreprocessor` will automatically enable most modules by replacing
        ```py
        if __name__ == '__main__':
        ```
      with
        ```py
        def __cythontools_main__():
        ```

    NOTE:
      The `CYTHON_NO_PYINIT_EXPORT` C macro should be defined when compiling all extensions
      except `bootstrap` - it causes their `PyInit_*` functions to be exported, which we don't want.

    NOTE:
      On import, all submodules have their `ModuleSpec`, `ModuleDef` and `Module` initialized.
      The `Module` contents are not executed until the `Loader` requests their execution.

      The two exception are `bootstrap`, which is executed by the interpreter,
      and top-most package, which will be executed as a last step in `bootstrap`.
      The latter will also replace `bootstrap` in `sys.modules`.

    :param package_name: Final name of the package
    :param package_paths: Path or paths to the package that will be compiled
    :param preprocessors: List of `BasePreprocessor` to run on the source code before compiling, defaults to None
    :param working_path: Working path for generated files, defaults to Path("./build/generated/")
    :param language_level: Major python version to assume in cython - must be 2 or 3, defaults to 3
    :param annotate_html: Generate html annotations which show python usage after cythonization, defaults to False
    :param annotate_coverage: Include coverage information in annotated html files, defaults to False, implies `annotate_html=True`
    :param check_timestamps: Cythonize only if changes are detected, defaults to True
    :param verbose: Include debug logs, defaults to False
    :param quiet: Do not emit logs, defaults to False
    :raises ValueError: If both `verbose=True` and `quiet=True`
    :return: List of cythonized `ModuleDef`
    """

    if isinstance(package_paths, Path):
        package_paths = [package_paths]

    if preprocessors is None:
        preprocessors = []

    if annotate_coverage:
        annotate_html = True

    if verbose and quiet:
        raise ValueError("Verbose and quiet are mutually exclusive.")

    init_count = sum(
        (package_path / "__init__.py").is_file() for package_path in package_paths
    )

    if len(package_paths) > 1:
        assert init_count == 0, "All namespace packages must omit their '__init__.py'"

    module_names: set[str] = set()

    module_defs: list[ModuleDef] = []
    for package_path in package_paths:
        for module_path in package_path.rglob("*.*"):
            if module_path.suffix not in {".py", ".pyx", ".pxd"}:
                continue

            relative_path = module_path.relative_to(package_path.parent)

            if is_package := module_path.stem == "__init__":
                module_name = relative_path.parent
            else:
                module_name = relative_path

            module_name = (
                str(module_name.with_suffix(""))
                .replace("/", ".")
                .replace("\\", ".")
                .strip(".")
            )

            if (is_package, module_name) in module_names:
                continue

            module_names.add((is_package, module_name))

            initializer_name = build_initializer_name(
                is_package=is_package, module_name=module_name
            )

            c_path = (working_path / relative_path).with_suffix(".c")
            c_path.parent.mkdir(parents=True, exist_ok=True)

            py_source = None
            if (py_path := module_path.with_suffix(".py")) and py_path.exists():
                py_source = py_path.read_text()

            pyx_source = None
            if (pyx_path := module_path.with_suffix(".pyx")) and pyx_path.exists():
                pyx_source = pyx_path.read_text()

            pxd_source = None
            if (pxd_path := module_path.with_suffix(".pxd")) and pxd_path.exists():
                pxd_source = pxd_path.read_text()

            module_defs.append(
                ModuleDef(
                    is_package=is_package,
                    module_name=module_name,
                    initializer_name=initializer_name,
                    c_path=c_path,
                    py_source=py_source,
                    pyx_source=pyx_source,
                    pxd_source=pxd_source,
                )
            )

    for idx, module_spec in enumerate(module_defs):
        if module_spec.module_name == package_name:
            root_idx = idx
            break
    else:
        root_idx = len(module_defs)
        namespace_init_path = working_path / package_name / "__init__.py"

        module_defs.append(
            ModuleDef(
                is_package=True,
                module_name=package_name,
                initializer_name=build_initializer_name(
                    is_package=True, module_name=package_name
                ),
                c_path=namespace_init_path.with_suffix(".c"),
                py_source="",
            )
        )

    for preprocessor in preprocessors:
        module_defs = preprocessor.process_package(module_defs)

    dirty = False
    for module_def in module_defs:
        module_def.save()

        dirty |= cythonize_module(
            module_def,
            language_level=language_level,
            annotate_html=annotate_html,
            annotate_coverage=annotate_coverage,
            check_timestamps=check_timestamps,
            verbose=verbose,
            quiet=quiet,
        )

    bootstrap_path = working_path / "bootstrap"
    c_path = bootstrap_path.with_suffix(".c")
    header_path = bootstrap_path.with_suffix(".h")
    cython_path = bootstrap_path.with_suffix(".pyx")
    html_path = bootstrap_path.with_suffix(".html")

    try:
        generated_last_modified = max(
            Utils.modification_time(header_path),
            Utils.modification_time(cython_path),
            Utils.modification_time(c_path),
        )
        if annotate_html:
            generated_last_modified = max(
                generated_last_modified, Utils.modification_time(html_path)
            )
        source_last_modified = max(
            module_def.last_modified for module_def in module_defs
        )
        dirty |= not check_timestamps or generated_last_modified < source_last_modified
    except OSError:
        dirty = True

    bootstrap_def = ModuleDef(
        is_package=True,
        module_name=package_name,
        initializer_name=f"PyInit_{package_name}",
        c_path=c_path,
    )

    if not dirty:
        module_defs.append(bootstrap_def)
        return module_defs

    finder_name = "MyMetaFinder"
    loader_name = "MyLoader"

    cython_code = "cdef extern from 'bootstrap.h':\n"
    header_code = (
        "#undef CYTHON_NO_PYINIT_EXPORT\n"
        "#ifdef __cplusplus\n"
        'extern "C" {\n'
        "#endif // __cplusplus\n"
    )
    for spec in module_defs:
        header_code += f"    void* {spec.initializer_name}(void);\n"
        cython_code += f"    void* {spec.initializer_name}()\n"

    header_code += "#ifdef __cplusplus\n}\n#endif // __cplusplus\n"

    cython_code += (
        f"\n"
        f"cdef extern from 'Python.h':\n"
        f"    object PyModule_FromDefAndSpec(void* module_def, object spec)\n"
        f"    int PyModule_ExecDef(object module, void* module_def)\n"
        f"    void* PyModule_GetDef(object module)\n"
        f"\n"
        f"cdef void bootstrap():\n"
        f"    import sys\n"
        f"\n"
        f"    from importlib.abc import Loader, MetaPathFinder\n"
        f"    from importlib.machinery import ModuleSpec\n"
        f"\n"
        f"    class {finder_name}(MetaPathFinder):\n"
        f"        @classmethod\n"
        f"        def find_spec(cls, fullname not None, path, target=None):\n"
        f"            cdef tuple module_info = module_infos.get(fullname)\n"
        f"            if module_info is None:\n"
        f"                return None\n"
        f"            return module_info[0]\n"
        f"\n"
        f"    class {loader_name}(Loader):\n"
        f"        @classmethod\n"
        f"        def get_code(cls, fullname not None):\n"
        f"            return (\n"
        f"                f'import {{fullname}}\\n'\n"
        f"                f'try:\\n'\n"
        f"                f'    from {{fullname}} import __cythontools_main__\\n'\n"
        f"                f'except ImportError:\\n'\n"
        f"                f'    __cythontools_main__ = None\\n'\n"
        f"                f'\\n'\n"
        f"                f'if __cythontools_main__ is not None:\\n'\n"
        f"                f'    __cythontools_main__()\\n'\n"
        f"            )\n"
        f"        @classmethod\n"
        f"        def create_module(cls, spec not None):\n"
        f"            cdef tuple module_info = module_infos.get(spec.name)\n"
        f"            if module_info is None:\n"
        f"                return None\n"
        f"            return module_info[1]\n"
        f"\n"
        f"        @classmethod\n"
        f"        def exec_module(cls, module not None):\n"
        f"            PyModule_ExecDef(module, PyModule_GetDef(module))\n"
        f"\n"
    )
    for idx, spec in enumerate(module_defs):
        cython_code += (
            f"    cdef str name_{idx} = {spec.module_name!r}\n"
            f"    cdef object spec_{idx} = ModuleSpec(name_{idx}, {loader_name}, is_package={spec.is_package})\n"
            f"    cdef void* module_def_{idx} = {spec.initializer_name}()\n"
            f"    cdef object module_{idx} = PyModule_FromDefAndSpec(module_def_{idx},  spec_{idx})\n"
            f"\n"
        )

    cython_code += "    cdef dict module_infos = {\n"
    cython_code += "".join(
        f"        name_{idx}: (spec_{idx}, module_{idx}),\n"
        for idx, _ in enumerate(module_defs)
    )
    cython_code += "    }\n\n"
    cython_code += (
        f"    sys.meta_path.insert(0, {finder_name})\n"
        f"    sys.modules[name_{root_idx}] = module_{root_idx}\n"
        f"    PyModule_ExecDef(module_{root_idx}, module_def_{root_idx})\n"
    )

    cython_code += "bootstrap()\n"

    header_path.write_text(header_code)
    cython_path.write_text(cython_code)

    compile(
        str(cython_path),
        full_module_name=package_name,
        output_file=c_path,
        module_name=package_name,
        language_level=language_level,
        annotate=annotate_html,
        annotate_coverage_xml=annotate_coverage,
        timestamps=check_timestamps,
        verbose=verbose,
        quiet=quiet,
    )

    module_defs.append(bootstrap_def)
    return module_defs
