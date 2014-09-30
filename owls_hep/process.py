"""Provides models for processes and process patches.
"""


# System imports
from copy import deepcopy
from functools import wraps

# Six imports
from six import string_types

# owls-data imports
from owls_data.loading import load as load_data


class Patch(object):
    """Represents a patch to apply to a process' data.
    """

    def properties(self):
        """Returns a Python set of properties of the data required to evaluate
        the patch.

        Implementers must override this method.
        """
        raise NotImplementedError('abstract method')

    def __call__(self, data):
        """Applies the patch to a DataFrame.

        The provided DataFrame will be a copy which can be freely mutated.

        Implementers must override this method.

        Args:
            data: The DataFrame to patch
        """
        raise NotImplementedError('abstract method')


class Process(object):
    """Represents a physical process whose events may be encoded in one or more
    data files and which should be rendered according to a certain style.
    """

    def __init__(self,
                 name,
                 files,
                 tree,
                 label,
                 line_color,
                 fill_color,
                 marker_style):
        """Initializes a new instance of the Process class.

        Args:
            name: A name by which to refer to the process
            files: An iterable of ROOT file paths for files representing the
                process
            tree: The ROOT TTree path within the files to use
            label: The ROOT TLatex label string to use when rendering the
                process
            line_color: The ROOT TColor number or hex string (#rrggbb) to use
                as the line color when rendering the process
            fill_color: The ROOT TColor number or hex string (#rrggbb) to use
                as the fill color when rendering the process
            marker_style: The ROOT TMarker number to use as the marker style
                when rendering the process
        """
        # Store parameters
        self._name = name
        self._files = tuple(files)
        self._tree = tree
        self._label = label
        self._line_color = line_color
        self._fill_color = fill_color
        self._marker_style = marker_style

        # Create initial patches container
        self._patches = ()

    def __hash__(self):
        """Returns a hash for the process.
        """
        # Hash only files, tree, and patches since those are all that really
        # matter for data loading
        return hash((self._files, self._tree, self._patches))

    @property
    def name(self):
        return self._name

    def load(self, properties):
        """Loads the given properties of the process data.

        The tree weights of the TTrees are included in the resultant DataFrame
        as the 'tree_weight' property.

        Args:
            properties: A Python set of property names (TTree branch names) to
                load

        Returns:
            A Pandas DataFrame containing the specified properties for the
            process.
        """
        # Compute the properties we need to load
        all_properties = set.union(properties,
                                   *(p.properties() for p in self._patches))

        # Load data, specifying ourselves as the cache name, because if we
        # apply patches, the resultant DataFrame will be mutated but still
        # transiently cached, and the load method won't know anything about it
        result = load_data(self._files, properties, {
            'tree': self._tree,
            'tree_weight_property': 'tree_weight'
        }, cache = self)

        # Apply patches
        for p in self._patches:
            result = p(result)

        # All done
        return result

    def retreed(self, tree):
        """Creates a new copy of the process with a different tree.

        Args:
            tree: The tree to set for the new process

        Returns:
            A copy of the process with the tree modified.
        """
        # Create the copy
        result = deepcopy(self)

        # Retree
        result._tree = tree

        # All done
        return result

    def patched(self, patch):
        """Creates a new copy of the process with a patch applied.

        Args:
            patch: The patch to apply in the new process

        Returns:
            A copy of the process with the additional patch applied.
        """
        # Create the copy
        result = deepcopy(self)

        # Add the patch
        result._patches += (patch,)

        # All done
        return result


def styled(f):
    """Decorator to apply process style to a histogram returned by a function.

    The process must be the first argument of the function.

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

        # Make lines visible
        result.SetLineWidth(2)

        # All done
        return result

    # Return the wrapper function
    return wrapper
