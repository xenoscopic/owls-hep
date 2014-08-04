"""Provides facilities for computing statistical and systematic uncertainties.
"""


# System imports
from uuid import uuid4
from math import sqrt

# Six imports
from six.moves import range

# ROOT imports
from ROOT import TH1, TGraphAsymmErrors

# owls-hep imports
from owls_hep.config import load as load_config


def load(uncertainties_path):
    # Load the configuration
    configuration = load_config(uncertainties_path)

    # Create the function to load individual estimations
    def uncertainty_loader(name):
        # Grab the full (module-qualified) function name for this uncertainty
        full_method_name = configuration[name]

        # Parse the name into module/function name
        method_module_name, method_name = full_method_name.rsplit('.', 1)

        # Load the module
        method_module = __import__(method_module_name,
                                   fromlist = [method_name])

        # Extract the method
        return getattr(method_module, method_name)

    # Return the loader
    return estimation_loader


def statistical_uncertainty(process, region, calculation, estimation):
    # Execute the calculation
    value = estimation(process, region, calculation)

    # Statistical uncertainty is a bit of a special case, because it is derived
    # from the result of the calculation itself, and not a variation of the
    # inputs to the calculation.  Thus we need to handle based on type.
    if isinstance(value, TH1):
        # Create up/down clones
        up = value.Clone(uuid4().hex)
        down = value.Clone(uuid4().hex)

        # Modify each bin (note that we do underflow/overflow)
        for i in range(0, value.GetNbinsX() + 2):
            content = value.GetBinContent(i)
            up.SetBinContent(i, content + sqrt(abs(content)))
            down.SetBinContent(i, content - sqrt(abs(content)))

        # Create the result
        result = (None, None, up, down)
    else:
        result = (None, None, value + sqrt(value), value - sqrt(value))

    # All done
    return result


def _sum_quadrature(values):
    """Adds values in quadrature.

    Args:
        values: An iterable of values to sum

    Returns:
        The sum of values in quadrature
    """
    return sqrt(sum((x**2 for x in values)))


def count_uncertainty(process, region, count, estimation, uncertainty):
    # Compute the nominal count
    nominal = estimation(process, region, count)

    # Compute the variations
    variations = uncertainty(process, region, count, estimation)

    # Unpack variations
    overall_up, overall_down, shape_up, shape_down = variations

    # Create a list of fractional variations which will be added in quadrature
    up_variations = []
    down_variations = []

    # Check for overall variations
    if nominal > 0 and overall_up is not None and overall_down is not None:
        up_variations.append(abs(overall_up - 1.0))
        down_variations.append(abs(overall_down - 1.0))

    # Check for shape variations
    if nominal > 0 and shape_up is not None and shape_down is not None:
        up_variations.append(abs((shape_up / nominal) - 1.0))
        down_variations.append(abs((shape_down / nominal) - 1.0))

    # Combine variations in quadrature
    return (_sum_quadrature(up_variations) * nominal,
            _sum_quadrature(down_variations) * nominal)


def combined_count_uncertainty(count_uncertainties):
    return (
        _sum_quadrature((u[0] for u in count_uncertainties)),
        _sum_quadrature((u[1] for u in count_uncertainties)),
    )


def histogram_uncertainty(process,
                          region,
                          histogram,
                          estimation,
                          uncertainty):
    # Compute the nominal histogram
    nominal = estimation(process, region, histogram)

    # Compute the variations
    variations = uncertainty(process, region, histogram, estimation)

    # Unpack variations
    overall_up, overall_down, shape_up, shape_down = variations

    # Get the number of bins in the histogram
    bins = nominal.GetNbinsX()

    # Create the error band.  We pass it the nominal histogram just to get the
    # binning correct.  The graph will also extract values and errors from the
    # histogram, but that's okay because we'll overwrite them below.
    band = TGraphAsymmErrors(nominal)

    # Go through each point in the graph and 0-out the Y-value and Y-error.
    # Unfortunately we can't set the Y-value individually (which would have
    # been great since the X-values would already be at bin centers).  Anyway,
    # no big deal, X-values are easy to set.  The X-error will have already bin
    # set to bin width.
    for bin in xrange(0, bins):
        band.SetPoint(bin, band.GetX()[bin], 0)
        band.SetPointEYhigh(bin, 0.0)
        band.SetPointEYlow(bin, 0.0)

    # Loop over all bins and compute errors.  Note that, of course, the TH1 and
    # TGraphAsymmErrors use different indexing schemes.
    for bin, point in zip(range(1, bins + 1), range(0, bins)):
        # Get the bin content
        content = nominal.GetBinContent(bin)

        # Create a list of fractional variations for this bin
        up_variations = []
        down_variations = []

        # Add any overall variations
        if content > 0 and overall_up is not None and overall_down is not None:
            up_variations.append(abs(overall_up - 1.0))
            down_variations.append(abs(overall_down - 1.0))

        # Add any shape variations
        if content > 0 and shape_up is not None and shape_down is not None:
            # Extract the variation bins
            up = shape_up.GetBinContent(bin)
            down = shape_down.GetBinContent(bin)

            # Compute the variations
            up_variations.append(abs((up / content) - 1.0))
            down_variations.append(abs((down / content) - 1.0))

        # Set the point and error
        band.SetPoint(point, band.GetX()[point], content)
        band.SetPointEYhigh(point, _sum_quadrature(up_variations) * content)
        band.SetPointEYlow(point, _sum_quadrature(down_variations) * content)

    # All done
    return band


def combined_histogram_uncertainty(bands,
                                   title = 'Uncertainty'):
    # Check that the band list is not empty, because we'll need to clone one
    if len(bands) == 0:
        raise ValueError('list of bands must be non-empty')

    # Clone the first band, just to get binning
    result = bands[0].Clone(uuid4().hex)

    # Set the title
    result.SetTitle(title)

    # Loop over all bins
    for i in xrange(0, result.GetN()):
        # Set the bin content
        result.SetPoint(i, result.GetX()[i], sum(b.GetY()[i] for b in bands))

        # Set the high error
        result.SetPointEYhigh(i, _sum_quadrature((b.GetErrorYhigh(i)
                                                  for b
                                                  in bands)))

        # Set the low error
        result.SetPointEYlow(i, _sum_quadrature((b.GetErrorYlow(i)
                                                 for b
                                                 in bands)))

    # All done
    return result


# TODO: Really need to validate that this is the correct treatment
def ratio_histogram_uncertainty(denominator, band):
    # Create a clone of the band
    result = band.Clone(uuid4().hex)

    # Calculate the number of bins
    bins = denominator.GetNbinsX()

    # Loop over all bins
    for bin, point in zip(range(1, bins + 1), range(0, bins)):
        # Set the band nominal point to center around Y = 1.0
        result.SetPoint(point, result.GetX()[point], 1.0)

        # Extract the bin content
        content = denominator.GetBinContent(bin)

        # If the bin content is 0, then set the error to be 0
        if content == 0:
            result.SetPointEYhigh(point, 0.0)
            result.SetPointEYlow(point, 0.0)
            continue

        # Scale the errors.  Note that we use the inverse (low for high and
        # high for low) since these errors are on the denominator.
        high_content = band.GetErrorYhigh(point)
        low_content = band.GetErrorYlow(point)
        result.SetPointEYhigh(point, low_content / content)
        result.SetPointEYlow(point, high_content / content)

    return result


def include_uncertainty():
    # TODO: Implement method to include an uncertainty into a workspace
    pass
