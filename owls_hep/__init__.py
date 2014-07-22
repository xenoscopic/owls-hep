"""Provides abstractions useful for High Energy Physics.
"""


# System imports
import warnings

# Six imports
from six import string_types

# Pandas imports
from pandas import DataFrame

# root_numpy imports
from root_numpy import root2array, RootNumpyUnconvertibleWarning

# owls-data imports
from owls_data.loading.backends import DataLoadingBackend, register_backend


# Export the owls-hep version
__version__ = '0.0.1'


# Ignore root_numpy unconvertible warnings
warnings.simplefilter('ignore', RootNumpyUnconvertibleWarning)


class RootNumpyDataLoadingBackend(DataLoadingBackend):
    """Data loading backend which reads from ROOT files via root_numpy.
    """

    def can_handle_urls(self, url_or_urls):
        """Determines whether or not this backend supports loading from the
        specified URL.

        Args:
            url_or_urls: The URL to test, or a list of URLs to test

        Returns:
            True if this backend can load the URL, False otherwise.
        """
        # Convert to a list if we have a single URL
        if isinstance(url_or_urls, string_types):
            url_or_urls = [url_or_urls]

        # Make sure we can handle all of the URLs
        return all([url.endswith('root') for url in url_or_urls])

    def load(self, url_or_urls, properties, options):
        """Loads the data from the URL.

        Args:
            url_or_urls: The URL to load, or a list of URLs to load
            properties: A Python set of properties of the data to load
            options: The RootNumpyDataLoadingBackend accepts to options:

                tree: The name of the tree to load (defaults to 'tree')
                tree_weight_property: The virtual property into which the tree
                    weight should be loaded, or None to ignore tree weights
                    (defaults to None)

        Returns:
            A Pandas DataFrame object with the specified data.
        """
        # Compute the name of the tree to load
        tree = options.get('tree', 'tree')

        # Compute the name of the property into which the tree weight should be
        # loaded
        tree_weight_property = options.get('tree_weight_property', None)

        # Load the data
        return DataFrame(root2array(
            filenames = url_or_urls,
            treename = tree,
            branches = list(properties),
            include_weight = tree_weight_property is not None,
            weight_name = tree_weight_property
        ))


# Register the root_numpy data loading backend
register_backend(RootNumpyDataLoadingBackend())
