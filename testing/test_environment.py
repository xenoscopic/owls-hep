# System imports
import unittest
from os.path import join, dirname

# owls-cache imports
from owls_cache.persistent import get_persistent_cache
from owls_cache.persistent.caches.redis import RedisPersistentCache

# owls-parallel imports
from owls_parallel import get_parallelization_backend
from owls_parallel.backends.batch import BatchParallelizationBackend

# owls-hep imports
from owls_hep.environment import load


# Compute the path to the test configuration file
config_path = join(dirname(__file__), 'environment.py')


class TestLoading(unittest.TestCase):
    def test(self):
        # Load the environment
        load(config_path)

        # Make sure it is correct
        self.assertIsInstance(get_persistent_cache(), RedisPersistentCache)
        self.assertIsInstance(get_parallelization_backend(),
                              BatchParallelizationBackend)


# Run the tests if this is the main module
if __name__ == '__main__':
    unittest.main()
