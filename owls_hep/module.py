"""Provides a dynamic module loading system, allowing one to load modules by
path.

There are two methods:

- `load`: Loads a module by path, optionally providing a definitions dictionary
  which will be accessible during the load.
- `definitions`: A function which will return the currently-set definitions
  dictionary when called from within a module being imported.  Definitions are
  stored on a stack, and the definitions corresponding to the current `load`
  call are returned by this function.  If called outside of a load call, this
  method returns None.
"""


# System imports
from sys import version_info
from uuid import uuid4
import threading
from contextlib import contextmanager


# Create a thread-local variable to track the current loading definitions
_thread_local = threading.local()
_thread_local.definitions = []


# Utility function to set the current thread's variables
def _push_definitions(d):
    _thread_local.definitions.append(d)


# Utility function to unset the current thread's variables
def _pop_definitions():
    _thread_local.definitions.pop()


def definitions():
    """Returns the currently-set variables dictionary when called from within
    the module being loaded.
    """
    if len(_thread_local.definitions) == 0:
        return None
    return _thread_local.definitions[-1]


# Define a method which can load modules by path.  The exact method depends on
# the Python version.
_major_version = version_info[0]
if _major_version == 2:
    import imp

    def _load_module(path):
        return imp.load_source(uuid4().hex, path)
elif _major_version == 3:
    import importlib.machinery

    def _load_module(path):
        loader = importlib.machinery.SourceFileLoader(uuid4().hex, path)
        return loader.load_module()
else:
    raise RuntimeError('unable to manually load modules for this version of '
                       'Python')


def load(path, definitions = {}):
    """Loads a Python module by path.

    Args:
        path: The path to the .py file
        definitions: A Python dictionary object which will be accessible during
            the module load via the owls_config.module.definitions method.

    Returns:
        The module object.
    """
    # Set definitions
    _push_definitions(definitions)

    # Load the module
    try:
        result = _load_module(path)
    except:
        raise
    finally:
        _pop_definitions()

    # All done
    return result
