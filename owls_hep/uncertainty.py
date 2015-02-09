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
    'uncertainty_count',
    'combined_count_uncertainty',
    'uncertainty_band',
    'combined_uncertainty_band',
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
    shape_integral = shape.Integral(1, shape.GetNbinsX())
    nominal_integral = nominal.Integral(1, nominal.GetNbinsX())

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


def combined_count_uncertainty(count_uncertainties):
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

    Any uncertainties (except statistical) that have a shape component will
    have the shape component converted to an overall component (considered in
    addition to any existing overall component).

    NOTE: The statistical error calculated is the statistical error on the
    estimate given the poisson statistics of the unweighted samples.  This is
    calculated per-bin as:

        uncertainty = sqrt(unweighted) * weighted / unweighted
                    = weighted / sqrt(unweighted)

    For samples such as data, where there is no weighting applied, this just
    reduces to sqrt(weighted) = sqrt(unweighted), which is the usual
    uncertainty applied by ROOT.

    NOTE: The y-component of the uncertainty band will NOT be set to bin
    content because this leads to errors in usage when combining the bands and
    is only really necessary when computing the final combined band, so instead
    simply pass a base for the error band when calling
    combined_uncertainty_band.

    Args:
        process: The process to consider
        region: The region to consider
        calculation: The calculation, which should return a histogram
        uncertainty: The Uncertainty subclass to consider, or None to compute
            statistical uncertainty of Monte Carlo samples
        estimation: The Estimation subclass to consider

    Returns:
        A TGraphAsymmErrors representing the error band.
    """
    # Compute the nominal histogram
    nominal = estimation(calculation)(process, region)

    # Compute and unpack variations
    if uncertainty is not None:
        # Perform the uncertainty estimation
        variations = estimation(uncertainty(calculation))(process, region)

        # Unpack variations
        overall_up, overall_down, shape_up, shape_down = variations

        # Convert any shape variations to overall
        if shape_up is None:
            shape_overall_up = None
        else:
            shape_overall_up = to_overall(shape_up, nominal)
            shape_up = None
        if shape_down is None:
            shape_overall_down = None
        else:
            shape_overall_down = to_overall(shape_down, nominal)
            shape_down = None
    else:
        # We're computing statistical variation, so we don't need these
        overall_up = overall_down = None
        shape_up = shape_down = None
        shape_overall_up = shape_overall_down = None

        # For computing the uncertainty of weighted MC samples, we need the
        # unweighted histogram
        unweighted = estimation(calculation)(
            process,
            region.weighted(False)
        )

    # Create the error band.  We pass it the nominal histogram just to get
    # the binning correct.  The graph will also extract values and errors
    # from the histogram, but that's okay because we'll overwrite them
    # below.
    band = TGraphAsymmErrors(nominal)

    # Get the number of bins in the histogram
    bins = nominal.GetNbinsX()

    # Go through each point in the graph and 0-out the Y-value and Y-error.
    # Unfortunately we can't set the Y-value individually (which would have
    # been great since the X-values would already be at bin centers).
    # Anyway, no big deal, X-values are easy to set.  The X-error will have
    # already bin set to bin width.
    for bin in xrange(0, bins):
        band.SetPoint(bin, band.GetX()[bin], 0)
        band.SetPointEYhigh(bin, 0.0)
        band.SetPointEYlow(bin, 0.0)

    # Loop over all bins and compute uncertainties
    for bin, point in zip(range(1, bins + 1), range(0, bins)):
        # Get the bin content
        content = nominal.GetBinContent(bin)

        # If the content is 0, there are no uncertainties, because we only
        # consider overall and statistical uncertainties
        if content == 0.0:
            band.SetPointEYhigh(point, 0.0)
            band.SetPointEYlow(point, 0.0)
            continue

        # Create a list of fractional variations for this bin.  These lists
        # will hold FRACTIONAL variations, i.e. variations normalized to bin
        # content, and will be converted to absolute variations below when they
        # are set as errors.
        up_variations = []
        down_variations = []

        # Add any overall variations
        if overall_up is not None:
            up_variations.append(overall_up - 1.0)
        if overall_down is not None:
            down_variations.append(1.0 - overall_down)
        if shape_overall_up is not None:
            up_variations.append(shape_overall_up - 1.0)
        if shape_overall_down is not None:
            down_variations.append(1.0 - shape_overall_down)

        # Add the statistical variation if uncertainty is None.  Note that we
        # compute this for the statistics of the unweighted Monte Carlo and not
        # the weighted bin count.
        if uncertainty is None:
            # Get the unweighted content
            unweighted_content = unweighted.GetBinContent(bin)

            # Calculate error if possible
            if content > 0.0 and unweighted_content > 0.0:
                # The extra factor of 1/content is just because we normalize
                # everything to content for combining together.  It has nothing
                # to do with the derivation of the uncertainty, and it is
                # multipled out below.
                statistical_variation = (
                    content / sqrt(unweighted_content)
                ) / content
                up_variations.append(statistical_variation)
                down_variations.append(statistical_variation)

        # Set the point and error.  Note that, since we sum things in
        # quadrature, it really doesn't matter how we compute the differences
        # above.
        band.SetPointEYhigh(point, sum_quadrature(up_variations) * content)
        band.SetPointEYlow(point, sum_quadrature(down_variations) * content)

    # All done
    return band


def combined_uncertainty_band(bands, base = None, title = 'Uncertainty'):
    """Combines the results of multiple UncertaintyBand calculations.

    Args:
        bands: The uncertainty bands to combine
        base: The base histogram (which must have the same binning as the
            bands) which the band bin content should be set to for plotting
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
        # Set the content, if any
        if base is not None:
            result.SetPoint(i,
                            result.GetX()[i],
                            base.GetBinContent(i + 1))

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


def ratio_uncertainty_band(denominator, band):
    """Converts an uncertainty band to one that can be displayed in a ratio
    plot.

    In truth, all ratio uncertainty bands are visually-misleading because the
    error bands from which they are derived don't take into account shape
    uncertainties and because they fail to take into account large correlations
    between the numerator (data) and backgrounds which are data-driven.  Also,
    we choose a somewhat arbitrary definition of for this band so that it
    visually conforms to intuition about agreement between uncertainty bands
    in the distribution above it (e.g. if bands just touch, the ratio error
    bands should just touch, if they overlap, the ratio error bands should
    overlap, etc).  We thus define it as:

        up = (numerator/denominator)
             - ((numerator - denominator_up_unc) / denominator)
           = denominator_up_unc / denominator
        down = (numerator/denominator)
               - ((numerator - denominator_down_unc) / denominator)
             = denominator_down_unc / denominator

    You might naively think the uncertainty would be added/subtracted to/from
    the denominator, but this doesn't have the desired visual meaning, i.e. how
    the variation would move *unity*.

    This definition also has the nice property that there is no dependence on
    the numerator, so the error band is always defined if the denominator is
    defined.

    So anyway, this is as good as it gets.

    Args:
        denominator: The denominator distribution of the ratio plot
        band: The uncertainty band for the denominator distribution

    Returns:
        A TGraphAsymmErrors representing the uncertainty band for a ratio plot.
    """
    # Create a clone of the band
    result = band.Clone(uuid4().hex)

    # Calculate the number of bins
    bins = denominator.GetNbinsX()

    # Loop over all bins
    # NOTE: We don't handle overflow because TGraphAsymmErrors doesn't have a
    # notion of overflow bins
    for bin, point in zip(range(1, bins + 1), range(0, bins)):
        # Set the band nominal point to center around Y = 1.0
        result.SetPoint(point, result.GetX()[point], 1.0)

        # Extract the bin content
        denominator_value = denominator.GetBinContent(bin)

        # If the bin content is 0, then the uncertainty is 0, otherwise it is
        # the definition given above
        if denominator_value == 0.0:
            result.SetPointEYhigh(point, 0.0)
            result.SetPointEYlow(point, 0.0)
        else:
            result.SetPointEYhigh(
                point,
                band.GetErrorYhigh(point) / denominator_value
            )
            result.SetPointEYlow(
                point,
                band.GetErrorYlow(point) / denominator_value
            )

    # All done
    return result
