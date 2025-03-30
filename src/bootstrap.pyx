import sys

from importlib.abc import Loader, MetaPathFinder

# PyInit exporting is disabled for all modules, but we want it for this one
cdef extern from "bootstrap.h":
    pass

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

initialize_modules(MyLoader())
