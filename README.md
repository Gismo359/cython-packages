# Packages in cython

Example code for compiling multiple Cython packages in a single extension module

These are the key points:
1. After generating the .c files with Cython and rename the PyInit functions to avoid conflicts

2. The `modules.pyx` file is generated from the packages and all their modules. It has information and code that creates and executes all the modules which we are compiling

3. Make a cython file which implements a Loader and MetaPathFinder (see `bootstrap.pyx`). Their functions are fairly simple if you generate some code for your modules (see `modules.pyx`):
   - `MyMetaFinder.find_spec` returns the specs for each module. They are created in `initialize_modules` (see `modules.pyx`). The most important thing is to give it `is_package=True` for packages, otherwise certain imports will break
   - `MyLoader.create_module` returns the module handle for a given spec. Module handles are created (but not executed) in `initialize_modules` (see `modules.pyx`). The are created via `PyModule_FromDefAndSpec` by passing the moduledef and spec
   - `MyLoader.exec_module` calls `PyModule_ExecDef` on the module and its module def. This essentially runs the top-level code of the module and fills its dict. After this, the module will be fully initialized and the interpreter will cache the module handle

4. `bootstrap.pyx`'s main role is to add our `MetaPathFinder` to `sys.meta_path` and will be the module that the interpreter first loads and initializes. Afterwards, we have to execute our real top-level module/package and replace it in `sys.modules` (see `modules.pyx`). We can't do this for the rest of the modules because we need to respect the import order - the finder/loader combo handles this for us

5. Define `CYTHON_NO_PYINIT_EXPORT` when compiling the generated .c files - this will disable the exported PyInit function that usually initialized the modules. `bootstrap.pyx` will explicitely undef it, so we have exactly one exported PyInit function