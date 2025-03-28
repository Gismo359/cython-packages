cpdef object find_spec(str module_name):
    if module_name == "root.file1":
        return ModuleSpec(
            "root.file1",
            loader,
            is_package=False
        )
    elif module_name == "root.file2":
        return ModuleSpec(
            "root.file2",
            loader,
            is_package=False
        )
    elif module_name == "root.file3":
        return ModuleSpec(
            "root.file3",
            loader,
            is_package=False
        )
    elif module_name == "root.file4":
        return ModuleSpec(
            "root.file4",
            loader,
            is_package=False
        )
    elif module_name == "root":
        return ModuleSpec(
            "root",
            loader,
            is_package=True
        )
    elif module_name == "root.subpackage.submodule1":
        return ModuleSpec(
            "root.subpackage.submodule1",
            loader,
            is_package=False
        )
    elif module_name == "root.subpackage.submodule2":
        return ModuleSpec(
            "root.subpackage.submodule2",
            loader,
            is_package=False
        )
    elif module_name == "root.subpackage":
        return ModuleSpec(
            "root.subpackage",
            loader,
            is_package=True
        )
    return None

cdef extern void* PyInit_root___file1()
cdef extern void* PyInit_root___file2()
cdef extern void* PyInit_root___file3()
cdef extern void* PyInit_root___file4()
cdef extern void* PyInit_root___init___()
cdef extern void* PyInit_root___subpackage___submodule1()
cdef extern void* PyInit_root___subpackage___submodule2()
cdef extern void* PyInit_root___subpackage___init___()

cpdef object create_module(object spec):
    cdef void* module_def
    if spec.name == "root.file1":
        module_def = PyInit_root___file1()
    elif spec.name == "root.file2":
        module_def = PyInit_root___file2()
    elif spec.name == "root.file3":
        module_def = PyInit_root___file3()
    elif spec.name == "root.file4":
        module_def = PyInit_root___file4()
    elif spec.name == "root":
        module_def = PyInit_root___init___()
    elif spec.name == "root.subpackage.submodule1":
        module_def = PyInit_root___subpackage___submodule1()
    elif spec.name == "root.subpackage.submodule2":
        module_def = PyInit_root___subpackage___submodule2()
    elif spec.name == "root.subpackage":
        module_def = PyInit_root___subpackage___init___()
    else:
        return None
    return PyModule_FromDefAndSpec(
        module_def,
        spec
    )
