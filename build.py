from __future__ import annotations

import textwrap
import subprocess
import sysconfig

from dataclasses import dataclass
from pathlib import Path

py_modules: list[Path] = []
c_modules: list[Path] = []


root_path = Path("./src/root/")
parent_path = root_path.parent
for path in root_path.rglob("*.py"):
    py_modules.append(path)
    c_modules.append(path.with_suffix(".c"))


subprocess.run(
    ["py", "-m", "cython", "-3", *map(str, py_modules)], shell=True, check=True
)


@dataclass(frozen=True, kw_only=True)
class ModuleSpec:
    module_name: str
    function_name: str
    is_package: bool


module_specs: list[ModuleSpec] = []
for c_module in c_modules:
    is_package = c_module.stem == "__init__"

    relative_path = c_module.relative_to(parent_path)
    if is_package:
        relative_path = relative_path.parent

    module_name = (
        str(relative_path.with_suffix(""))
        .replace("/", ".")
        .replace("\\", ".")
        .strip(".")
    )
    function_name = module_name.replace(".", "___")
    if is_package:
        function_name += "___init___"

    old_name = f"PyInit_{relative_path.stem}"
    new_name = f"PyInit_{function_name}"

    old_text = c_module.read_text(encoding="utf8")
    new_text = old_text.replace(old_name, new_name)
    if old_text != new_text:
        c_module.write_text(new_text, encoding="utf8")

    module_specs.append(
        ModuleSpec(
            module_name=module_name, function_name=new_name, is_package=is_package
        )
    )


def make_find_spec() -> str:
    code = ""
    packages = set()
    modules = set()
    for spec in module_specs:
        if spec.is_package:
            packages.add(spec.module_name)
        else:
            modules.add(spec.module_name)

    code = (
        f"cdef bint is_package = module_name in {packages!r}\n"
        f"if not is_package and module_name not in {modules!r}:\n"
        f"    return None\n"
        f"return ModuleSpec(\n"
        f"    module_name,\n"
        f"    loader,\n"
        f"    is_package=is_package\n"
        f")\n"
    )
    code = textwrap.indent(code, prefix="    ")
    return f"cpdef object find_spec(str module_name):\n{code}"


def make_create_module() -> str:
    declarations = ""
    code = ""
    for spec in module_specs:
        if code:
            code += "el"
        code += (
            f'if spec.name == "{spec.module_name}":\n'
            f"    module_def = {spec.function_name}()\n"
        )

    code = "cdef void* module_def\n" + code

    for spec in module_specs:
        declarations += f"cdef extern void* {spec.function_name}()\n"

    code += "else:\n    return None\n"
    code += "return PyModule_FromDefAndSpec(\n    module_def,\n    spec\n)\n"
    code = textwrap.indent(code, prefix="    ")
    return f"{declarations}\ncpdef object create_module(object spec):\n{code}"


Path("src/modules.pyx").write_text(
    f"from importlib.machinery import ModuleSpec\n\n"
    f"ctypedef void*(*init_fn)()\n"
    f"cdef extern from \"Python.h\":\n"
    f"    object PyModule_FromDefAndSpec(void* module_def, object spec)\n"
    f"    int PyModule_ExecDef(object module, void* module_def)\n"
    f"    void* PyModule_GetDef(object module)\n\n"
    f"cdef object loader\n\n"
    f"{make_find_spec()}\n"
    f"{make_create_module()}",
    encoding="utf8",
)

subprocess.run(
    [
        "py",
        "-m",
        "cython",
        "-3",
        "src/bootstrap.pyx",
        "--module-name",
        root_path.stem,
    ],
    shell=True,
    check=True,
)

include_path = sysconfig.get_path("include")
libs_path = sysconfig.get_config_var("LIBDIR")

subprocess.run(
    [
        "clang-cl",
        "/LD",
        "/DCYTHON_NO_PYINIT_EXPORT",
        "src/bootstrap.c",
        *map(str, c_modules),
        f"/I{include_path}",
        "/link",
        "/out:root.pyd",
        f"/LIBPATH:{libs_path}",
    ],
    shell=True,
    check=True,
)
