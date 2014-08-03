"""Provides facilities for event estimation.
"""


# System imports
from functools import partial

# owls-hep imports
from owls_hep.config import load as load_config
from owls_hep.counting import count
from owls_hep.histogramming import histogram


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
