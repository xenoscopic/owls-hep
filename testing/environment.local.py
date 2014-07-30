# System imports
from tempfile import mkdtemp

# owls-cache imports
from owls_cache.persistent import set_persistent_cache
from owls_cache.persistent.caches.redis import RedisPersistentCache

# owls-parallel imports
from owls_parallel import set_parallelization_backend
from owls_parallel.backends.batch import BatchParallelizationBackend, \
    qsub_submit, qsub_monitor


# Create redis cache
set_persistent_cache(RedisPersistentCache())


# Create batch parallelization backend
set_parallelization_backend(BatchParallelizationBackend(mkdtemp(),
                                                        qsub_submit,
                                                        qsub_monitor))
