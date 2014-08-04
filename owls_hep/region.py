"""Provides routines for loading region selections and weights.
"""


# System imports
import re
from copy import deepcopy

# owls-data imports
from owls_data.expression import multiplied

# owls-hep imports
from owls_hep.config import load as load_config


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


def load(regions_path, definitions_path):
    # Load the configurations
    regions = load_config(regions_path)
    definitions = load_config(definitions_path)

    # Create a definition finder/translator
    finder = re.compile('\[(.*?)\]')
    translator = lambda match: '({0})'.format(definitions[match.group(1)])

    # Create the function to load individual regions
    def region_loader(name):
        # Grab the region configuration
        configuration = regions[name]

        # Extract parameters
        weight = configuration['weight']
        selection = configuration['selection']
        label = configuration['label']

        # Translate definitions
        weight = finder.sub(translator, weight)
        selection = finder.sub(translator, selection)

        # Create the region
        region = Region()

        # Set parameters
        region._init(name, weight, selection, label)

        # All done
        return region

    # Return the loader
    return region_loader
