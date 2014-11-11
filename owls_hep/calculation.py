"""Provides the base interface for all owls-hep calculations.
"""


# Set up default exports
__all__ = [
    'Calculation',
    'HigherOrderCalculation',
]


class Calculation(object):
    """Abstract base class for all calculations.
    """

    def __call__(self, process, region):
        """Executes the calculation and returns the result.

        Implementers must override this method.

        Args:
            process: The process providing the data for the calculation
            region: The region providing selection/weighting for the
                calculation

        Returns:
            The result of the calculation.
        """
        raise NotImplementedError('abstract method')


class HigherOrderCalculation(Calculation):
    """Abstract base class for higher order calculations.

    Higher order calculations wrap an underlying calculation and return a
    result which is some function of the results of the underlying calculation.
    The result may have a different return type than the underlying
    calculation and may be the result of several calls to the underlying
    calculation.

    The underlying calculation **must** be passed to the HigherOrderCalculation
    constructor, and is available via the `calculation` property.

    Implementers must still override the abstract methods of Calculation.
    """

    def __init__(self, calculation):
        """Initializes a new instance of the HigherOrderCalculation class.

        Subclasses **must** call this implementation if they override it.

        Args:
            calculation: The underlying calculation
        """
        # Store the calculation
        self._calculation = calculation

    @property
    def calculation(self):
        """Returns the underlying calculation.
        """
        return self._calculation
