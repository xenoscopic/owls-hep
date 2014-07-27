"""Provides a configuration loader which allows user-specific overrides to
facilitate shared configuration amongst multiple analysts.
"""


# System imports
from os.path import splitext
from sys import version_info
from uuid import uuid4

# owls-config imports
from owls_config import load as _load_config


def load_config(path):
    """Provides an identical interface to the owls_config.load method, except
    that if file with the same path but extension `.local.yml` instead of
    `.yml` exists, it will be loaded after the `.yml` file, and its contents
    will overwrite those of the `.yml` file in the returned configuration.  If
    the `.yml` file does not exist, but the `.local.yml` does, then this method
    returns None.

    Overrides take place only at the top level of the configuration.

    Args:
        path: A path to a JSON file containing configuration information

    Returns:
        A Python OrderedDict representing the contents of the configuration.
        Returns None if the configuration path does not exist or is not a file.
    """
    # Load the initial configuration
    result = _load_config(path)

    # If it was empty or non-existant, just bail
    if result is None:
        return

    # Now try to load the local override
    local = _load_config('{0}.local.yml'.format(splitext(path)[0]))

    # Merge configuration, if any
    if local is not None:
        result.update(local)

    # All done
    return result


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


def load_module(path):
    """Loads a Python module by path, returning the module object.

    Args:
        path: The full path to the .py file

    Returns:
        A module object.
    """
    return _load_module(path)
