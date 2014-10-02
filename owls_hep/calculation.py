"""Provides the base interface for all owls-hep calculations.
"""


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
