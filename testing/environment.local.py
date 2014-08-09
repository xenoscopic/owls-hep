# System imports
from tempfile import mkdtemp

# owls-cache imports
from owls_cache.persistent.caches.redis import RedisPersistentCache

# owls-parallel imports
from owls_parallel.backends.batch import BatchParallelizationBackend, \
    qsub_submit, qsub_monitor


# Create redis cache
persistent_cache = RedisPersistentCache()


# Create batch parallelization backend
parallelization_backend = BatchParallelizationBackend(mkdtemp(),
                                                      qsub_submit,
                                                      qsub_monitor)
