"""Provides routines for loading region selections and weights.
"""


# System imports
import re
from copy import deepcopy

# owls-data imports
from owls_data.expression import multiplied

# owls-hep imports
from owls_hep.config import load_config


class Variation(object):
    def name(self):
        raise NotImplementedError('abstract method')

    def __call__(self, weight, selection):
        raise NotImplementedError('abstract method')


class Region(object):
    def _init(self, name, weight, selection, label):
        # Store parameters
        self._name = name
        self._weight = weight
        self._selection = selection
        self._label = label

        # Set default parameters
        self._variations = ()

    def name(self):
        return self._name

    def __repr__(self):
        return '{0}<{1}>'.format(
            self._name,
            ','.join((v.name() for v in self._variations))
        )

    def __call__(self):
        # Grab resultant weight/selection
        weight, selection = self._weight, self._selection

        # Apply any variations
        for v in self._variations:
            weight, selection = v(weight, selection)

        # Compute the combined expression
        return multiplied(weight, selection)

    def varied(self, variation):
        # Create a copy
        result = deepcopy(self)

        # Update patches
        result._variations += (variation,)

        # All done
        return result


class RegionLoader(object):
    def __init__(self, regions_path, definitions_path):
        # Load configuration
        self._regions = load_config(regions_path)
        self._definitions = load_config(definitions_path)

        # Create a definition translator
        self._finder = re.compile('\[(.*?)\]')
        self._translator = lambda match: '({0})'.format(
            self._definitions[match.group(1)]
        )

    def __call__(self, name):
        # Grab the process configuration
        configuration = self._regions[name]

        # Get parameters
        weight = configuration['weight']
        selection = configuration['selection']
        label = configuration['label']
        
        # Translate definitions
        weight = self._finder.sub(self._translator, weight)
        selection = self._finder.sub(self._translator, selection)

        # Create the process
        result = Region()

        # Set parameters
        result._init(name, weight, selection, label)

        # All done
        return result
