"""Provides method for efficiently histogramming properties of events in a
region.
"""


# System imports
from uuid import uuid4
from functools import wraps
import gc

# Six imports
from six import string_types

# NumPy imports
import numpy

# ROOT imports
from ROOT import TH1F, TH2F, TH3F, nullptr

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
    'Binning',
    'Histogram',
]


class Binning(object):
    """Represents a binning to be used on an axis in a histogram.
    """

    def __init__(self, type, *args):
        """Initializes a new instance of the Binning class.

        Args:
            type: The binning type, either 'fixed' or 'variable'
            *args: The remaining arguments depend on the binning type.  For
                'fixed'-width bins, the remaining arguments should be of the
                form:

                    low_bin_left_edge, high_bin_right_edge, n_bins

                For 'variable'-width bins, the remaining arguments should be of
                the form:

                    low_bin_left_edge,
                    second_bin_left_edge,
                    ...,
                    high_bin_right_edge
        """
        # Validate and store type
        if type not in ('fixed', 'variable'):
            raise ValueError('invalid binning type')
        self._type = type

        # Validate and store edge specifications
        self._low_bin_left_edge = None
        self._high_bin_right_edge = None
        self._n_bins = None
        self._edges = None
        if self._type == 'fixed':
            # Parse
            low_bin_left_edge, high_bin_right_edge, n_bins = args

            # Validate
            if n_bins < 1:
                raise ValueError('must have at least one bin')
            if low_bin_left_edge >= high_bin_right_edge:
                raise ValueError('lower edge must be higher than upper edge')

            # Store
            self._low_bin_left_edge = low_bin_left_edge
            self._high_bin_right_edge = high_bin_right_edge
            self._n_bins = n_bins
        elif self._type == 'variable':
            # Parse
            edges = args

            # Validate
            if len(edges) < 2:
                raise ValueError('must have at least two edges')
            if not all(x < y for x, y in zip(edges, edges[1:])):
                raise ValueError('edges must be strictly increasing')

            # Store
            self._edges = edges

    def __hash__(self):
        """Returns a unique hash for the binning.

        The hash is based on the specifications provided to the constructor, so
        equivalent binnings may have different hashes.
        """
        # HACK: hash(None) is not consistent across Python processes because
        # None is a singleton and its address varies between runs.  I wish I
        # were making this up.  Anyway, we would normally just do a dumb tuple
        # including self._* parameters which are None, but I guess we can't.
        if self._type == 'fixed':
            return hash((self._type,
                         self._low_bin_left_edge,
                         self._high_bin_right_edge,
                         self._n_bins))
        elif self._type == 'variable':
            return hash((self._type, self._edges))

    def edges(self):
        """Returns an explicit NumPy array of doubles representing bin edges.
        """
        if self._type == 'fixed':
            # Expand to a full edge list, adding 1 to the bin count so that at
            # least 2 edges are generated.  Unfortunately there is no way to
            # specify a dtype to linspace, but the implementation is hard-coded
            # to return a float, so we'll go with it.
            return numpy.linspace(self._low_bin_left_edge,
                                  self._high_bin_right_edge,
                                  self._n_bins + 1)
        elif self._type == 'variable':
            # Use existing edges, but ensure they are type as float
            return numpy.array(self._edges, dtype = numpy.float)


# Dummy function to return fake values when parallelizing
def _parallel_mocker(process, region, expressions, binnings):
    # Extract binnings
    edges = tuple((b.edges() for b in binnings))

    # Create a unique name and title for the histogram
    name = title = uuid4().hex

    # Create an empty histogram
    # NOTE: When specifying explicit bin edges, you aren't passing a length
    # argument, you are passing an nbins argument, which is length - 1, hence
    # the code below.  If you pass length for n bins, then you'll get garbage
    # for the last bin's upper edge and things go nuts in ROOT.
    dimensionality = len(edges)
    if dimensionality == 1:
        return TH1F(name, title,
                    len(edges[0]) - 1, edges[0])
    elif dimensionality == 2:
        return TH2F(name, title,
                    len(edges[0]) - 1, edges[0],
                    len(edges[1]) - 1, edges[1])
    elif dimensionality == 3:
        return TH3F(name, title,
                    len(edges[0]) - 1, edges[0],
                    len(edges[1]) - 1, edges[1],
                    len(edges[2]) - 1, edges[2])
    else:
        raise ValueError('ROOT can only histograms 1 - 3 dimensions')


# Histogram parallelization mapper.  We map/group based on process to maximize
# data loading caching.
def _parallel_mapper(process, region, expressions, binnings):
    return (process,)


# Histogram argument converter which can take *args, **kwargs and convert them
# to *args.  No other way to do this correctly and simply than having a
# function with the proper names.
def _parallel_extractor(process, region, expressions, binnings):
    return (process, region, expressions, binnings)


# Caching loader to be able to share data across histogram calls without
# necessarily pre-loading it
@transiently_cached(lambda process, properties: (process, tuple(properties)))
def _caching_loader(process, properties):
    return process.load(properties)


# Histogram parallelization batcher
def _parallel_batcher(function, args_kwargs):
    # Create a combined set of properties necessary for all calls
    # NOTE: We don't need to handle patch properties because those are handled
    # internally by the process and we're only dealing with one process in
    # batch mode
    all_properties = set()
    for args, kwargs in args_kwargs:
        # Extract region and expressions
        _, region, expressions, _ = _parallel_extractor(*args, **kwargs)

        # Add region properties
        selection, weight = region.selection_weight()
        all_properties.update(properties(selection))
        all_properties.update(properties(weight))

        # Add expression properties
        all_properties.update(*(properties(e) for e in expressions))

    # Go through all args/kwargs pairs and call the function
    for args, kwargs in args_kwargs:
        # Call the functions with load hints
        kwargs['load_hints'] = all_properties
        function(*args, **kwargs)

    # Force garbage collection
    gc.collect()

    # Clear the load caches of the caching loader
    _caching_loader.caches.clear()


# Histogram persistent cache mapper
def _cache_mapper(process, region, expressions, binnings, load_hints = None):
    return (process, region, expressions, binnings)


@parallelized(_parallel_mocker, _parallel_mapper, _parallel_batcher)
@persistently_cached('owls_hep.histogramming._histogram', _cache_mapper)
def _histogram(process, region, expressions, binnings, load_hints = None):
    """Generates a ROOT histogram of a distribution a process in a region.

    Args:
        process: The process whose events should be histogrammed
        region: The region whose weighting/selection should be applied
        expressions: A tuple of expression strings
        binnings: A tuple of Binning instances
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

    # Expand binnings to edge lists
    edges = tuple((b.edges() for b in binnings))

    # Load data
    if load_hints is not None:
        # If load_hints have been provided, just use those with the
        # _caching_loader
        data = _caching_loader(process, load_hints)
    else:
        # Otherwise manually create the set of necessary properties
        # NOTE: All we need to do are region and expression properties - patch
        # properties are handled internally by the process
        required_properties = set()

        # Add those properties necessary to evaluate region selection/weight
        required_properties.update(properties(selection))
        required_properties.update(properties(weight))

        # Add in those properties necessary to evaluate expressions
        required_properties.update(*(properties(e) for e in expressions))

        # Load data
        data = process.load(required_properties)

    # Apply selection if specified
    if selection != '':
        data = data[data.eval(normalized(selection))]

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
    if weight != '':
        weights = data.eval(normalized(weight)).values.astype(numpy.float64)
    else:
        weights = nullptr

    # Create a unique name and title for the histogram
    name = title = uuid4().hex

    # Create a histogram based on dimensionality
    # NOTE: When specifying explicit bin edges, you aren't passing a length
    # argument, you are passing an nbins argument, which is length - 1, hence
    # the code below.  If you pass length for n bins, then you'll get garbage
    # for the last bin's upper edge and things go nuts in ROOT.
    dimensionality = len(expressions)
    count = len(data)
    if dimensionality == 1:
        # Create a one-dimensional histogram
        result = TH1F(name, title,
                      len(edges[0]) - 1, edges[0])

        # Fill the histogram
        # HACK: TH1::FillN will die if N == 0
        if count > 0:
            result.FillN(count, samples[0], weights)
    elif dimensionality == 2:
        # Create a two-dimensional histogram
        result = TH2F(name, title,
                      len(edges[0]) - 1, edges[0],
                      len(edges[1]) - 1, edges[1])

        # Fill the histogram
        # HACK: TH1::FillN will die if N == 0
        if count > 0:
            result.FillN(count, samples[0], samples[1], weights)
    elif dimensionality == 3:
        # Create a three-dimensional histogram
        result = TH3F(name, title,
                      len(edges[0]) - 1, edges[0],
                      len(edges[1]) - 1, edges[1],
                      len(edges[2]) - 1, edges[2])

        # HACK: TH3 doesn't have a FillN method, so we have to do things the
        # slow way.
        # TODO: We may want to put a warning about this slowness
        if weights == nullptr:
            weights = numpy.ones(count, dtype = numpy.float64)
        for x, y, z, w in zip(samples[0], samples[1], samples[2], weights):
            result.Fill(x, y, z, w)
    else:
        raise ValueError('ROOT can only histograms 1 - 3 dimensions')

    # All done
    return result


class Histogram(Calculation):
    """A histogramming calculation which generates a ROOT THN histogram.

    Although the need should not generally arise to subclass Histogram, all
    subclasses must return a ROOT THN subclass for their result.
    """

    def __init__(self, expressions, binnings, title, x_label, y_label):
        """Initializes a new instance of the Histogram calculation.

        Args:
            expressions: The expression (as a string or 1-tuple of a string) or
                expressions (as an N-tuple of strings), in terms of dataset
                variables, to histogram.  The multiplicity of expressions
                determines the dimensionality of the histogram.
            binnings: The binning (as a Binning or 1-tuple of a Binning) or
                binnings (as an N-tuple of Binning instances), to use for
                histogramming. The binning count must match the expression
                count.
            title: The ROOT TLatex label to use for the histogram title
            x_label: The ROOT TLatex label to use for the x-axis
            y_label: The ROOT TLatex label to use for the y-axis
        """
        # Store parameters
        if isinstance(expressions, string_types):
            self._expressions = (expressions,)
        else:
            self._expressions = expressions
        if isinstance(binnings, Binning):
            self._binnings = (binnings,)
        else:
            self._binnings = binnings
        self._title = title
        self._x_label = x_label
        self._y_label = y_label

        # Validate that expression and binning counts jive
        if len(self._expressions) != len(self._binnings):
            raise ValueError('histogram bin specifications must have the same '
                             'length as expression specifications')

    def title(self):
        """Returns the title for this histogram calculation.
        """
        return self._title

    def x_label(self):
        """Returns the x-axis label for this histogram calculation.
        """
        return self._x_label

    def y_label(self):
        """Returns the y-axis label for this histogram calculation.
        """
        return self._y_label

    def __call__(self, process, region):
        """Histograms weighted events passing a region's selection into a
        distribution.

        Args:
            process: The process whose weighted events should be histogrammed
            region: The region providing selection/weighting for the histogram

        Returns:
            A ROOT histogram representing the resultant distribution.
        """
        # Compute the histogram
        result = _histogram(process, region, self._expressions, self._binnings)

        # Set labels
        result.SetTitle(self._title)
        result.GetXaxis().SetTitle(self._x_label)
        result.GetYaxis().SetTitle(self._y_label)

        # Style the histogram
        process.style(result)

        # All done
        return result
