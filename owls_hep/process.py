"""Provides models for processes and process patches.
"""


# System imports
import warnings
from inspect import getsource
from copy import deepcopy

# Six imports
from six import string_types

# Pandas imports
from pandas import DataFrame

# root_numpy imports
from root_numpy import root2array, RootNumpyUnconvertibleWarning

# owls-hep imports
from owls_hep.expression import normalized, properties


# Set up default exports
__all__ = [
    'Patch',
    'Filter',
    'Process',
]


# Ignore root_numpy unconvertible warnings
warnings.simplefilter('ignore', RootNumpyUnconvertibleWarning)


class Patch(object):
    """Represents a patch to apply to a process' data.
    """

    def __hash__(self):
        """Returns a unique hash for the patch.

        This method should not be overridden.
        """
        # HACK: Use the implementation of the patch in the hash, because the
        # behavior of the patch is what should determine hash equality, and
        # it's impossible to determine solely on type if the implementation
        # changes.
        return hash((self.state(), getsource(self.__call__)))

    def state(self):
        """Returns a representation of the patch's internal state, if any.

        This method is used to generate a unique hash for the patch for the
        purposes of caching.  If a patch has no internal state, and it's
        behavior is determined entirely by its type, then the implementer need
        not override this method.  However, if a patch contains state which
        affects its patching behavior, this method needs to be overridden.  A
        simple tuple may be returned containing the state of the patch.

        Returns:
            A hashable object representing the internal state of the patch.
        """
        return ()

    def properties(self):
        """Returns a Python set of properties of the data required to evaluate
        the patch.

        Implementers must override this method if they require any properties
        to be loaded, as the default implementation returns an empty set.

        Returns:
            A Python set containing strings of the required patch properties.
        """
        return set()

    def __call__(self, data):
        """Applies the patch to a DataFrame.

        The provided DataFrame may be mutated in-place, as it will not be
        re-used.  In any event, the patched DataFrame should be returned.

        Implementers must override this method.

        Args:
            data: The DataFrame to patch

        Returns:
            The patched DataFrame.
        """
        raise NotImplementedError('abstract method')


class Filter(Patch):
    """A reusable process patch that filters events according to an expression.
    """

    def __init__(self, selection):
        """Initializes a new instance of the Filter class.

        Args:
            selection: The selection expression to apply to the process data
        """
        self._selection = normalized(selection)

    def properties(self):
        """Returns a Python set of properties of the data required to evaluate
        the patch.

        Returns:
            A Python set containing strings of the required patch properties.
        """
        return properties(self._selection)

    def __call__(self, data):
        """Applies the selection to a DataFrame.

        Args:
            data: The DataFrame to patch

        Returns:
            The patched DataFrame.
        """
        return data[data.eval(self._selection)]


class Process(object):
    """Represents a physical process whose events may be encoded in one or more
    data files and which should be rendered according to a certain style.
    """

    def __init__(self,
                 files,
                 tree,
                 label,
                 line_color = 1,
                 fill_color = 0,
                 marker_style = None,
                 metadata = None):
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
            metadata: A (pickleable) object containing optional metadata
        """
        # Store parameters
        self._files = tuple(files)
        self._tree = tree
        self._label = label
        self._line_color = line_color
        self._fill_color = fill_color
        self._marker_style = marker_style
        self._metadata = metadata

        # Translate hex colors if necessary
        if isinstance(self._line_color, string_types):
            self._line_color = TColor.GetColor(self._line_color)
        if isinstance(self._fill_color, string_types):
            self._fill_color = TColor.GetColor(self._fill_color)

        # Create initial patches container
        self._patches = ()

    def __hash__(self):
        """Returns a hash for the process.
        """
        # Hash only files, tree, and patches since those are all that really
        # matter for data loading
        return hash((self._files, self._tree, self._patches))

    def metadata(self):
        """Returns the metadata for the process, if any.
        """
        return self._metadata

    def load(self, properties):
        """Loads the given properties of the process data.

        The tree weights of the TTrees are included in the resultant DataFrame
        as the 'tree_weight' property.

        Args:
            properties: A Python set of property names (TTree branch names) to
                load.  'tree_weight' may be included, just for convenience, it
                will not be treated as a branch name.

        Returns:
            A Pandas DataFrame containing the specified properties for the
            process.
        """
        # Compute the properties we need to load
        all_properties = set.union(properties,
                                   *(p.properties() for p in self._patches))

        # Remove tree weight branch if present, it will be added implicitly
        if 'tree_weight' in all_properties:
            all_properties.remove('tree_weight')

        # Load the data
        result = DataFrame(root2array(
            filenames = self._files,
            treename = self._tree,
            branches = list(all_properties),
            include_weight = True,
            weight_name = 'tree_weight'
        ))

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

    def style(self, histogram):
        """Applies the process' style to a histogram.

        Args:
            histogram: The histogram to style
        """
        # Set title
        histogram.SetTitle(self._label)

        # Set line color
        histogram.SetLineColor(self._line_color)

        # Set fill style and color
        histogram.SetFillStyle(1001)
        histogram.SetFillColor(self._fill_color)

        # Set marker style
        if self._marker_style is not None:
            histogram.SetMarkerStyle(self._marker_style)
            histogram.SetMarkerSize(1)
            histogram.SetMarkerColor(histogram.GetLineColor())
        else:
            # HACK: Set marker style to an invalid value if not specified,
            # because we need some way to differentiate rendering in the legend
            histogram.SetMarkerStyle(0)

        # Make lines visible
        histogram.SetLineWidth(2)
