"""Provides models for regions and region variations.
"""


# System imports
from inspect import getsource
import re
from copy import copy

# owls-data imports
from owls_hep.expression import normalized, multiplied


# Set up default exports
__all__ = [
    'Variation',
    'Reweighted',
    'Region'
]


class Variation(object):
    """Represents a variation which can be applied to a region.
    """

    def __hash__(self):
        """Returns a unique hash for the patch.

        This method should not be overridden.
        """
        # HACK: Use the implementation of the variation in the hash, because
        # the behavior of the variation is what should determine hash equality,
        # and it's impossible to determine solely on type if the implementation
        # changes.
        return hash((self.state(), getsource(self.__call__)))

    def state(self):
        """Returns a representation of the variation's internal state, if any.

        This method is used to generate a unique hash for the variation for the
        purposes of caching.  If a variation has no internal state, and it's
        behavior is determined entirely by its type, then the implementer need
        not override this method.  However, if a variation contains state which
        affects its patching behavior, this method needs to be overridden.  A
        simple tuple may be returned containing the state of the variation.

        Returns:
            A hashable object representing the internal state of the variation.
        """
        return ()

    def __call__(self, selection, weight):
        """Applies a variation to a region's weight and selection.

        Implementers must override this method.

        Args:
            selection: The existing selection expression
            weight: The existing weight expression

        Returns:
            A tuple of the form (varied_selection, varied_weight).
        """
        raise NotImplementedError('abstract method')


class Reweighted(Variation):
    """A reusable region variation that multiplies an expression into the
    region weight.
    """

    def __init__(self, weight):
        """Initializes a new instance of the Reweighted class.

        Args:
            weight: The weight expression to incorporate into the region
        """
        # Store the weight
        self._weight = normalized(weight)

    def state(self):
        """Returns a representation of the variation's internal state.
        """
        return (self._weight,)

    def __call__(self, selection, weight):
        """Add's an expression to a region's weight.

        Args:
            selection: The existing selection expression
            weight: The existing weight expression

        Returns:
            A tuple of the form (varied_selection, varied_weight).
        """
        return (selection, multiplied(weight, self._weight))


class Region(object):
    """Represents a region (a selection and weight) in which processes can be
    evaluated.
    """

    def __init__(self,
                 selection,
                 weight,
                 label,
                 metadata = {},
                 weighted = True):
        """Initialized a new instance of the Region class.

        Args:
            selection: A string representing selection for the region, or an
                empty string for no selection
            weight: A string representing the weight for the region, or an
                empty string for no weighting
            label: The ROOT TLatex label string to use when rendering the
                region
            metadata: A (pickleable) object containing optional metadata
            weighted: If False, the `selection_weight` method will return an
                empty string for weight - can be varied later using the
                `weighted` method
        """
        # Store parameters
        self._selection = selection
        self._weight = weight
        self._label = label
        self._metadata = metadata
        self._weighted = weighted

        # Create initial variations container
        self._variations = ()

    def __hash__(self):
        """Returns a hash for the region.
        """
        # Only hash those parameters which affect evaluation
        return hash((
            self._selection,
            self._weight,
            self._weighted,
            self._variations
        ))

    def label(self):
        """Returns the label for the region, if any.
        """
        return self._label

    def metadata(self):
        """Returns metadata for this region, if any.
        """
        return self._metadata

    def varied(self, variation):
        """Creates a copy of the region with the specified variation applied.

        Args:
            variation: The variation to apply

        Returns:
            A duplicate region, but with the specified variation applied.
        """
        # Create the copy
        result = copy(self)

        # Add the variation
        result._variations += (variation,)

        # All done
        return result

    def weighted(self, weighting_enabled):
        """Creates a copy of the region with weighting turned on or off.

        If there is no change to the weighting, self will be returned.

        Args:
            weighting_enabled: Whether or not to enable weighting

        Returns:
            A duplicate region, but with weighting set to weighting_enabled.
        """
        # If there's no change, return self
        if weighting_enabled == self._weighted:
            return self

        # Create a copy
        result = copy(self)

        # Change weighting status
        result._weighted = weighting_enabled

        # All done
        return result

    def selection_weight(self):
        """Returns a tuple of (selection, weight) with all variations applied.
        """
        # Grab resultant weight/selection
        selection, weight = self._selection, self._weight

        # Apply any variations
        for v in self._variations:
            selection, weight = v(selection, weight)

        # If this region isn't weighted, return an empty weight
        if not self._weighted:
            return (selection, '')

        # All done
        return (selection, weight)
