from __future__ import annotations

import os


def build_wheel(wheel_directory, *_):
    from hatchling.builders.wheel import WheelBuilder
    from cythontools.build import hatch

    builder = WheelBuilder(os.getcwd())
    builder.plugin_manager.manager.register(hatch)

    return os.path.basename(
        next(builder.build(directory=wheel_directory, versions=["standard"]))
    )
