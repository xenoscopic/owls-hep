"""Provides the base class for all estimation schemes.
"""


# owls-hep imports
from owls_hep.calculation import HigherOrderCalculation


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
    pass
