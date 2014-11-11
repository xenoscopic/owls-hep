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
from owls_hep.calculation import HigherOrderCalculation
from owls_hep.algebra import multiply


# Set up default exports
__all__ = [
    'Uncertainty',
    'StatisticalUncertainty',
    'uncertainty_count',
    'combine_count_uncertainties',
    'uncertainty_band',
    'combine_uncertainty_bands',
    'ratio_uncertainty_band',
]


class Uncertainty(HigherOrderCalculation):
    """Abstract base class for all uncertainties.

    All Uncertainty implementations should accept either a floating-point count
    or ROOT THN subclass as the result of their underlying calculation.

    All uncertainty calculations should return a tuple of the form:

        (overall_up, overall_down, shape_up, shape_down)

    Overall uncertainty tuple elements should be numbers.  Shape uncertainty
    tuple elements should be the type of the underlying calculation - either a
    count or a histogram.

    All uncertainty calculations should return the same type as their
    underlying calculation.

    All Uncertainty implementations should call their parent constructor if
    they override it.
    """

    def name(self):
        """Returns the name of the uncertainty.

        Implementers must override this method.
        """
        raise NotImplementedError('abstract method')


class StatisticalUncertainty(Uncertainty):
    """Computes the statistical uncertainty associated with a count or
    distribution.
    """

    def name(self):
        """Returns the name of the uncertainty.
        """
        return 'Statistical'

    def __call__(self, process, region):
        """Evaluates the uncertainty on the given process/region.

        Args:
            process: The process to consider
            region: The region to consider

        Returns:
            A tuple of the form (shape_up, shape_down).
        """
        # Execute the calculation
        value = self.calculation(process, region)

        # Statistical uncertainty is a bit of a special case, because it is
        # derived from the result of the calculation itself, and not a
        # variation of the inputs to the calculation.  Thus we need to handle
        # based on type.
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


def sum_quadrature(values):
    """Adds values in quadrature.

    Args:
        values: An iterable of values to sum

    Returns:
        The sum of values in quadrature
    """
    return sqrt(sum((x ** 2 for x in values)))


# TODO: Update the signature of this method to match to_shape
def to_overall(shape, nominal):
    """Converts a shape variation to an overall variation.

    Args:
        shape: The varied histogram
        nominal: The nominal histogram - should have the same bining as shape

    Returns:
        The ratio of shape.Integral()/nominal.Integral(), or 0.0 if nominal has
        0 integral.
    """
    # Compute integrals
    shape_integral = shape.Integral()
    nominal_integral = nominal.Integral()

    # Watch out for divide by 0
    # TODO: Is this the correct treatment?
    if nominal_integral == 0.0:
        return 0.0

    # Compute
    return shape_integral / nominal_integral


def to_shape(uncertainty, nominal):
    """Converts an overall uncertainty to a shape uncertainty.

    If the uncertainty has no overall component, it is returned as-is.

    If the uncertainty has an overall component and a shape component, the
    shape component is disregarded and replaced by the newly converted shape
    component.

    Args:
        uncertainty: A tuple of the form
            (overall_up, overall_down, shape_up, shape_down)
        nominal: The nominal shape result

    Returns:
        A tuple of the form
            (None, None, shape_up, shape_down)
    """
    # Extract overall uncertainties
    overall_up, overall_down, _, _ = uncertainty

    # If we don't have overall components, bail
    if overall_up is None or overall_down is None:
        return uncertainty

    # Compute the result
    return (
        None,
        None,
        multiply(overall_up, nominal),
        multiply(overall_down, nominal)
    )


def uncertainty_count(process, region, calculation, uncertainty, estimation):
    """Calculates the count uncertainty for a specific uncertainty.

    Args:
        process: The process to consider
        region: The region to consider
        calculation: The calculation, which should return a count
        uncertainty: The Uncertainty subclass to consider
        estimation: The Estimation subclass to consider

    Returns:
        A tuple of the form (upper_expectation, lower_expectation).
    """
    # Compute the nominal histogram
    nominal = estimation(calculation)(process, region)

    # Compute the variations
    variations = estimation(uncertainty(calculation))(process, region)

    # Unpack variations
    overall_up, overall_down, shape_up, shape_down = variations

    # Create a list of fractional variations which will be added in
    # quadrature
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
    return (sum_quadrature(up_variations) * nominal,
            sum_quadrature(down_variations) * nominal)


def combine_count_uncertainties(count_uncertainties):
    """Combines the results of multiple UncertaintyCount calculations.

    Args:
        count_uncertainties: The uncertainties to combine

    Returns:
        A tuple of the form (upper_expectation, lower_expectation).
    """
    return (
        sum_quadrature((u[0] for u in count_uncertainties)),
        sum_quadrature((u[1] for u in count_uncertainties)),
    )


def uncertainty_band(process, region, calculation, uncertainty, estimation):
    """Calculates an uncertainty band (TGraphAsymmErrors) for a specific
    uncertainty.

    Args:
        process: The process to consider
        region: The region to consider
        calculation: The calculation, which should return a histogram
        uncertainty: The Uncertainty subclass to consider
        estimation: The Estimation subclass to consider

    Returns:
        A TGraphAsymmErrors representing the error band.
    """
    # Compute the nominal histogram
    nominal = estimation(calculation)(process, region)

    # Compute the variations
    variations = estimation(uncertainty(calculation))(process, region)

    # Unpack variations
    overall_up, overall_down, shape_up, shape_down = variations

    # Get the number of bins in the histogram
    bins = nominal.GetNbinsX()

    # Create the error band.  We pass it the nominal histogram just to get
    # the binning correct.  The graph will also extract values and errors
    # from the histogram, but that's okay because we'll overwrite them
    # below.
    band = TGraphAsymmErrors(nominal)

    # Go through each point in the graph and 0-out the Y-value and Y-error.
    # Unfortunately we can't set the Y-value individually (which would have
    # been great since the X-values would already be at bin centers).
    # Anyway, no big deal, X-values are easy to set.  The X-error will have
    # already bin set to bin width.
    for bin in xrange(0, bins):
        band.SetPoint(bin, band.GetX()[bin], 0)
        band.SetPointEYhigh(bin, 0.0)
        band.SetPointEYlow(bin, 0.0)

    # Loop over all bins and compute errors.  Note that, of course, the TH1
    # and TGraphAsymmErrors use different indexing schemes.
    for bin, point in zip(range(1, bins + 1), range(0, bins)):
        # Get the bin content
        content = nominal.GetBinContent(bin)

        # Create a list of fractional variations for this bin
        up_variations = []
        down_variations = []

        # Add any overall variations
        if content > 0 and None not in (overall_up, overall_down):
            up_variations.append(abs(overall_up - 1.0))
            down_variations.append(abs(overall_down - 1.0))

        # Add any shape variations
        if content > 0 and None not in (shape_up, shape_down):
            # Extract the variation bins
            up = shape_up.GetBinContent(bin)
            down = shape_down.GetBinContent(bin)

            # Compute the variations
            up_variations.append(abs((up / content) - 1.0))
            down_variations.append(abs((down / content) - 1.0))

        # Set the point and error
        band.SetPoint(point, band.GetX()[point], content)
        band.SetPointEYhigh(point,
                            sum_quadrature(up_variations) * content)
        band.SetPointEYlow(point,
                           sum_quadrature(down_variations) * content)

    # All done
    return band


def combine_uncertainty_bands(bands, sum_values, title = 'Uncertainty'):
    """Combines the results of multiple UncertaintyBand calculations.

    Args:
        bands: The uncertainty bands to combine
        sum_values: If True, then the y-components of the uncertainty bands are
            summed (which is what you want when combining uncertainty bands for
            multiple processes which you will stack).  If False, then the
            y-component of the first uncertainty band is propagated to the
            result, the assumption being that all bands have the same
            y-component (which is what you want when combining uncertainty
            bands for the same process where only the magnitude of the
            uncertainties should be summed).
        title: The title to give to the resulting combined band

    Returns:
        A TGraphAsymmErrors representing the combined band.
    """
    # Check that the band list is not empty, because we'll need to clone one
    if len(bands) == 0:
        raise ValueError('list of bands must be non-empty')

    # Clone the first band, just to get binning
    result = bands[0].Clone(uuid4().hex)

    # Set the title
    result.SetTitle(title)

    # Loop over all bins
    for i in xrange(0, result.GetN()):
        # Set the bin content if we're summing, otherwise it will already have
        # been propagated from the first error band
        if sum_values:
            result.SetPoint(i,
                            result.GetX()[i],
                            sum(b.GetY()[i] for b in bands))

        # Set the high error
        result.SetPointEYhigh(i, sum_quadrature((b.GetErrorYhigh(i)
                                                 for b
                                                 in bands)))

        # Set the low error
        result.SetPointEYlow(i, sum_quadrature((b.GetErrorYlow(i)
                                                for b
                                                in bands)))

    # All done
    return result


# TODO: Really need to validate that this is the correct treatment
def ratio_uncertainty_band(denominator, band):
    """Converts an uncertainty band to one that can be displayed in a ratio
    plot.

    Args:
        denominator: The denominator distribution of the ratio band
        band: The uncertainty band

    Returns:
        A TGraphAsymmErrors representing the uncertainty band for a ratio plot.
    """
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
