"""Provides a function to load Python modules by path.
"""


# System imports
from sys import version_info
from uuid import uuid4


# Define a method which can load modules by path.  The exact method depends on
# the Python version.
_major_version = version_info[0]
_module_id = lambda: 'm{0}'.format(uuid4().hex)
if _major_version == 2:
    import imp

    def _load_module(path):
        return imp.load_source(_module_id(), path)
elif _major_version == 3:
    import importlib.machinery

    def _load_module(path):
        loader = importlib.machinery.SourceFileLoader(_module_id(), path)
        return loader.load_module()
else:
    raise RuntimeError('unable to manually load modules for this version of '
                       'Python')


def load(path):
    """Loads a Python module by path.

    Args:
        path: The path to the .py file

    Returns:
        The module object.
    """
    return _load_module(path)
