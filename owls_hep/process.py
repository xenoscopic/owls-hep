"""Provides routines for loading process configuration and data.

Processes are encoded as Python dictionaries with the following entries:

- 'label': The TLatex label to use for the process
- 'line_color': The line color to use for the process in plots, as a
  hexidecimal string of the form '#xxxxxx' or as a numeric ROOT color code
- 'fill_color': The fill color to use for the process in plots, as a
  hexidecimal string of the form '#xxxxxx' or as a numeric ROOT color code
- 'marker_style': The marker style to use, or empty for no style
- 'files': The ROOT files from which to load data, encoded as a list of partial
  URLs relative to some base
- 'patches': A tuple of functions to be applied to loaded data
- 'patch_branches': A Python set which encodes additional branches necessary to
  apply a patch
- 'tree': The name of the tree within the ROOT files to load

This information is loaded from a YAML configuration file.  Within the file,
there should only be mappings from process names to configurations.  The
configuration for each process must include at least the 'label' and 'files'
information provided.

Additionally, the configuration file should contain an entry named 'defaults',
which should point to a mapping containing the following keys mapping to
default values:

- 'line_color': The default line color
- 'fill_color': The default fill color
- 'marker_style': The default marker style
- 'files_prefix': The base of all file URLs
- 'tree': The default tree to use

In the event that these keys are not provided for a process, these default
values will be used.  The 'files_prefix' value will be prepended to all 'files'
entries.

The patches tuple will always default to empty.
"""


# System imports
from copy import deepcopy
from functools import wraps

# Six imports
from six import string_types

# ROOT imports
from ROOT import TColor

# owls-config imports
from owls_config import load as load_config

# owls-cache imports
from owls_cache.transient import cached as transiently_cached

# owls-data imports
from owls_data.loading import load as load_data


# Global variables to store process configuration
_defaults = {}
_configuration = {}


def load_processes(configuration_path):
    """Loads process configuration from a YAML file.

    Args:
        configuration_path: The path to the YAML configuration file
    """
    # Switch to the global variables
    global _defaults
    global _configuration

    # Load the configuration
    _configuration = load_config(configuration_path)

    # Make sure it isn't empty
    if _configuration is None:
        raise RuntimeError('process configuration empty')

    # Extract defaults
    _defaults = _configuration.pop('defaults')


def process(name):
    """Loads a process configuration by name.

    Args:
        name: The name of the process configuration to load

    Returns:
        A process configuration dictionary.
    """
    # Grab the file prefix
    files_prefix = _defaults['files_prefix']

    # Grab the configuration
    process = _configuration[name]

    # Create the result
    return {
        'label': process['label'],
        'line_color': process.get('line_color', _defaults['line_color']),
        'fill_color': process.get('fill_color', _defaults['fill_color']),
        'marker_style': process.get('marker_style', _defaults['marker_style']),
        'files': ['{0}{1}'.format(files_prefix, f) for f in process['files']],
        'patches': (),
        'patch_branches': set(),
        'tree': process.get('tree', _defaults['tree']),
    }


def patch(process, patch, branches):
    """Adds a patch to a process.

    Args:
        process: The process configuration dictionary
        patch: A function which takes and returns a Pandas DataFrame
        branches: Additional branches which must be loaded in order to apply
            the patch, as a Python set

    Returns:
        A modified process configuration dictionary with the added patch.
    """
    # Create the result
    result = deepcopy(process)

    # Update the patch list and branches
    result['patches'] = result['patches'] + (patch,)
    result['patch_branches'] = result['patch_branches'].union(branches)

    # All done
    return result


def tree(process, tree):
    """Creates a variation of the process which loads a different tree.

    Args:
        process: The process configuration dictionary
        tree: The new tree path

    Returns:
        A modified process configuration dictionary with the new tree value.
    """
    # Create the result
    result = deepcopy(process)

    # Update the tree
    result['tree'] = tree

    # All done
    return result


@transiently_cached
def load(process, branches):
    """Loads the data associated with the process configuration.

    Args:
        process: The process configuration dictionary
        branches: The tree branches to load, as a Python set

    Returns:
        A Pandas DataFrame containing the process data.  The tree weight will
        be loaded into a virtual property called 'tree_weight'.
    """
    # Load the data
    result = load_data(
        process['files'],
        branches.union(process['patch_branches']),
        {
            'tree': process['tree'],
            'tree_weight_property': 'tree_weight'
        }
    )

    # Apply any patches
    for patch in process['patches']:
        result = patch(result)

    # All done
    return result


def styled(f):
    """Decorator which provides styling capability for functions returning
    THN objects.  The wrapper function should accept a process configuration
    dictionary as its first argument.
    """
    # Create the wrapper function
    @wraps(f)
    def wrapper(process, *args, **kwargs):
        # Compute the result
        result = f(process, *args, **kwargs)

        # Get style
        line_color = process['line_color']
        fill_color = process['fill_color']
        marker_style = process['marker_style']

        # Translate hex colors if necessary
        if isinstance(line_color, string_types):
            line_color = TColor.GetColor(line_color)
        if isinstance(fill_color, string_types):
            fill_color = TColor.GetColor(fill_color)

        # Apply style
        result.SetLineColor(line_color)
        result.SetFillColor(fill_color)
        if marker_style is not None:
            result.SetMarkerStyle(marker_style)
            result.SetMarkerSize(1)
            result.SetMarkerColor(result.GetLineColor())

        # All done
        return result

    # Return the wrapper function
    return wrapper
