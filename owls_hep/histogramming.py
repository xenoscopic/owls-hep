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


class Distribution(object):
    """Represents a histogrammable distribution.
    """

    def __init__(self,
                 name,
                 expressions,
                 binnings,
                 x_label = None,
                 y_label = None):
        """Initializes a new instance of the Distribution class.

        Args:
            name: A name by which to refer to the histogram
            expressions: See owls.data.histogramming.histogram
            binnings: See owls.data.histogramming.histogram
            x_label: The ROOT TLatex label to use for the x-axis
            y_label: The ROOT TLatex label to use for the y-axis
        """
        # Store parameters
        self.name = name
        self.expressions = expressions
        self.binnings = binnings
        self.x_label = x_label
        self.y_label = y_label

    def __hash__(self):
        """Returns a hash of those quantities affecting the resultant
        computation.
        """
        return hash((self.expressions,
                     self.binnings,
                     self.x_label,
                     self.y_label))


def _numpy_to_root_histogram(histogram,
                             name = None,
                             title = None,
                             x_label = None,
                             y_label = None):
    """Converts a NumPy histogram object into a ROOT histogram object.

    Args:
        histogram: A NumPy histogram (i.e. the tuple returned by histogramdd)
            of dimension <= 3
        name: The name to use for the ROOT histogram.  If None (the default) a
            random and unique id will be used.
        title: The title to use for the ROOT histogram.  If None (the default)
            the name of the histogram will be used.
        x_label: The TLatex x-axis label to use for the ROOT histogram.  If
            None (the default), no x-axis label will be set.
        y_label: The TLatex y-axis label to use for the ROOT histogram.  If
            None (the default), no y-axis label will be set.

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

    # Set axis labels if necessary
    if x_label is not None:
        result.GetXaxis().SetTitle(x_label)
    if y_label is not None:
        result.GetYaxis().SetTitle(y_label)

    # Calculate errors.  In the event that Sumw2 is on automatically, the
    # errors will not be updated when we call SetBinContent, so we need to
    # clear them and update them.  Instead of using the False flag to Sumw2, we
    # use a more manual method to maintain compatibility with ROOT 5.32.
    if result.GetSumw2N() > 0:
        result.GetSumw2().Set(0)
    result.Sumw2()

    return result


# Dummy function to return fake values when parallelizing
def _parallel_mocker(process, region, distribution):
    # Create a unique id
    name_title = uuid4().hex

    # Create a bogus histogram
    return TH1F(name_title, name_title, 1, 0, 1)


# Histogram parallelization mapper.  We map/group based on process to maximize
# data loading caching.
def _parallel_mapper(process, region, distribution):
    return (process,)


# Histogram argument extractor for calling by args/kwargs and extracting region
# and expressions
def _parallel_extractor(process, region, distribution):
    return (region, distribution)


# Histogram parallelization batcher
def _parallel_batcher(function, args_kwargs):
    # Create a combined set of properties necessary for all calls
    all_properties = set()

    # Go through all args/kwargs pairs
    for args, kwargs in args_kwargs:
        # Extract region and expressions
        region, distribution = _parallel_extractor(*args, **kwargs)

        # Add region properties
        all_properties.update(properties(region.weighted_selection()))

        # Add expression properties
        if isinstance(distribution.expressions, string_types):
            all_properties.update(properties(distribution.expressions))
        else:
            all_properties.update(*(
                properties(e)
                for e
                in distribution.expressions
            ))

    # Go through all args/kwargs pairs and call the function
    for args, kwargs in args_kwargs:
        # Call the functions with load hints
        kwargs['_load_hints'] = all_properties
        function(*args, **kwargs)


# Histogram persistent cache mapper
def _cache_mapper(process, region, distribution, _load_hints = None):
    return (process, region, distribution)


@parallelized(_parallel_mocker, _parallel_mapper, _parallel_batcher)
@styled
@persistently_cached('owls_hep.histogramming.histogram', _cache_mapper)
def histogram(process, region, distribution, _load_hints = None):
    """Generates a ROOT histogram of the specified event properties in the
    given region.

    The style of the process is applied to the result.

    Args:
        process: The process whose events should be histogrammed
        region: The region whose weighting/selection should be applied
        distribution: The distribution to histogram
        _load_hints: A set of properties which the histogram will load in
            addition to the minimum set required so that future calls will
            hit transiently cached loads and evaluations (this is a private
            argument for parallelization optimization and should not be
            provided by users)

    Returns:
        A ROOT histogram.
    """
    # Compute weighted selection
    weighted_selection = region.weighted_selection()

    # Compute required data properties
    required_properties = _load_hints if _load_hints is not None else set()

    # Add in those properties necessary to evaluate the weighted selection
    required_properties.update(properties(weighted_selection))

    # Add in those properties necessary to evaluate expressions
    if isinstance(distribution.expressions, string_types):
        required_properties.update(properties(distribution.expressions))
    else:
        required_properties.update(*(
            properties(e)
            for e
            in distribution.expressions
        ))

    # Load data
    data = process.load(required_properties)

    # Create the NumPy histogram and convert it to a ROOT histogram
    return _numpy_to_root_histogram(
        _histogram(
            data,
            weighted_selection,
            distribution.expressions,
            distribution.binnings
        ),
        x_label = distribution.x_label,
        y_label = distribution.y_label
    )
