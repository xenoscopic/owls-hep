"""Provides facilities for setting the OWLS execution environment, in
particular the parallelization backend and the persistent cache.  The
environment is loaded from a configuration file, allowing for the
locally-overridable behavior of owls_hep.config.load.
"""


# System imports
from sys import version_info
from uuid import uuid4
from os.path import exists, isfile, splitext

# owls-cache imports
from owls_cache.persistent import set_persistent_cache
from owls_cache.persistent.caches.fs import FileSystemPersistentCache

# owls-parallel imports
from owls_parallel import set_parallelization_backend
from owls_parallel.backends.multiprocessing import \
    MultiprocessingParallelizationBackend


# Define a method which can load modules by path
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
    """Loads and configures the OWLS execution environment from a configuration
    script.

    The configuration script should be a Python module.  It may export any of
    the following symbols:

    - persistent_cache: The persistent cache to use (defaults to a file system
        cache if not present)
    - parallelization_backend: The parallelization backend to use (defaults to
        a multiprocessing backend if not present)

    If a file with the same path but the `.py` extension replaced with
    `.local.py` is present, any symbols it exports will override those in the
    main file.

    If None is passed for path, then the default environment is set up.

    If the path does not exist, an OSError is raised.

    Args:
        path: The path to the environment configuration file, or None for the
            default environment
    """
    # Create defaults
    persistent_cache = FileSystemPersistentCache()
    parallelization_backend = MultiprocessingParallelizationBackend()

    # Load the configuration (if any)
    if path is not None:
        # Check that it exists
        if not exists(path) or not isfile(path):
            raise OSError('invalid environment configuration path')

        # Load it
        module = _load_module(path)

        # Extract components
        if hasattr(module, 'persistent_cache'):
            persistent_cache = module.persistent_cache
        if hasattr(module, 'parallelization_backend'):
            parallelization_backend = module.parallelization_backend

        # Check for local overrides
        local_path = '{0}.local.py'.format(splitext(path)[0])
        if exists(local_path) and isfile(local_path):
            # Load the module
            local_module = _load_module(local_path)

            # Extract components
            if hasattr(local_module, 'persistent_cache'):
                persistent_cache = local_module.persistent_cache
            if hasattr(local_module, 'parallelization_backend'):
                parallelization_backend = local_module.parallelization_backend

    # Set parameters
    set_persistent_cache(persistent_cache)
    set_parallelization_backend(parallelization_backend)
