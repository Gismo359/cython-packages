import sys

from importlib.abc import Loader, MetaPathFinder

# PyInit exporting is disabled for all modules, but we want it for this one
cdef extern from "bootstrap.h":
    pass

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

include "modules.pyx"

loader = MyLoader()

spec = find_spec("root")
module = create_module(spec)
exec_module(module)
sys.modules["root"] = module