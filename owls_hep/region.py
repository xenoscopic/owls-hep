"""Provides routines for loading region selections and weights.

Regions are encoded as Python dictionaries with the following entries:

- 'label': The TLatex label to use for the region
- 'weight': The weight expression to use for the region
- 'selection': The selection expression to use for the region

This information is loaded from a YAML configuration file.  Within the file,
there should only be mappings from region names to configurations.  The
configuration for each region must include all fields.

Additionally, the region configuration may contain an entry named
'definitions', which may contain names mapping to expressions.  These names may
be used in the 'weight' and 'selection' expressions of region definitions by
writing them in square brackets.
"""


# System imports
from copy import deepcopy
import re

# owls-config imports
from owls_config import load as load_config

# owls-data imports
from owls_data.expression import multiplied, anded


# Global variables to store region configuration
_definitions = {}
_configuration = {}


def load_regions(configuration_path):
    """Loads region configuration from a YAML file.

    Args:
        configuration_path: The path to the YAML configuration file
    """
    # Switch to the global variables
    global _definitions
    global _configuration

    # Load the configuration
    _configuration = load_config(configuration_path)

    # Make sure it isn't empty
    if _configuration is None:
        raise RuntimeError('region configuration empty')

    # Extract definitions, if any
    if 'definitions' in _configuration:
        _definitions = _configuration.pop('definitions')


def region(name):
    """Loads a region configuration by name.

    Args:
        name: The name of the region configuration to load

    Returns:
        A region configuration dictionary.
    """
    # Create a regex to match definition specifications
    finder = re.compile('\[(.*?)\]')

    # Create a function which can be used to translate regex matches
    translator = lambda match: '({0})'.format(_definitions[match.group(1)])

    # Grab the configuration
    region = _configuration[name]

    # Create the result
    return {
        'label': region['label'],
        'weight': finder.sub(translator, region['weight']),
        'selection': finder.sub(translator, region['selection']),
    }


def reweight(region, expression):
    """Modifies a region configuration by multiplying the specified expression
    into the region weight.

    Args:
        region: The region configuration dictionary
        expression: The additional weighting expression

    Returns:
        A modified region configuration dictionary with the added weight.
    """
    # Create the result
    result = deepcopy(region)

    # Update the weight
    result['weight'] = multiplied(result['weight'], expression)

    # All done
    return result


def select(region, expression):
    """Modifies a region configuration by adding the additional selection
    requirement specified by the expression

    Args:
        region: The region configuration dictionary
        expression: The additional selection expression

    Returns:
        A modified region configuration dictionary with the added selection.
    """
    # Create the result
    result = deepcopy(region)

    # Update the weight
    result['selection'] = anded(result['selection'], expression)

    # All done
    return result


def weighted_selection(region):
    """Creates a weighted selection from a region configuration.

    Args:
        region: The region configuration dictionary

    Returns:
        A string representing the weighted selection expression.
    """
    return multiplied(region['weight'], region['selection'])
