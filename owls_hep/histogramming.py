"""Provides method for efficiently histogramming properties of events in a
region.
"""


# System imports
from uuid import uuid4

# Six imports
from six import string_types

# Pandas import
from pandas import merge

# ROOT imports
from ROOT import TH1F, TH2F, TH3F, TColor

# owls-cache imports
from owls_cache.persistent import cached as persistently_cached

# owls-data imports
from owls_data.expression import properties
from owls_data.histogramming import histogram as _histogram

# owls-parallel imports
from owls_parallel import parallelized

# owls-hep imports
from owls_hep.process import styled


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


# Dummy function to return fake values when parallelizing
def _dummy_histogram(process, region, expressions, binnings):
    # Create a unique id
    name_title = uuid4().hex

    # Create a bogus histogram
    return TH1F(name_title, name_title, 1, 0, 1)


# Histogram parallelization mapper
def _parallel_mapper(process, region, expressions, binnings):
    return (process,)


# Histogram argument extractor for calling by args/kwargs and extracting region
# and expressions
def _parallel_extractor(process, region, expressions, binnings):
    return (region, expressions)


# Histogram parallelization batcher
def _parallel_batcher(function, args_kwargs):
    # Create a combined set of properties necessary for all calls
    all_properties = set()

    # Go through all args/kwargs pairs
    for args, kwargs in args_kwargs:
        # Extract region and expressions
        region, expressions = _parallel_extractor(*args, **kwargs)

        # Add region properties
        all_properties.update(properties(region()))

        # Add expression properties
        if isinstance(expressions, string_types):
            all_properties.update(properties(expressions))
        else:
            all_properties.update(*(properties(e) for e in expressions))

    # Go through all args/kwargs pairs and call the function
    for args, kwargs in args_kwargs:
        # Call the functions with load hints
        kwargs['_load_hints'] = all_properties
        function(*args, **kwargs)


# Histogram persistent cache mapper
def _cache_mapper(process, region, expressions, binnings, _load_hints = None):
    return (process, region, expressions, binnings)


@parallelized(_dummy_histogram, _parallel_mapper, _parallel_batcher)
@styled
@persistently_cached('owls_hep.histogramming.histogram', _cache_mapper)
def histogram(process, region, expressions, binnings, _load_hints = None):
    """Generates a ROOT histogram of the specified event properties in the
    given region.

    The style of the process is applied to the result.

    Args:
        process: The process whose events should be histogrammed
        region: The region whose weighting/selection should be applied
        expressions: See owls.data.histogramming.histogram
        binnings: See owls.data.histogramming.histogram
        _load_hints: A set of properties which the histogram will load in
            addition to the minimum set required so that future calls will
            hit transiently cached loads and evaluations (this is a private
            argument for parallelization optimization and should not be
            provided by users)

    Returns:
        A ROOT histogram.
    """
    # Compute weighted selection
    weighted_selection = region()

    # Compute required data properties
    required_properties = _load_hints if _load_hints is not None else set()

    # Add in those properties necessary to evaluate the weighted selection
    required_properties.update(properties(weighted_selection))

    # Add in those properties necessary to evaluate expressions
    if isinstance(expressions, string_types):
        required_properties.update(properties(expressions))
    else:
        required_properties.update(*(properties(e) for e in expressions))

    # Load data
    data = process(required_properties)

    # Create the NumPy histogram
    return _numpy_to_root_histogram(_histogram(
        data,
        weighted_selection,
        expressions,
        binnings
    ))
