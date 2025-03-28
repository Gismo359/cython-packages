# cdef extern void * PyInit_Dummy_fake_root()
# cdef extern void * PyInit_Dummy_file1()
# cdef extern void * PyInit_Dummy_file2()
# cdef extern void * PyInit_Dummy_file3()
# cdef extern void * PyInit_Dummy_file4()
# 
# cdef extern from "Python.h":
#     object PyModule_FromDefAndSpec(void* module_def, object spec)
#     int PyModule_ExecDef(object module, void* module_def)
#     void* PyModule_GetDef(object module)