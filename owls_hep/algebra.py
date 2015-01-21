"""Provides a common algebra for scalar counts and histograms.
"""


# System imports
from uuid import uuid4

# ROOT imports
from ROOT import TH1


def add(coefficient_1, value_1, coefficient_2, value_2):
    """Provides an addition algebra for various types, including scalars and
    histogram objects.

    Incoming values are not modified.

    Args:
        coefficient_1: The first coefficient, a scalar
        value_1: The first value, a histogram or scalar
        coefficient_2: The second coefficient, a scalar
        value_2: The second value, a histogram or scalar

    Returns:
        The value of the expression:
            ((coefficient_1 * value_1) + (coefficient_2 * value_2))
    """
    # Verify that the incoming types match
    if type(value_1) != type(value_2):
        raise ValueError('values must be of the same type')

    # Handle based on type
    if isinstance(value_1, TH1):
        # Create the result
        result = value_1.Clone(uuid4().hex)

        # Add the histograms
        result.Add(value_1, value_2, coefficient_1, coefficient_2)
    else:
        # Create the result
        result = ((coefficient_1 * value_1) + (coefficient_2 * value_2))

    # All done
    return result


def multiply(coefficient, value):
    """Provides a multiplication algebra for various types, including scalars
    and histogram objects.

    Incoming values are not modified.

    Args:
        coefficient: The coefficient, a scalar
        value: The value, a histogram or scalar

    Returns:
        The value of the expression:
            (coefficient * value)
    """
    # Handle based on type
    if isinstance(value, TH1):
        # Create the result
        result = value.Clone(uuid4().hex)

        # Scale it
        result.Scale(coefficient)
    else:
        # Create the result
        result = (coefficient * value)

    # All done
    return result
