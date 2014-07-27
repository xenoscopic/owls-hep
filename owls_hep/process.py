"""Provides routines for loading process configuration and data.

Processes are encoded as dictionary-like objects with the following entries:

- 'name': The name of the process
- 'label': The TLatex label to use for the process
- 'files': The ROOT files from which to load data, encoded as a list of partial
  URLs relative to some base
- 'patches': A tuple of functions to be applied to loaded data
- 'patch_properties': A Python set which encodes additional branches necessary
  to apply a patch
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
configuration key itself.  The 'patches' and 'patch_properties' properties must
also not be specified in configuration, but rather within Python code in the
using the `patch`/`retree` method of ProcessSpecification objects.  All other
configuration parameters may be omitted, and will take on the following default
values:

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


class ProcessSpecification(dict):
    """Represents a process specification.
    """

    def __repr__(self):
        """Reimplementation of __repr__ which is human-friendly and better for
        caching.
        """
        return '{0}<{1},{2}>'.format(self['name'],
                                     self['tree'],
                                     repr(self['patches']))

    def __setitem__(self, key, value):
        raise RuntimeError('process specifications are immutable')

    def pop(self, key):
        raise RuntimeError('process specifications are immutable')

    def popitem(self, item):
        raise RuntimeError('process specifications are immutable')

    def update(self, other):
        raise RuntimeError('process specifications are immutable')

    def clear(self):
        raise RuntimeError('process specifications are immutable')

    def relabeled(self, name):
        """Generates an identical process specification with the label changed.

        Args:
            label: The new label

        Returns:
            A new ProcessSpecification object.
        """
        # Compute the result information
        properties = dict(self)

        # Modify the tree
        properties['label'] = name

        # All done
        return ProcessSpecification(properties)

    def retreed(self, tree):
        """Generates an identical process specification with the target tree
        changed.

        Args:
            tree: The new tree value

        Returns:
            A new ProcessSpecification object.
        """
        # Compute the result information
        properties = dict(self)

        # Modify the tree
        properties['tree'] = tree

        # All done
        return ProcessSpecification(properties)

    def patched(self, patch, patch_properties):
        """Generates an identical process specification with the specified
        patch and patch properties added.

        Args:
            patch: A callable which transforms a Pandas DataFrame
            patch_properties: The properties which need to be loaded to apply
                the patch

        Returns:
            A new ProcessSpecification object.
        """
        # Compute the result information
        properties = dict(self)

        # Modify the patches
        properties['patches'] += (patch,)

        # Modify the patch properties
        properties['patch_properties'] = properties['patch_properties'].union(
            patch_properties
        )

        # All done
        return ProcessSpecification(properties)


def process(name):
    """Loads a process configuration by name.

    Args:
        name: The name of the process configuration to load

    Returns:
        A ProcessSpecification object.
    """
    # Grab the file prefix
    files_prefix = _defaults['files_prefix']

    # Grab the configuration
    process = _configurations[name]

    # Create the result
    return ProcessSpecification((
        ('name', name),
        ('label', process['label']),
        ('line_color', process.get('line_color', _defaults['line_color'])),
        ('fill_color', process.get('fill_color', _defaults['fill_color'])),
        ('marker_style', process.get('marker_style',
                                     _defaults['marker_style'])),
        ('files', ['{0}{1}'.format(files_prefix, f)
                   for f
                   in process['files']]),
        ('patches', ()),
        ('patch_properties', set()),
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
        properties.union(process['patch_properties']),
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
