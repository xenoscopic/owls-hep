"""Provides facilities for setting the OWLS execution environment, in
particular the parallelization backend and the persistent cache.
"""


# System imports
from os.path import exists, isfile, splitext

# owls-cache imports
from owls_cache.persistent import set_persistent_cache
from owls_cache.persistent.caches.fs import FileSystemPersistentCache

# owls-parallel imports
from owls_parallel import set_parallelization_backend
from owls_parallel.backends.multiprocessing import \
    MultiprocessingParallelizationBackend

# owls-hep imports
from owls_hep.config import load_module


def load_environment(path = None):
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
    # Create container to store environment so that we needn't immediately
    # instantiate defaults (which will consume system resources)
    result = {}

    # Load the configuration (if any)
    if path is not None:
        # Check that it exists
        if not exists(path) or not isfile(path):
            raise OSError('invalid environment configuration path')

        # Load it
        module = load_module(path)

        # Extract components
        if hasattr(module, 'persistent_cache'):
            result['persistent_cache'] = module.persistent_cache
        if hasattr(module, 'parallelization_backend'):
            result['parallelization_backend'] = module.parallelization_backend

        # Check for local overrides
        local_path = '{0}.local.py'.format(splitext(path)[0])
        if exists(local_path) and isfile(local_path):
            # Load the module
            local_module = load_module(local_path)

            # Extract components
            if hasattr(local_module, 'persistent_cache'):
                result['persistent_cache'] = local_module.persistent_cache
            if hasattr(local_module, 'parallelization_backend'):
                result['parallelization_backend'] = \
                    local_module.parallelization_backend

    # Set persistent cache
    if 'persistent_cache' in result:
        set_persistent_cache(result['persistent_cache'])
    else:
        set_persistent_cache(FileSystemPersistentCache())

    # Set parallelization backend
    if 'parallelization_backend' in result:
        set_parallelization_backend(result['parallelization_backend'])
    else:
        set_parallelization_backend(MultiprocessingParallelizationBackend())
