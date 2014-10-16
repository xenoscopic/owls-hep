"""Provides method for efficiently histogramming properties of events in a
region.
"""


# System imports
from uuid import uuid4
from functools import wraps

# Six imports
from six import string_types

# NumPy imports
import numpy

# rootpy imports
from ROOT import TH1F, TH2F, TH3F

# owls-cache imports
from owls_cache.transient import cached as transiently_cached
from owls_cache.persistent import cached as persistently_cached

# owls-parallel imports
from owls_parallel import parallelized

# owls-hep imports
from owls_hep.expression import properties, normalized
from owls_hep.calculation import Calculation


# Set up default exports
__all__ = [
    'Distribution',
    'Histogram',
]


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
            expressions: The expression (as a string or 1-tuple of a string) or
                expressions (as an N-tuple of strings), in terms of dataset
                variables, to histogram.  The multiplicity of expressions
                determines the dimensionality of the histogram.  Each
                expression must be a string evaluable using
                owls.data.evaluation.evaluate.
            binnings: The binning (as a binning or 1-tuple of a binning) or
                binnings (as an N-tuple of binnings) to use for the axix/axes
                of the histogram.  The multiplicity of binnings must match that
                of expressions.  Each binning must be a tuple of one of two
                forms:

                    ('fixed', low_bin_left_edge, high_bin_right_edge, n_bins)

                or

                    ('variable',
                     low_bin_left_edge,
                     second_bin_left_edge,
                     ...,
                     high_bin_right_edge)

                If passing a single string (outside of a tuple) for
                expressions, then binnings must be a single binning object
                outside of a tuple.
            x_label: The ROOT TLatex label to use for the x-axis
            y_label: The ROOT TLatex label to use for the y-axis
        """
        # Store parameters
        self._name = name
        self._x_label = x_label
        self._y_label = y_label

        # Normalize expressions and binnings by converting them to tuples if
        # they are single elements.  We don't check the type of binnings, since
        # it will always be some manner of tuple, and the docstrings state it
        # must be a single element if expressions is a single element.
        if isinstance(expressions, string_types):
            self._expressions = (expressions,)
            self._binnings = (binnings,)
        else:
            self._expressions = expressions
            self._binnings = binnings

        # Validate that expression and binning counts jive
        if len(self._expressions) != len(self._binnings):
            raise ValueError('histogram bin specifications must have the same '
                             'length as expression specifications')

    def __hash__(self):
        """Returns a hash of those quantities affecting the resultant
        computation.
        """
        # TODO: Do we really need x-label/y-label here?
        return hash((self._expressions,
                     self._binnings,
                     self._x_label,
                     self._y_label))

    def name(self):
        """Returns the name for this distribution.
        """
        return self._name

    def expressions(self):
        """Returns the expressions for this distribution.
        """
        return self._expressions

    @staticmethod
    def _expand_binning(binning):
        """Expands a fixed or variable-width binning specification.

        Args:
            binning: The binning specification to expand

        Returns:
            A NumPy array of the bin edges.
        """
        # Check that the basic format of the specification is correct
        if not isinstance(binning, tuple) or len(binning) < 1:
            raise ValueError('invalid bin specification value')

        # Handle based on binning type
        if binning[0] == 'fixed':
            # Check length of tuples, making sure it will generate at least 2
            # edges (we add 1 below)
            if len(binning) != 4 or binning[3] < 1:
                raise ValueError('invalid fixed-width bin specification')

            # Expand them to full edge lists, adding 1 to the bin count so that
            # at least 2 edges are generated.  Unfortunately there is no way to
            # specify a dtype to linspace, but the implementation is hard-coded
            # to return a float, so we'll go with it.
            return numpy.linspace(binning[1], binning[2], binning[3] + 1)
        elif binning[0] == 'variable':
            # Check length of edge lists (need at least 2 edges in addition to
            # type specification)
            if len(binning) < 3:
                raise ValueError('invalid variable-width bin specification')

            # Take existing edge lists as they come, but ensure they are
            # typed as float
            return numpy.array(binning[1:], dtype = numpy.float)
        else:
            raise ValueError('invalid bin specification type')

    def binnings(self):
        """Returns the expanded binnings for this distribution.
        """
        return tuple((Distribution._expand_binning(b) for b in self._binnings))

    def x_label(self):
        """Returns the x-axis label for this distribution.
        """
        return self._x_label

    def y_label(self):
        """Returns the y-axis label for this distribution.
        """
        return self._y_label


# Dummy function to return fake values when parallelizing
def _parallel_mocker(process, region, distribution):
    # Extract binnings
    binnings = distribution.binnings()

    # Create a unique name and title for the histogram
    name = title = uuid4().hex

    # Create an empty histogram
    # NOTE: When specifying explicit bin edges, you aren't passing a length
    # argument, you are passing an nbins argument, which is length - 1, hence
    # the code below.  If you pass length for n bins, then you'll get garbage
    # for the last bin's upper edge and things go nuts in ROOT.
    dimensionality = len(binnings)
    if dimensionality == 1:
        return TH1F(name, title,
                    len(binnings[0]) - 1, binnings[0])
    elif dimensionality == 2:
        return TH2F(name, title,
                    len(binnings[0]) - 1, binnings[0],
                    len(binnings[1]) - 1, binnings[1])
    elif dimensionality == 3:
        return TH3F(name, title,
                    len(binnings[0]) - 1, binnings[0],
                    len(binnings[1]) - 1, binnings[1],
                    len(binnings[2]) - 1, binnings[2])
    else:
        raise ValueError('ROOT can only histograms 1 - 3 dimensions')


# Histogram parallelization mapper.  We map/group based on process to maximize
# data loading caching.
def _parallel_mapper(process, region, distribution):
    return (process,)


# Histogram argument converter which can take *args, **kwargs and convert them
# to *args.  No other way to do this correctly and simply than having a
# function with the proper names.
def _parallel_extractor(process, region, distribution):
    return (process, region, distribution)


# Caching loader to be able to share data across histogram calls without
# necessarily pre-loading it
@transiently_cached(lambda process, properties: (process, tuple(properties)))
def _caching_loader(process, properties):
    return process.load(properties)


# Histogram parallelization batcher
def _parallel_batcher(function, args_kwargs):
    # Create a combined set of properties necessary for all calls
    all_properties = set()
    for args, kwargs in args_kwargs:
        # Extract region and expressions
        _, region, distribution = _parallel_extractor(*args, **kwargs)

        # Add region properties
        selection, weight = region.selection_weight()
        all_properties.update(properties(selection))
        all_properties.update(properties(weight))

        # Add expression properties
        expressions = distribution.expressions()
        if isinstance(expressions, string_types):
            all_properties.update(properties(expressions))
        else:
            all_properties.update(*(properties(e) for e in expressions))

    # Go through all args/kwargs pairs and call the function
    for args, kwargs in args_kwargs:
        # Call the functions with load hints
        kwargs['load_hints'] = all_properties
        function(*args, **kwargs)

    # Clear the load caches of the caching loader
    _caching_loader.caches.clear()


# Histogram persistent cache mapper
def _cache_mapper(process, region, distribution, load_hints = None):
    return (process, region, distribution)


@parallelized(_parallel_mocker, _parallel_mapper, _parallel_batcher)
@persistently_cached('owls_hep.histogramming.histogram', _cache_mapper)
def _histogram(process, region, distribution, load_hints = None):
    """Generates a ROOT histogram of a distribution a process in a region.

    Args:
        process: The process whose events should be histogrammed
        region: The region whose weighting/selection should be applied
        distribution: The distribution to histogram
        load_hints: If provided, this argument will hint to _histogram that it
            should load additional properties when loading data and that it
            should use the _caching_loader.  This facilitates cached loading of
            data across multiple calls to _histogram with the same process.
            This is particularly useful for parallelized histogramming, where
            the jobs are grouped by process.

    Returns:
        A ROOT histogram, of the TH1F, TH2F, or TH3F variety.
    """
    # Compute weighted selection
    selection, weight = region.selection_weight()

    # Extract expressions and binnings
    expressions = distribution.expressions()
    binnings = distribution.binnings()

    # Compute required data properties
    required_properties = load_hints if load_hints is not None else set()

    # Add in those properties necessary to evaluate the selection and weight
    required_properties.update(properties(selection))
    required_properties.update(properties(weight))

    # Add in those properties necessary to evaluate expressions
    if isinstance(expressions, string_types):
        required_properties.update(properties(expressions))
    else:
        required_properties.update(*(properties(e) for e in expressions))

    # Load data, using the _caching_loader if load_hints have been provided
    if load_hints is not None:
        data = _caching_loader(process, required_properties)
    else:
        data = process.load(required_properties)

    # Extract just those events passing the selection
    data = data[data.eval(normalized(selection))]

    # Count the number of events passing selection
    count = len(data)

    # Evaluate each variable expression, converting the resultant Pandas Series
    # to a NumPy array
    # HACK: TH1::FillN only supports 64-bit floating point values, so convert
    # things.  Would be nice to find a better approach.
    samples = tuple((data.eval(normalized(e)).values.astype(numpy.float64)
                     for e
                     in expressions))

    # Evaluate weights, converting the resultant Pandas Series to a NumPy array
    # HACK: TH1::FillN only supports 64-bit floating point values, so convert
    # things.  Would be nice to find a better approach.
    weights = data.eval(normalized(weight)).values.astype(numpy.float64)

    # Create a unique name and title for the histogram
    name = title = uuid4().hex

    # Create a histogram based on dimensionality
    # NOTE: When specifying explicit bin edges, you aren't passing a length
    # argument, you are passing an nbins argument, which is length - 1, hence
    # the code below.  If you pass length for n bins, then you'll get garbage
    # for the last bin's upper edge and things go nuts in ROOT.
    dimensionality = len(expressions)
    if dimensionality == 1:
        # Create a one-dimensional histogram
        result = TH1F(name, title,
                      len(binnings[0]) - 1, binnings[0])

        # Fill the histogram
        # HACK: TH1::FillN will die if N == 0
        if count > 0:
            result.FillN(count, samples[0], weights)
    elif dimensionality == 2:
        # Create a two-dimensional histogram
        result = TH2F(name, title,
                      len(binnings[0]) - 1, binnings[0],
                      len(binnings[1]) - 1, binnings[1])

        # Fill the histogram
        # HACK: TH1::FillN will die if N == 0
        if count > 0:
            result.FillN(count, samples[0], samples[1], weights)
    elif dimensionality == 3:
        # Create a three-dimensional histogram
        result = TH3F(name, title,
                      len(binnings[0]) - 1, binnings[0],
                      len(binnings[1]) - 1, binnings[1],
                      len(binnings[2]) - 1, binnings[2])

        # HACK: TH3 doesn't have a FillN method, so we have to do things the
        # slow way.
        # TODO: We may want to put a warning here at some point.
        for x, y, z, w in zip(samples[0], samples[1], samples[2], weights):
            result.Fill(x, y, z, w)
    else:
        raise ValueError('ROOT can only histograms 1 - 3 dimensions')

    # All done
    return result


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
        # Compute the histogram
        result = _histogram(process, region, self._distribution)

        # Style the histogram
        process.style(result)

        # All done
        return result
