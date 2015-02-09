"""Provides method for efficiently counting events in a region.
"""


# owls-cache imports
from owls_cache.persistent import cached as persistently_cached

# owls-parallel imports
from owls_parallel import parallelized

# owls-hep imports
from owls_hep.expression import properties, normalized
from owls_hep.calculation import Calculation


@parallelized(lambda p, r: 1.0, lambda p, r: (p, r))
@persistently_cached('owls_hep.counting.count', lambda p, r: (p, r))
def _count(process, region):
    """Computes the weighted event count of a process in a region.

    Args:
        process: The process whose events should be counted
        region: The region whose weighting/selection should be applied

    Returns:
        The weighted event count in the region.
    """
    # Compute weighted selection
    selection, weight = region.selection_weight()

    # Compute the weighted selection properties
    required_properties = set()
    required_properties.update(properties(selection))
    required_properties.update(properties(weight))

    # Load data
    data = process.load(required_properties)

    # Apply selection if specified
    if selection != '':
        data = data[data.eval(normalized(selection))]

    # Compute the weighted or unweighted count
    if weight != '':
        return data.eval(normalized(weight)).sum()
    else:
        return len(data)


class Count(Calculation):
    """A counting calculation.

    Although the need should not generally arise to subclass Count, all
    subclasses must return a floating point value for their result.
    """

    def __call__(self, process, region):
        """Counts the number of weighted events passing a region's selection.

        Args:
            process: The process whose weighted events should be counted
            region: The region providing selection/weighting for the count

        Returns:
            The number of weighted events passing the region's selection.
        """
        return _count(process, region)
