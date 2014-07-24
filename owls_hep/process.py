"""Provides routines for loading process configuration and data.

Processes are encoded as dictionary-like objects with the following entries:

- 'name': The name of the process
- 'label': The TLatex label to use for the process
- 'files': The ROOT files from which to load data, encoded as a list of partial
  URLs relative to some base
- 'patches': A tuple of functions to be applied to loaded data
- 'patch_branches': A Python set which encodes additional branches necessary to
  apply a patch
- 'tree': The name of the tree within the ROOT files to load
- 'line_color': The line color to use for the process in plots, as a
  hexidecimal string of the form '#xxxxxx' or as a numeric ROOT color code
- 'fill_color': The fill color to use for the process in plots, as a
  hexidecimal string of the form '#xxxxxx' or as a numeric ROOT color code
- 'marker_style': The marker style to use, or None for no style

This information is loaded from a YAML configuration file, using the
`load_processes` method.  Within the file, there should only be mappings from
process names to configurations.  The configuration for each process must
include at least the 'label' and 'files' information provided.  The 'name'
parameter should not be included, as it will be determined from the
configuration key itself.  The 'patches' and 'patch_branches' properties must
also not be specified in configuration, but rather within Python code in the
`process` method.  All other configuration parameters may be omitted, and will
take on the following default values:

- 'tree': 'tree'
- 'line_color': 1
- 'fill_color': 0
- 'marker_style': None

These defaults may be overridden from a configuration file by calling the
`load_defaults` method.

Finally, if the configuration file passed to `load_defaults` contains an entry
named 'files_prefix', it will be pre-pended to all file paths specified in the
process configurations.  The pre-pending does not include the addition of any
'/' characters - it is simple concatenation.
"""


# owls-cache imports
from owls_cache.transient import cached as transiently_cached

# owls-data imports
from owls_data.loading import load as load_data

# owls-hep imports
from owls_hep.config import load as load_config


# Global variables to store process configuration and defaults
_defaults = {
    'files_prefix': '',
    'tree': 'tree',
    'line_color': 1,
    'fill_color': 0,
    'marker_style': None,
}
_configurations = {}


def load_defaults(configuration_path):
    """Loads process configuration defaults from a YAML file.

    `.local.yml`-style configuration overrides are supported.

    Args:
        configuration_path: The path to the YAML configuration file
    """
    # Load the configuration
    _defaults.update(load_config(configuration_path))


def load_processes(configuration_path):
    """Loads process configurations from a YAML file.

    `.local.yml`-style configuration overrides are supported.

    Args:
        configuration_path: The path to the YAML configuration file
    """
    _configurations.update(load_config(configuration_path))


# Private class to implement friendly __repr__ for processes
class _Process(dict):
    def __repr__(self):
        return '{0}<{1},{2}>'.format(self['name'],
                                     self['tree'],
                                     repr(self['patches']))


def process(name, tree = None, patches = (), patch_properties = set()):
    """Loads a process configuration by name.

    Args:
        name: The name of the process configuration to load
        tree: If not None, this will override any value in
            configuration/defaults
        patches: A tuple of callables, each of which must take and return a
            Pandas DataFrame, which will be applied to the process upon loading
        patch_branches: A Python set of properties of the data which need to be
            loaded for the patches to be applied

    Returns:
        A process configuration object, which behaves like a dictionary.
    """
    # Grab the file prefix
    files_prefix = _defaults['files_prefix']

    # Grab the configuration
    process = _configurations[name]

    # Create the result
    return _Process((
        ('name', name),
        ('label', process['label']),
        ('line_color', process.get('line_color', _defaults['line_color'])),
        ('fill_color', process.get('fill_color', _defaults['fill_color'])),
        ('marker_style', process.get('marker_style',
                                     _defaults['marker_style'])),
        ('files', ['{0}{1}'.format(files_prefix, f)
                   for f
                   in process['files']]),
        ('patches', patches),
        ('patch_branches', patch_properties),
        ('tree', process.get('tree', _defaults['tree'])),
    ))


@transiently_cached
def load_process_data(process, properties):
    """Loads the data associated with the process configuration.

    Args:
        process: The process configuration dictionary
        properties: The tree branches to load, as a Python set

    Returns:
        A Pandas DataFrame containing the process data.  The tree weight will
        be loaded into a virtual property called 'tree_weight'.
    """
    # Load the data
    result = load_data(
        process['files'],
        properties.union(process['patch_branches']),
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
