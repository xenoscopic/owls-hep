"""Provides the base class for all estimation schemes.
"""


# owls-hep imports
from owls_hep.calculation import Calculation


class Estimation(Calculation):
    """Abstract base class for all estimation schemes.

    All estimation calculations should return the same type as their underlying
    calculation.

    The underlying calculation can be evaluated using the `calculation` method.
    """

    def __init__(self, calculation):
        """Initializes a new instance of the Estimation class.

        Subclasses should call this method.

        Args:
            calculation: The base calculation, which should return either a
                count or a histogram.  This will be accessible via the
                `calculation` member function.
        """
        # Store the calculation
        self._calculation = calculation

    def calculation(self, process, region):
        """Executes the underlying calculation, for use by subclasses.

        Args:
            process: The process to consider
            region: The region to consider

        Returns:
            The result of the underlying calculation.
        """
        return self._calculation(process, region)

    def __call__(self, process, region):
        """Calculates the result using the estimation scheme.

        Implementers must override this method.

        Args:
            process: The process to consider
            region: The region to consider

        Returns:
            The same type as the underlying calculation, with the value
            determined by the estimation scheme.
        """
        raise NotImplementedError('abstract method')
