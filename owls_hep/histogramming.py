"""Provides method for efficiently histogramming properties of events in a
region.
"""


# System imports
from uuid import uuid4

# ROOT imports
from ROOT import TH1F, TH2F, TH3F

# owls-cache imports
from owls_cache.persistent import cached as persistently_cached

# owls-data imports
from owls_data.expression import properties
from owls_data.histogramming import histogram as data_histogram

# owls-parallel imports
from owls_parallel import parallelized

# owls-hep imports
from owls_hep.process import load
from owls_hep.region import weighted_selection


def _numpy_to_root_histogram(histogram, name = None, title = None):
    """Converts a NumPy histogram object into a ROOT histogram object.

    Args:
        histogram: A NumPy histogram (i.e. the tuple returned by histogramdd)
            of dimension <= 3
        name: The name to use for the ROOT histogram.  If None (the default) a
            random and unique id will be used.
        title: The title to use for the ROOT histogram.  If None (the default)
            the name of the histogram will be used.

    Returns:
        An equivalent ROOT histogram, of the THND variety.
    """
    # Decompose the histogram tuple
    values, edges = histogram

    # Check that the number of dimensions is something ROOT can handle
    dimensions = len(edges)
    if dimensions < 1 or dimensions > 3:
        raise ValueError('ROOT can only handle histograms with 1 <= dimension '
                         '<= 3')

    # Figure out what we're going to do for name/title
    name = name or uuid4().hex
    title = title or name

    # Convert to the appropriate histogram class
    # TODO: Is there a better way than using floats for everything?  Perhaps we
    # can use Panda's eval() infrastructure to extract type information.
    # NOTE: The '- 3' on all of the n_bins arguments here is because we need to
    # subtract off our underflow/overflow constants (-inf, +inf) and because
    # the last entry in the array specifies the upper edge of the last bin.
    if dimensions == 1:
        # Create a 1-d histogram
        result = TH1F(name, title,
                      len(edges[0]) - 3, edges[0][1:-1])

        # Set values
        for x in xrange(0, values.shape[0]):
            result.SetBinContent(x, values[x])
    elif dimensions == 2:
        # Create a 2-d histogram
        result = TH2F(name, title,
                      len(edges[0]) - 3, edges[0][1:-1],
                      len(edges[1]) - 3, edges[1][1:-1])

        # Set values
        for x in xrange(0, values.shape[0]):
            for y in xrange(0, values.shape[1]):
                result.SetBinContent(x, y, values[x][y])
    else:
        # Create a 3-d histogram
        result = TH3F(name, title,
                      len(edges[0]) - 3, edges[0][1:-1],
                      len(edges[1]) - 3, edges[1][1:-1],
                      len(edges[2]) - 3, edges[2][1:-1])

        # Set values
        for x in xrange(0, values.shape[0]):
            for y in xrange(0, values.shape[1]):
                for z in xrange(0, values.shape[2]):
                    result.SetBinContent(x, y, z, values[x][y][z])

    # Calculate errors.  In the event that Sumw2 is on automatically, the
    # errors will not be updated when we call SetBinContent, so we need to
    # clear them and update them.  Instead of using the False flag to Sumw2, we
    # use a more manual method to maintain compatibility with ROOT 5.32.
    if result.GetSumw2N() > 0:
        result.GetSumw2().Set(0)
    result.Sumw2()

    return result


# TODO: Create proper dummy function
@parallelized(lambda p, r, e, b: 0, lambda p, r, e, b: p)
@persistently_cached
def histogram(process, region, expressions, binnings):
    """Generates a ROOT histogram of the specified event properties in the
    given region.

    The style of the process is applied to the result.

    Args:
        process: The process whose events should be histogrammed
        region: The region whose weighting/selection should be applied
        expressions: The expressions, in terms of the dataset variables, to
            histogram.  The length of this list determines the dimensionality
            of the histogram.  Each expression must be a string to evaluate
            using owls.data.evaluate.  A single expression string may be passed
            in for a 1-D histogram.
        binnings: An interable object of len(variables) representing binnings.
            Each element of bins must have one of two forms:

            A tuple of the form

                (low_bin_left_edge, high_bin_right_edge, n_bins)

            or a list of the form:

                [low_bin_left_edge,
                 second_bin_left_edge,
                 ...,
                 high_bin_right_edge]

            If passing in a single expression string (not an iterable of
            expression strings) for expressions, then binnings must be a single
            object of one of these two types.

    Returns:
        A ROOT histogram.
    """
    # Compute weighted selection
    region_weighted_selection = weighted_selection(region)

    # Compute the weighted selection properties
    region_properties = properties(region_weighted_selection)

    # Create the NumPy histogram
    numpy_result = data_histogram(
        load(process, region_properties),
        region_weighted_selection,
        expressions,
        binnings
    )

    # Compute the result
    result = _numpy_to_root_histogram(numpy_result)

    # Style it
    # TODO:

    # All done
    return result
