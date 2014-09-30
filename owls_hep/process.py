"""Provides routines for loading process configuration and data.
"""


# System imports
from copy import deepcopy
from functools import wraps

# Six imports
from six import string_types

# owls-cache imports
from owls_cache.transient import cached

# owls-data imports
from owls_data.loading import load as load_data


class Process(object):
    """Represents a physical process whose events may be encoded in one or more
    data files and which should be rendered according to a certain style.
    """

    def __init__(self,
                 files,
                 tree,
                 label,
                 line_color,
                 fill_color,
                 marker_style):
        """Initializes a new instance of the Process class.

        Args:
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
        self._files = tuple(files)
        self._tree = tree
        self._label = label
        self._line_color = line_color
        self._fill_color = fill_color
        self._marker_style = marker_style

    def __eq__(self, other):
        """Checks for equivalence between processes.

        Args:
            other: The other object to test

        Returns:
            True if self and other are equivalent processes, False otherwise.
        """
        # Check types
        if not isinstance(other, Process):
            return False

        # Check only files and trees, since those are all that really matter
        # for data loading
        return self._files == other._files and self._tree == other._tree

    def __hash__(self):
        """Returns a hash for the process.
        """
        # Hash only files and trees, since those are all that really matter for
        # data loading
        return hash((self._files, self._tree))

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
        # Load data, specifying our own representation as the cache name,
        # because if we apply patches, the resultant DataFrame will be mutated
        # but still transiently cached, and the load method won't know anything
        # about it
        return load_data(self._files, properties, {
            'tree': self._tree,
            'tree_weight_property': 'tree_weight'
        })

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


class PatchedProcess(Process):
    """Represents a process which applies some patching function to its data.

    This is an abstract class, and implementers are required to override the
    `properties` and `patch` methods.
    """

    def __init__(self, process):
        """Initializes a new instance of the PatchedProcess class.

        Args:
            process: The process to wrap
        """
        # Extract parameters from the underlying process
        self._files = process._files
        self._tree = process._tree
        self._label = process._label
        self._line_color = process._line_color
        self._fill_color = process._fill_color
        self._marker_style = process._marker_style

    def properties(self):
        """Returns a Python set of properties which need to be loaded from the
        data in order to apply the patch.

        Implementers must override this method.
        """
        raise NotImplementedError('abstract method')

    def patch(self, data):
        """Applies a patch to a DataFrame.

        Implementers must override this method.  The DataFrame should be
        mutated in-place.

        Args:
            data: The DataFrame to patch
        """
        raise NotImplementedError('abstract method')

    @cached(lambda properties: (tuple(properties),))
    def load(self, properties):
        """Loads the given properties of the process data and applies a patch.

        The tree weights of the TTrees are included in the resultant DataFrame
        as the 'tree_weight' property.

        Args:
            properties: A Python set of property names (TTree branch names) to
                load

        Returns:
            A patched Pandas DataFrame containing the specified properties for
            the process.
        """
        # Compute the full required properties
        all_properties = set.union(properties, self.properties())

        # Call the underlying load method, making a copy of the result so-as
        # not to mutate something which is cached
        result = super(PatchedProcess, self).load(all_properties).copy()

        # Apply the patch
        self.patch(result)

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
