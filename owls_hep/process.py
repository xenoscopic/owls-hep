"""Provides routines for loading process configuration and data.

Processes are encoded as Python dictionaries with the following entries:

- 'label': The TLatex label to use for the process
- 'line_color': The line color to use for the process in plots, either a
  hexidecimal code of the form '#xxxxxx' or a numeric ROOT color code
- 'fill_color': The fill color to use for the process in plots, either a
  hexidecimal code of the form '#xxxxxx' or a numeric ROOT color code
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
- 'files_prefix': The base of all file URLs
- 'tree': The default tree to use

In the event that these keys are not provided for a process, these default
values will be used.  The 'files_prefix' value will be prepended to all 'files'
entries.

The patches tuple will always default to empty.
"""


# System imports
from copy import deepcopy

# owls-config imports
from owls_config import load as load_config

# owls-cache imports
from owls_cache.transient import cached as transiently_cached

# owls-data imports
from owls_data.loading import load as load_data


# Global variable to store process configuration
_configuration = {}


def load_processes(configuration_path):
    """Loads process configuration from a YAML file.

    Args:
        configuration_path: The path to the YAML configuration file
    """
    # Switch to the global variable
    global _configuration

    # Load the configuration
    _configuration = load_config(configuration_path)


def process(name):
    """Loads a process configuration by name.

    Args:
        name: The name of the process configuration to load

    Returns:
        A process configuration dictionary.
    """
    # Grab defaults
    defaults = _configuration['defaults']

    # Grab the file prefix
    file_prefix = defaults['files_prefix']

    # Grab the configuration
    process = _configuration[name]

    # Create the result
    return {
        'label': process['label'],
        'line_color': process.get('line_color', defaults['line_color']),
        'fill_color': process.get('fill_color', defaults['fill_color']),
        'files': ['{0}{1}'.format(files_prefix, f) for f in process['files']],
        'patches': (),
        'patch_branches': set(),
        'tree': process.get('tree', defaults['tree']),
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
