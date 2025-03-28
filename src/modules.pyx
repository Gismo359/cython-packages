cpdef object find_spec(str module_name):
    cdef bint is_package = module_name in {'root', 'root.subpackage'}
    if not is_package and module_name not in {'root.file1', 'root.file2', 'root.subpackage.submodule1', 'root.file3', 'root.file4', 'root.subpackage.submodule2'}:
        return None
    return ModuleSpec(
        module_name,
        loader,
        is_package=is_package
    )

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
