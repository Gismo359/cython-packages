import sys

from importlib.machinery import ModuleSpec

ctypedef object(*init_fn)()
cdef extern from "Python.h":
    object PyModule_FromDefAndSpec(void* module_def, object spec)
    int PyModule_ExecDef(object module, void* module_def)
    void* PyModule_GetDef(object module)

cdef extern void* PyInit_root___file1()
cdef extern void* PyInit_root___file2()
cdef extern void* PyInit_root___file3()
cdef extern void* PyInit_root___file4()
cdef extern void* PyInit_root___init___()
cdef extern void* PyInit_root___subpackage___submodule1()
cdef extern void* PyInit_root___subpackage___submodule2()
cdef extern void* PyInit_root___subpackage___init___()

cdef dict module_infos
cdef void initialize_modules(object loader):
    cdef str name_0 = 'root.file1'
    cdef object spec_0 = ModuleSpec(name_0, loader, is_package=False)
    cdef void* module_def_0 = PyInit_root___file1()
    cdef object module_0 = PyModule_FromDefAndSpec(module_def_0,  spec_0)

    cdef str name_1 = 'root.file2'
    cdef object spec_1 = ModuleSpec(name_1, loader, is_package=False)
    cdef void* module_def_1 = PyInit_root___file2()
    cdef object module_1 = PyModule_FromDefAndSpec(module_def_1,  spec_1)

    cdef str name_2 = 'root.file3'
    cdef object spec_2 = ModuleSpec(name_2, loader, is_package=False)
    cdef void* module_def_2 = PyInit_root___file3()
    cdef object module_2 = PyModule_FromDefAndSpec(module_def_2,  spec_2)

    cdef str name_3 = 'root.file4'
    cdef object spec_3 = ModuleSpec(name_3, loader, is_package=False)
    cdef void* module_def_3 = PyInit_root___file4()
    cdef object module_3 = PyModule_FromDefAndSpec(module_def_3,  spec_3)

    cdef str name_4 = 'root'
    cdef object spec_4 = ModuleSpec(name_4, loader, is_package=True)
    cdef void* module_def_4 = PyInit_root___init___()
    cdef object module_4 = PyModule_FromDefAndSpec(module_def_4,  spec_4)

    cdef str name_5 = 'root.subpackage.submodule1'
    cdef object spec_5 = ModuleSpec(name_5, loader, is_package=False)
    cdef void* module_def_5 = PyInit_root___subpackage___submodule1()
    cdef object module_5 = PyModule_FromDefAndSpec(module_def_5,  spec_5)

    cdef str name_6 = 'root.subpackage.submodule2'
    cdef object spec_6 = ModuleSpec(name_6, loader, is_package=False)
    cdef void* module_def_6 = PyInit_root___subpackage___submodule2()
    cdef object module_6 = PyModule_FromDefAndSpec(module_def_6,  spec_6)

    cdef str name_7 = 'root.subpackage'
    cdef object spec_7 = ModuleSpec(name_7, loader, is_package=True)
    cdef void* module_def_7 = PyInit_root___subpackage___init___()
    cdef object module_7 = PyModule_FromDefAndSpec(module_def_7,  spec_7)

    global module_infos
    module_infos = {
        name_0: (spec_0, module_0),
        name_1: (spec_1, module_1),
        name_2: (spec_2, module_2),
        name_3: (spec_3, module_3),
        name_4: (spec_4, module_4),
        name_5: (spec_5, module_5),
        name_6: (spec_6, module_6),
        name_7: (spec_7, module_7),
    }

    PyModule_ExecDef(module_4, module_def_7)
    sys.modules[name_4] = module_4

cpdef object find_spec(str module_name):
    cdef tuple module_info = module_infos.get(module_name)
    if module_info is None:
        return None
    return module_info[0]

cpdef object create_module(object spec):
    cdef tuple module_info = module_infos.get(spec.name)
    if module_info is None:
        return None
    return module_info[1]

cpdef void exec_module(object module):
    PyModule_ExecDef(module, PyModule_GetDef(module))
