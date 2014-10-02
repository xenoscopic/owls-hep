"""Provides method for efficiently histogramming properties of events in a
region.
"""


# System imports
from uuid import uuid4
from functools import wraps

# Six imports
from six import string_types

# Pandas import
from pandas import merge

# rootpy imports
from rootpy.plotting import Hist, Hist2D, Hist3D

# owls-cache imports
from owls_cache.persistent import cached as persistently_cached

# owls-data imports
from owls_data.expression import properties
from owls_data.histogramming import histogram as _raw_histogram

# owls-parallel imports
from owls_parallel import parallelized

# owls-hep imports
from owls_hep.process import styled
from owls_hep.calculation import Calculation


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


def _numpy_to_root_histogram(histogram):
    """Converts a NumPy histogram object into a ROOT histogram object.

    Args:
        histogram: A NumPy histogram (i.e. the tuple returned by histogramdd)
            of dimension <= 3

    Returns:
        An equivalent ROOT histogram, of the THND variety.  Actually, a rootpy
        subclass.
    """
    # Decompose the histogram tuple
    values, edges = histogram

    # Check that the number of dimensions is something ROOT can handle
    dimensions = len(edges)
    if dimensions < 1 or dimensions > 3:
        raise ValueError('ROOT can only handle histograms with 1 <= dimension '
                         '<= 3')

    # Convert to the appropriate histogram class
    # TODO: Is there a better way than using floats for everything?  Perhaps we
    # can use Panda's eval() infrastructure to extract type information.
    # NOTE: We don't include the first and last bins in the specification to
    # ROOT because these are (-inf, +inf) to emulate underflow/overflow, and
    # ROOT implicitly adds underflow/overflow bins.
    # HACK: We have to convert the edge arrays to lists - though as small as
    # they are, this is probably not a performance issue
    if dimensions == 1:
        # Create a 1-d histogram
        result = Hist(list(edges[0][1:-1]))

        # Set values
        for x in xrange(0, values.shape[0]):
            result.SetBinContent(x, values[x])
    elif dimensions == 2:
        # Create a 2-d histogram
        result = Hist2D(list(edges[0][1:-1]), list(edges[1][1:-1]))

        # Set values
        for x in xrange(0, values.shape[0]):
            for y in xrange(0, values.shape[1]):
                result.SetBinContent(x, y, values[x][y])
    else:
        # Create a 3-d histogram
        result = Hist3D(list(edges[0][1:-1]),
                        list(edges[1][1:-1]),
                        list(edges[2][1:-1]))

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


# Decorator to convert numpy histograms to ROOT histograms using
# _numpy_to_root_histogram
def _rootify(f):
    # Create the wrapper function
    @wraps(f)
    def wrapper(*args, **kwargs):
        return _numpy_to_root_histogram(f(*args, **kwargs))
    return wrapper


# Dummy function to return fake values when parallelizing
def _parallel_mocker(process, region, distribution):
    return Hist(1, 0, 1)


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
@_rootify
@persistently_cached('owls_hep.histogramming.histogram', _cache_mapper)
def _histogram(process, region, distribution, _load_hints = None):
    """Generates a NumPy histogram of a distribution a process in a region.

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
        A NumPy histogram.
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
    return _raw_histogram(
        data,
        weighted_selection,
        distribution.expressions,
        distribution.binnings
    )


class Histogram(Calculation):
    """A histogramming calculation.
    """

    def __init__(self, distribution):
        """Initializes a new instance of the histogramming calculation.

        Args:
            distribution: The distribution which the calculation should
                generate when evaluated
        """
        # Store the distribution
        self._distribution = distribution

    def __call__(self, process, region):
        """Histograms weighted events passing a region's selection into a
        distribution.

        Args:
            process: The process whose weighted events should be histogrammed
            region: The region providing selection/weighting for the histogram

        Returns:
            A rootpy histogram representing the resultant distribution.
        """
        return _histogram(process, region, self._distribution)
