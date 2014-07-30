"""Provides method for efficiently counting events in a region.
"""


# owls-cache imports
from owls_cache.persistent import cached as persistently_cached

# owls-data imports
from owls_data.expression import properties
from owls_data.counting import count as _count

# owls-parallel imports
from owls_parallel import parallelized


@parallelized(lambda p, r: 1.0, lambda p, r: (p, r))
@persistently_cached('owls_hep.counting.count', lambda p, r: (p, r))
def count(process, region):
    """Computes the weighted event count of a process in a region.

    Args:
        process: The process whose events should be counted
        region: The region whose weighting/selection should be applied

    Returns:
        The weighted event count in the region.
    """
    # Compute weighted selection
    weighted_selection = region()

    # Compute the weighted selection properties
    region_properties = properties(weighted_selection)

    # Compute the count
    return _count(process(region_properties), weighted_selection)
