"""Provides facilities for event estimation.
"""


# System imports
from uuid import uuid4
from functools import partial

# ROOT imports
from ROOT import TH1

# owls-hep imports
from owls_hep.config import load as load_config
from owls_hep.counting import count
from owls_hep.histogramming import histogram


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
        result = value_1.Clone(uuid4().hex)

        # Scale it
        result.Scale(value)
    else:
        # Create the result
        result = (coefficient * value)

    # All done
    return result


class Estimation(object):
    def _init(self, processes, method):
        # Store parameters
        self._processes = processes
        self._method = method

    def count(self, region):
        return self._method(self._processes, region, count)

    def histogram(self, region, expressions, binnings):
        return self._method(
            self._processes,
            region,
            partial(histogram, expressions = expressions, binnings = binnings)
        )


class EstimationLoader(object):
    def __init__(self, estimations_path, process_loader):
        # Load configuration
        self._estimations = load_config(estimations_path)

        # Store process loader
        self._process_loader = process_loader

    def __call__(self, name):
        # Grab the configuration
        configuration = self._estimations[name]

        # Create the projection
        result = Estimation()

        # Load processes
        processes = configuration['processes']
        if isinstance(processes, list):
            processes = tuple((self._process_loader(p) for p in processes))
        else:
            processes = self._process_loader(processes)

        # Load the method
        full_method_name = configuration['method']
        method_module_name, method_name = full_method_name.rsplit('.', 1)
        method_module = __import__(method_module_name,
                                   fromlist = [method_name])
        method = getattr(method_module, method_name)

        # Initialize it
        result._init(processes, method)

        # All done
        return result
