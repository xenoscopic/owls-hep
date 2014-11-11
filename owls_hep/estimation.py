"""Provides the base class for all estimation schemes.
"""


# owls-hep imports
from owls_hep.calculation import HigherOrderCalculation


# Set up default exports
__all__ = [
    'Estimation',
]


class Estimation(HigherOrderCalculation):
    """Abstract base class for all estimation schemes.

    All estimation calculations should return the same type as their underlying
    calculation.
    """
    pass
