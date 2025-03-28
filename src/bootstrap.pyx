import sys

from importlib.abc import Loader, MetaPathFinder
from importlib.util import spec_from_file_location
from importlib.machinery import ModuleSpec

# PyInit exporting is disabled for all modules, but we want it for this one
cdef extern from "bootstrap.h":
    pass

ctypedef void*(*init_fn)()
cdef extern from "Python.h":
    object PyModule_FromDefAndSpec(void* module_def, object spec)
    int PyModule_ExecDef(object module, void* module_def)
    void* PyModule_GetDef(object module)

cpdef exec_module(object module):
    PyModule_ExecDef(module, PyModule_GetDef(module))

class MyMetaFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        return find_spec(fullname)

class MyLoader(Loader):
    def create_module(self, spec):
        return create_module(spec)

    def exec_module(self, module):
        exec_module(module)
sys.meta_path.insert(0, MyMetaFinder())

loader = MyLoader()

spec = find_spec("root")
module = create_module(spec)
exec_module(module)
sys.modules["root"] = module

include "modules.pyx"
