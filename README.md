# Packages in cython

Example code for compiling multiple Cython packages in a single extension module

These are the key points:
1. After generating the .c files with Cython and rename the PyInit functions to avoid conflicts
2. Make a cython file which implements a Loader and MetaPathFinder (see `bootstrap.pyx`). Their functions are fairly simple if you generate some code for your modules (see `modules.pyx`):
   - `MyMetaFinder.find_spec` just creates the specs for our modules. The most important thing here is to give it `is_package=True` for packages, otherwise certain imports will break
   - `MyLoader.create_module` takes the spec we created, calls the appropriate PyInit function and passes them both to `PyModule_FromDefAndSpec`. This creates the module object, but does not initialize it
   - `MyLoader.exec_module` calls `PyModule_ExecDef` on the module and its module def. This initializes the module object; once it has been initialized once, python will cache it and this won't be called again (for this module)

3. `bootstrap.pyx`'s main role is to add our `MetaPathFinder` to `sys.meta_path` and will be the "real" module in the extension, from the perspective of the interpreter. Afterwards, we have to create and execute our real top-level module and replace it in `sys.modules`. We can't do this for the rest of the modules because we need to respect the import order - the finder/loader combo handles this for us

4. Define `CYTHON_NO_PYINIT_EXPORT` when compiling the generated .c files - this will disable the exported PyInit function that usually initialized the modules. `bootstrap.pyx` will explicitely undef it, so we have exactly one exported PyInit function