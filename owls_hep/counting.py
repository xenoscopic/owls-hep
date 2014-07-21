"""Provides method for efficiently counting events in a region.
"""


# owls-cache imports
from owls_cache.persistent import cached as persistently_cached

# owls-data imports
from owls_data.expression import properties
from owls_data.counting import count as data_count

# owls-parallel imports
from owls_parallel import parallelized

# owls-hep imports
from owls_hep.process import load
from owls_hep.region import weighted_selection


@parallelized(lambda p, r: 1.0, lambda p, r: p)
@persistently_cached
def count(process, region):
    """Computes the weighted event count of a process in a region.

    Args:
        process: The process whose events should be counted
        region: The region whose weighting/selection should be applied

    Returns:
        The weighted event count in the region.
    """
    # Compute weighted selection
    region_weighted_selection = weighted_selection(region)

    # Compute the weighted selection properties
    region_properties = properties(region_weighted_selection)

    # Compute the count
    return data_count(
        load(process, region_properties),
        weighted_selection(region_weighted_selection)
    )
