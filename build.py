from __future__ import annotations

import textwrap
import subprocess
import sysconfig
import sys

from dataclasses import dataclass
from pathlib import Path

# import builtins
# for obj in object.__subclasses__():
#     if obj.__name__ != "moduledef":
#         continue

#     print(obj, obj.__module__)

# exit(0)

py_modules: list[Path] = []
c_modules: list[Path] = []

root_path = Path("./src/root/")
parent_path = root_path.parent
for path in root_path.rglob("*.py"):
    py_modules.append(path)
    c_modules.append(path.with_suffix(".c"))


subprocess.run(
    [sys.executable, "-m", "cython", "-3", "-D", *map(str, py_modules)],
    check=True,
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


def generate_code() -> str:
    declarations = ""
    module_defs = "cdef dict module_defs = {\n"
    for spec in module_specs:
        declarations += f"cdef extern void* {spec.function_name}()\n"
        module_defs += f"    {spec.module_name!r}: {spec.function_name}(),\n"
    module_defs += "}\n"

    body = ""
    root_idx: int
    for idx, spec in enumerate(module_specs):
        if spec.module_name == root_path.stem:
            root_idx = idx

        body += (
            f"cdef str name_{idx} = {spec.module_name!r}\n"
            f"cdef object spec_{idx} = ModuleSpec(name_{idx}, loader, is_package={spec.is_package})\n"
            f"cdef void* module_def_{idx} = {spec.function_name}()\n"
            f"cdef object module_{idx} = PyModule_FromDefAndSpec(module_def_{idx},  spec_{idx})\n"
            f"\n"
        )

    body += "global module_infos\n"
    body += "module_infos = {\n"
    for idx, _ in enumerate(module_specs):
        body += f"    name_{idx}: (spec_{idx}, module_{idx}),\n"
    body += "}\n\n"

    body += (
        f"PyModule_ExecDef(module_{root_idx}, module_def_{idx})\n"
        f"sys.modules[name_{root_idx}] = module_{root_idx}\n"
    )

    body = textwrap.indent(body, prefix="    ")
    return (
        f"import sys\n"
        f"\n"
        f"from importlib.machinery import ModuleSpec\n"
        f"\n"
        f"ctypedef object(*init_fn)()\n"
        f'cdef extern from "Python.h":\n'
        f"    object PyModule_FromDefAndSpec(void* module_def, object spec)\n"
        f"    int PyModule_ExecDef(object module, void* module_def)\n"
        f"    void* PyModule_GetDef(object module)\n"
        f"\n"
        f"{declarations}\n"
        f"cdef dict module_infos\n"
        f"cdef void initialize_modules(object loader):\n"
        f"{body}\n"
        f"cpdef object find_spec(str module_name):\n"
        f"    cdef tuple module_info = module_infos.get(module_name)\n"
        f"    if module_info is None:\n"
        f"        return None\n"
        f"    return module_info[0]\n"
        f"\n"
        f"cpdef object create_module(object spec):\n"
        f"    cdef tuple module_info = module_infos.get(spec.name)\n"
        f"    if module_info is None:\n"
        f"        return None\n"
        f"    return module_info[1]\n"
        f"\n"
        f"cpdef void exec_module(object module):\n"
        f"    PyModule_ExecDef(module, PyModule_GetDef(module))\n"
    )


Path("src/modules.pyx").write_text(
    generate_code(),
    encoding="utf8",
)

subprocess.run(
    [
        sys.executable,
        "-m",
        "cython",
        "-3",
        "-D",
        "src/bootstrap.pyx",
        "--module-name",
        root_path.stem,
    ],
    check=True,
)

include_path = sysconfig.get_path("include")
libs_path = sysconfig.get_config_var("LIBDIR")

if sys.platform == "win32":
    subprocess.run(
        [
            "clang-cl",
            "/LD",
            "/DCYTHON_NO_PYINIT_EXPORT",
            "src/bootstrap.c",
            *map(str, c_modules),
            f"/I{include_path}",
            "/link",
            f"/out:{root_path.stem}.pyd",
            f"/LIBPATH:{libs_path}",
        ],
        check=True,
    )
elif sys.platform == "linux":
    subprocess.run(
        [
            "clang",
            "-O3",
            "-fPIC",
            "-fwrapv",
            "-flto=thin",
            "-fno-strict-aliasing",
            "-fvisibility=hidden",
            "-shared",
            "-DCYTHON_NO_PYINIT_EXPORT",
            f"-I{include_path}",
            f"-L{libs_path}",
            f"-o{root_path.stem}.so",
            "src/bootstrap.c",
            *map(str, c_modules),
        ]
    )
