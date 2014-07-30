"""Provides facilities for setting the OWLS execution environment, in
particular the parallelization backend and the persistent cache.
"""


# System imports
from os.path import exists, isfile, splitext
from sys import version_info
from uuid import uuid4

# owls-cache imports
from owls_cache.persistent import get_persistent_cache, set_persistent_cache
from owls_cache.persistent.caches.fs import FileSystemPersistentCache

# owls-parallel imports
from owls_parallel import get_parallelization_backend, \
    set_parallelization_backend
from owls_parallel.backends.multiprocessing import \
    MultiprocessingParallelizationBackend


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


def load(path = None):
    """Loads and executes a script to set up the owls environment.

    If, after execution of the script, no persistent cache or parallelization
    backend is set, they will be set to the default.

    If a file with the same path but the `.py` extension replaced with
    `.local.py` is present, it will be loaded after the main file is loaded.

    If None is passed for path, then the default environment is set up.

    If the path is not None and does not exist, an OSError is raised.

    Args:
        path: The path to the environment configuration file, or None for the
            default environment
    """
    # Load the configuration (if any)
    if path is not None:
        # Check that it exists
        if not exists(path) or not isfile(path):
            raise OSError('invalid environment configuration path')

        # Load it
        _load_module(path)

        # Check for local overrides
        local_path = '{0}.local.py'.format(splitext(path)[0])
        if exists(local_path) and isfile(local_path):
            # Load the module
            local_module = _load_module(local_path)

    # Set persistent cache if it hasn't been set
    if get_persistent_cache() is None:
        set_persistent_cache(FileSystemPersistentCache())

    # Set parallelization backend
    if get_parallelization_backend() is None:
        set_parallelization_backend(MultiprocessingParallelizationBackend())
