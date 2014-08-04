"""Provides routines for loading process configuration and data.
"""


# System imports
from functools import wraps
from copy import deepcopy

# Six imports
from six import string_types

# owls-data imports
from owls_data.loading import load as load_data

# owls-hep imports
from owls_hep.config import load as load_config


class Patch(object):
    def name(self):
        raise NotImplementedError('abstract method')

    def properties(self):
        raise NotImplementedError('abstract method')

    def __call__(self, data):
        raise NotImplementedError('abstract method')


class Process(object):
    def _init(self, name, files, tree, label, line_color, fill_color,
              marker_style):
        # Store parameters
        self._name = name
        self._files = files
        self._tree = tree
        self._label = label
        self._line_color = line_color
        self._fill_color = fill_color
        self._marker_style = marker_style

        # Set default parameters
        self._patches = ()

    def __repr__(self):
        return '{0}[{1}]<{2}>'.format(
            self._name,
            self._tree,
            ','.join((p.name() for p in self._patches))
        )

    def __call__(self, properties):
        # Load data, specifying our own representation as the cache name,
        # because if we apply patches, the resultant DataFrame will be mutated
        # but still transiently cached, and the load method won't know anything
        # about it
        result = load_data(
            self._files,
            properties.union(*(p.properties() for p in self._patches)),
            {
                'tree': self._tree,
                'tree_weight_property': 'tree_weight'
            },
            cache = repr(self)
        )

        # Apply patches
        for p in self._patches:
            result = p.apply(result)

        # All done
        return result

    def retreed(self, tree):
        # Create a copy
        result = deepcopy(self)

        # Update the tree
        result._tree = tree

        # All done
        return result

    def patched(self, patch):
        # Create a copy
        result = deepcopy(self)

        # Update patches
        result._patches += (patch,)

        # All done
        return result


def load(processes_path, defaults_path):
    # Load the configurations
    processes = load_config(processes_path)
    defaults = {
        'file_prefix': '',
        'tree': 'tree',
        'label': 'Process',
        'line_color': 1,
        'fill_color': 0,
        'marker_style': None,
    }
    defaults.update(load_config(defaults_path))

    # Create the function to load individual processes
    def process_loader(name):
        # Grab the region configuration
        configuration = processes[name]

        # Get the files
        prefix = defaults['file_prefix']
        files = ['{0}{1}'.format(prefix, f) for f in configuration['files']]

        # Get the initial tree
        tree = defaults['tree']

        # Get style parameters
        label = configuration.get('label', defaults['label'])
        line_color = configuration.get('line_color', defaults['line_color'])
        fill_color = configuration.get('fill_color', defaults['fill_color'])
        marker_style = configuration.get('marker_style',
                                         defaults['marker_style'])

        # Create the process
        process = Process()

        # Set parameters
        process._init(
            name,
            files,
            tree,
            label,
            line_color,
            fill_color,
            marker_style
        )

        # All done
        return process

    # Return the loader
    return process_loader


def styled(f):
    """Decorator to apply process style to a histogram returned by a function.

    The process name must be the first argument of the function.

    Args:
        f: The function to wrap, which must return a ROOT THN object

    Returns:
        A function that returns styled THN objects.
    """
    # Create the wrapper function
    @wraps(f)
    def wrapper(process, *args, **kwargs):
        # Compute the result
        result = f(process, *args, **kwargs)

        # Extract style
        title = process._label
        line_color = process._line_color
        fill_color = process._fill_color
        marker_style = process._marker_style

        # Translate hex colors if necessary
        if isinstance(line_color, string_types):
            line_color = TColor.GetColor(line_color)
        if isinstance(fill_color, string_types):
            fill_color = TColor.GetColor(fill_color)

        # Apply style
        result.SetTitle(title)
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
