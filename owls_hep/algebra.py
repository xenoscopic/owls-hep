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

    For uncertainty tuples, the addition is done by recursively calling for
    each component of the uncertainty.  This is because we're not trying to
    combine uncertainties, but rather propagate them appropriately through
    estimation.

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
    if isinstance(value_1, tuple):
        # Unpack
        overall_up_1, overall_down_1, shape_up_1, shape_down_1 = value_1
        overall_up_2, overall_down_2, shape_up_2, shape_down_2 = value_2

        # Handle overall_up
        if None not in (overall_up_1, overall_up_2):
            overall_up = add(
                coefficient_1,
                overall_up_1,
                coefficient_2,
                overall_up_2
            )
        else:
            overall_up = None

        # Handle overall_down
        if None not in (overall_down_1, overall_down_2):
            overall_down = add(
                coefficient_1,
                overall_down_1,
                coefficient_2,
                overall_down_2
            )
        else:
            overall_down = None

        # Handle shape_up
        if None not in (shape_up_1, shape_up_2):
            shape_up = add(
                coefficient_1,
                shape_up_1,
                coefficient_2,
                shape_up_2
            )
        else:
            shape_up = None

        # Handle shape_down
        if None not in (shape_down_1, shape_down_2):
            shape_down = add(
                coefficient_1,
                shape_down_1,
                coefficient_2,
                shape_down_2
            )
        else:
            shape_down = None

        # Repack
        result = (overall_up, overall_down, shape_up, shape_down)
    elif isinstance(value_1, TH1):
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
    if isinstance(value, tuple):
        # Unpack
        overall_up, overall_down, shape_up, shape_down = value

        # Handle values which aren't None
        if overall_up is not None:
            overall_up = multiply(coefficient, overall_up)
        if overall_down is not None:
            overall_down = multiply(coefficient, overall_down)
        if shape_up is not None:
            shape_up = multiply(coefficient, shape_up)
        if shape_down is not None:
            shape_down = multiply(coefficient, shape_down)

        # Repack
        result = (overall_up, overall_down, shape_up, shape_down)
    elif isinstance(value, TH1):
        # Create the result
        result = value.Clone(uuid4().hex)

        # Scale it
        result.Scale(coefficient)
    else:
        # Create the result
        result = (coefficient * value)

    # All done
    return result
