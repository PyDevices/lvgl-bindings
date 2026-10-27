"""Sphinx configuration for the LVGL documentation.

Everything shared by the PyDevices documentation projects (theme, top bar,
Markdown and docstring setup, the reference map) comes from pydevices-docs.
The site covers lvgl-bindings and the three packages built from it:
lvgl-python, lvgl-micropython and lvgl-circuitpython.
"""

from pydevices_docs import configure

globals().update(configure(
    "lvgl", __file__,
    repo="PyDevices/lvgl-bindings", edit_path="docs",
    version_file=None,
))

# Pages that describe how the generator was rebuilt, not how to use LVGL, and
# the data the API report reads. They stay in the repository, off the site.
exclude_patterns += [
    "README.md",
    "lvgl-bindings-rebuild-plan.md",
    "generator-migration.md",
    "baseline",
]
