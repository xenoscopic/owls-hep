"""Provides the base class for all estimation schemes.
"""


# owls-hep imports
from owls_hep.calculation import HigherOrderCalculation
from owls_hep.uncertainty import Uncertainty, to_shape
from owls_hep.algebra import add, multiply


# Set up default exports
__all__ = [
    'Estimation',
]


# TODO: May want to impose documented requirements on the types of calculations
# which should be supported by estimation, specifically Count, Histogram, and
# Uncertainty, but the underlying calculation/estimation combination may be too
# domain-specific, so maybe we don't want to make that assumption.
class Estimation(HigherOrderCalculation):
    """Abstract base class for all estimation schemes.

    All estimation calculations should return the same type as their underlying
    calculation.

    All Estimation implementations should call their parent constructor if they
    override it.
    """

    def components(self, process, region):
        """Generates the components that are combined to form the background
        estimation.

        Args:
            process: The process to consider
            region: The region to consider

        Returns:
            A list of the form:

                [
                    (coefficient_0, use_nominal_0, process_0, region_0),
                    ...,
                    (coefficient_N, use_nominal_N, process_N, region_N)
                ]

            This list will be used to generate the combined result.
            coefficient is the scale factor to use for this component.
            use_nominal causes this method to ignore systematic variaitons for
            this component if the underlying calculation is an uncertainty.
            process and region are the values passed to the underlying
            calculation.
        """
        raise NotImplementedError('abstract method')

    def __call__(self, process, region, weighted_combination = True):
        """Executes the background estimation scheme.

        This method combines components which enter into backgruond estimation.
        Implementers should NOT override this method.  Instead, they should
        return a tuple of the components entering background estimation by
        overriding the `components` method.

        This method is designed to handle the following types of calculations:

            - Count
            - Histogram
            - Uncertainty

        Args:
            process: The process to consider
            region: The region to consider
            weighted_combination: Whether or not to apply weights from
                components

        Returns:
            The combined background estimation.
        """
        # Get components
        components = self.components(process, region)

        # Watch for empty components
        if len(components) == 0:
            raise ValueError('must have at least one component for estimation')

        # If we're not using weights, switch all coefficients to 1
        if not weighted_combination:
            components = [(1.0, c[1], c[2], c[3]) for c in components]

        # Determine if we're dealing with an uncertainty or not
        is_uncertainty = isinstance(self.calculation, Uncertainty)

        # If we're dealing with an uncertainty calculation, then create a
        # calculation that will compute a faux-uncertainty ntuple with the
        # nominal value for components that shouldn't have the uncertainty
        # applied.  Also have it support the coefficient.
        if is_uncertainty:
            def nominal(coefficient, process, region):
                # self.calculation.calculation is the nominal calculation
                n = multiply(
                    coefficient,
                    self.calculation.calculation(process, region)
                )
                return (None, None, n, n)

        # If we're dealing with an uncertainty calculation, then create a
        # calculation that will convert any overall systematics to shape
        # systematics so that they can be combined with the other components of
        # the estimation.  Also have it support the coefficient.
        if is_uncertainty:
            def uncertainty(coefficient, process, region):
                u = self.calculation(process, region)
                # self.calculation.calculation is the nominal calculation
                n = self.calculation.calculation(process, region)
                u = to_shape(u, n)
                return (
                    None,
                    None,
                    multiply(coefficient, u[2]),
                    multiply(coefficient, u[3])
                )

        # Compute the first value which we'll use as the basis of the result
        coefficient, use_nominal, process, region = components[0]
        if is_uncertainty:
            if use_nominal:
                result = nominal(coefficient, process, region)
            else:
                result = uncertainty(coefficient, process, region)
        else:
            result = multiply(coefficient, self.calculation(process, region))

        # Compute the remaining values
        for coefficient, use_nominal, process, region in components[1:]:
            if is_uncertainty:
                if use_nominal:
                    value = nominal(coefficient, process, region)
                else:
                    value = uncertainty(coefficient, process, region)
                result = (
                    None,
                    None,
                    # NOTE: Coefficient already handled above
                    add(1.0, result[2], 1.0, value[2]),
                    add(1.0, result[3], 1.0, value[3])
                )
            else:
                result = add(
                    1.0,
                    result,
                    coefficient,
                    self.calculation(process, region)
                )

        # All done
        return result
