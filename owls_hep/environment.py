"""Provides facilities for loading an execution environment, in particular the
parallelization backend and the persistent cache.
"""


# System imports
from collections import defaultdict
from os.path import exists, isfile, splitext

# owls-cache imports
from owls_cache.persistent.caches.fs import FileSystemPersistentCache

# owls-parallel imports
from owls_parallel.backends.multiprocessing import \
    MultiprocessingParallelizationBackend

# owls-hep imports
from owls_hep.module import load as load_module


def load(path = None):
    """Loads an execution environment, either from a Python module or by using
    default values.

    Modules provided to this method may export any of the following symbols:

        - persistent_cache
        - parallelization_backend

    If neither the module nor its overrides exports a given symbol, it will be
    replaced by a default.

    Args:
        path: The path to the environment configuration file, or None for the
            default environment.  If a file with the same path but the `.py`
            extension replaced with `.local.py` is present, it will be loaded
            after the main file is loaded and it's symbols will take
            precedence.

    Returns:
        A tuple of the form (persistent_cache, parallelization_backend).
    """
    # Set up symbols we want to look for
    symbols = ('persistent_cache', 'parallelization_backend')

    # Set up a dictionary to track values
    values = defaultdict(lambda: 'unset')

    # Load the configuration (if any)
    if path is not None:
        # Check that it exists
        if not exists(path) or not isfile(path):
            raise OSError('invalid environment configuration path')

        # Load the module
        module = load_module(path)

        # Extract attributes
        for symbol in symbols:
            values[symbol] = getattr(module, symbol, 'unset')

        # Check for local overrides
        local_path = '{0}.local.py'.format(splitext(path)[0])
        if exists(local_path) and isfile(local_path):
            # Load the module
            module = load_module(local_path)

            # Extract attributes
            for symbol in symbols:
                values[symbol] = getattr(module, symbol, 'unset')

    # Create results
    persistent_cache = values['persistent_cache']
    parallelization_backend = values['parallelization_backend']

    # Check if a default persistent cache is needed
    if persistent_cache == 'unset':
        persistent_cache = FileSystemPersistentCache()

    # Set parallelization backend
    if parallelization_backend == 'unset':
        parallelization_backend = MultiprocessingParallelizationBackend()

    # All done
    return (persistent_cache, parallelization_backend)
