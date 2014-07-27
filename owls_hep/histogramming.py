"""Provides method for efficiently histogramming properties of events in a
region.
"""


# System imports
from uuid import uuid4
from functools import wraps

# Six imports
from six import string_types

# ROOT imports
from ROOT import TH1F, TH2F, TH3F, TColor

# owls-cache imports
from owls_cache.persistent import cached as persistently_cached

# owls-data imports
from owls_data.expression import properties
from owls_data.histogramming import histogram as data_histogram

# owls-parallel imports
from owls_parallel import parallelized

# owls-hep imports
from owls_hep.process import load_process_data
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


# Decorator which applies style for the histogram method - necessary because
# pickling of ROOT THN objects in the cache doesn't preserve style
def _styled(f):
    # Create the wrapper function
    @wraps(f)
    def wrapper(process, *args, **kwargs):
        # Compute the result
        result = f(process, *args, **kwargs)

        # Get style
        title = process['label']
        line_color = process['line_color']
        fill_color = process['fill_color']
        marker_style = process['marker_style']

        # Translate hex colors if necessary
        if isinstance(line_color, string_types):
            line_color = TColor.GetColor(line_color)
        if isinstance(fill_color, string_types):
            fill_color = TColor.GetColor(fill_color)

        # Apply style
        result.SetTitle(title)
        result.SetLineColor(line_color)
        result.SetFillColor(fill_color)
        if marker_style is not None:
            result.SetMarkerStyle(marker_style)
            result.SetMarkerSize(1)
            result.SetMarkerColor(result.GetLineColor())

        # All done
        return result

    # Return the wrapper function
    return wrapper


# Dummy function to return fake values when parallelizing
def _dummy_histogram(process, region, expressions, binnings):
    # Create a unique id
    name_title = uuid4().hex

    # Create a bogus histogram
    return TH1F(name_title, name_title, 1, 0, 1)


@parallelized(_dummy_histogram, lambda p, r, e, b: p)
@_styled
@persistently_cached
def histogram(process, region, expressions, binnings):
    """Generates a ROOT histogram of the specified event properties in the
    given region.

    The style of the process is applied to the result.

    Args:
        process: The process whose events should be histogrammed
        region: The region whose weighting/selection should be applied
        expressions: See owls.data.histogramming.histogram
        binnings: See owls.data.histogramming.histogram

    Returns:
        A ROOT histogram.
    """
    # Compute weighted selection
    region_weighted_selection = weighted_selection(region)

    # Compute the weighted selection properties
    required_properties = properties(region_weighted_selection)

    # Add in properties for expressions
    if isinstance(expressions, string_types):
        required_properties.update(properties(expressions))
    else:
        for expression in expressions:
            required_properties.update(properties(expression))

    # Create the NumPy histogram
    numpy_result = data_histogram(
        load_process_data(process, required_properties),
        region_weighted_selection,
        expressions,
        binnings
    )

    # Compute the result
    result = _numpy_to_root_histogram(numpy_result)

    # All done
    return result
