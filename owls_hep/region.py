"""Provides routines for loading region selections and weights.

Regions are encoded as dictionary-like with the following entries:

- 'name': The name of the region
- 'label': The TLatex label to use for the region
- 'weight': The weight expression to use for the region
- 'selection': The selection expression to use for the region
- 'variations': A tuple of functions which accept two arguments, a weight
  expression and a selection expression, and return a 2-tuple of modified
  weight and selection expressions

This information is loaded from a YAML configuration file.  Within the file,
there should only be mappings from region names to configurations.  The
configuration for each region must include all fields, except 'name' which will
be taken from the configuration key itself.  The 'variations' properties must
also not be specified in configuration, but rather within Python code in the
`varied` method.

Users may provide a set of definitions, via the `load_definitions` method,
from a configuration file mapping definition names to expressions.  The
expressions may be substituted into weight/selection expressions by enclosing
their names into square brackets.  E.g.:

    In definitions.yml:

        base_selection: 'property1 && property2 > 5'

    In regions.yml

        my_region:
            label: 'My Region'
            selection: '[base_selection] && property3 == 7'
            weight: 'weight_property'
"""


# System imports
import re

# owls-data imports
from owls_data.expression import multiplied

# owls-hep imports
from owls_hep.config import load as load_config


# Global variables to store region configuration and definitions
_definitions = {}
_configurations = {}


def load_definitions(configuration_path):
    """Loads region definitions from a YAML file.

    `.local.yml`-style configuration overrides are supported.

    Args:
        configuration_path: The path to the YAML configuration file
    """
    # Load the configuration
    _definitions.update(load_config(configuration_path))


def load_regions(configuration_path):
    """Loads region configurations from a YAML file.

    `.local.yml`-style configuration overrides are supported.

    Args:
        configuration_path: The path to the YAML configuration file
    """
    _configurations.update(load_config(configuration_path))


# Private class to implement friendly __repr__ for regions
class RegionSpecification(dict):
    def __repr__(self):
        return '{0}<{1}>'.format(self['name'],
                                 repr(self['variations']))

    def __setitem__(self, key, value):
        raise RuntimeError('region specifications are immutable')

    def pop(self, key):
        raise RuntimeError('process specifications are immutable')

    def popitem(self, item):
        raise RuntimeError('process specifications are immutable')

    def update(self, other):
        raise RuntimeError('process specifications are immutable')

    def clear(self):
        raise RuntimeError('process specifications are immutable')

    def varied(self, variation):
        """Generates an identical region specification with the specified
        variation added.

        Args:
            variation: A callable which transforms a 2-tuple of a weight and
                selection expression

        Returns:
            A new RegionSpecification object.
        """
        # Compute the result information
        properties = dict(self)

        # Modify the patches
        properties['variations'] += (variation,)

        # All done
        return RegionSpecification(properties)


def region(name):
    """Loads a region configuration by name.

    Args:
        name: The name of the region configuration to load

    Returns:
        A RegionSpecification object.
    """
    # Create a regex to match definition specifications
    finder = re.compile('\[(.*?)\]')

    # Create a function which can be used to translate regex matches
    translator = lambda match: '({0})'.format(_definitions[match.group(1)])

    # Grab the configuration
    region = _configurations[name]

    # Create the result
    return RegionSpecification((
        ('name', name),
        ('label', region['label']),
        ('weight', finder.sub(translator, region['weight'])),
        ('selection', finder.sub(translator, region['selection'])),
        ('variations', ()),
    ))


def weighted_selection(region):
    """Creates a weighted selection from a region configuration, with all
    variations applied to the base weight and selection expressions.

    Args:
        region: The region configuration dictionary

    Returns:
        A string representing the weighted selection expression.
    """
    # Get the base weight and selection expressions
    weight = region['weight']
    selection = region['selection']

    # Apply any variations
    for variation in region['variations']:
        weight, selection = variation(weight, selection)

    # Compute the combined expression
    return multiplied(weight, selection)
