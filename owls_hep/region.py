"""Provides models for regions and region variations.
"""


# System imports
import re
from copy import deepcopy

# owls-data imports
from owls_hep.expression import multiplied


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
        # Grab the variation type
        variation_type = type(self)

        # Extract hashable components
        module = variation_type.__module__
        name = variation_type.__name__
        state = self.state()

        # Create a unique hash
        return hash((module, name, state))

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
    """A reusable region variation which multiplies an expression into the
    region weight.
    """

    def __init__(self, weight):
        """Initializes a new instance of the Reweighted class.

        Args:
            weight: The weight expression to incorporate into the region
        """
        # Store the weight
        self._weight = weight

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

    def __init__(self, name, selection, weight, label, blinded = False):
        """Initialized a new instance of the Region class.

        Args:
            name: A name by which to refer to the region
            selection: A string representing selection for the region
            weight: A string representing the weight for the region
            label: The ROOT TLatex label string to use when rendering the
                region
            blinded: Whether or not the region is marked as blinded
        """
        # Store parameters
        self._name = name
        self._selection = selection
        self._weight = weight
        self._label = label
        self._blinded = blinded

        # Create initial variations container
        self._variations = ()

    def __hash__(self):
        """Returns a hash for the region.
        """
        # Hash only weight, selection, and variations since those are all that
        # really matter for evaluation
        return hash((self._selection, self._weight, self._variations))

    def name(self):
        """Returns the region name.
        """
        return self._name

    def blinded(self):
        """Returns whether or not the region is blinded.
        """
        return self._blinded

    def varied(self, variation):
        """Creates a copy of the region with the specified variation applied.

        Args:
            variation: The variation to apply

        Returns:
            A duplicate region, but with the specified variation applied.
        """
        # Create the copy
        result = deepcopy(self)

        # Add the variation
        result._variations += (variation,)

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

        # Compute the combined expression
        return (selection, weight)
