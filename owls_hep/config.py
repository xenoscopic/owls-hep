"""Provides a configuration loader which allows user-specific overrides to
facilitate shared configuration amongst multiple analysts.
"""


# System imports
from os.path import splitext

# owls-config imports
from owls_config import load as load_config


def load(path):
    """Provides an identical interface to the owls_config.load method, except
    that if file with the same path but extension `.local.yml` instead of
    `.yml` exists, it will be loaded after the `.yml` file, and its contents
    will overwrite those of the `.yml` file in the returned configuration.  If
    the `.yml` file does not exist, but the `.local.yml` does, then this method
    returns None.

    Overrides take place only at the top level of the configuration.

    Args:
        path: A path to a JSON file containing configuration information

    Returns:
        A Python OrderedDict representing the contents of the configuration.
        Returns None if the configuration path does not exist or is not a file.
    """
    # Load the initial configuration
    result = load_config(path)

    # If it was empty or non-existant, just bail
    if result is None:
        return

    # Now try to load the local override
    local = load_config('{0}.local.yml'.format(splitext(path)[0]))
    
    # Merge configuration, if any
    if local is not None:
        result.update(local)

    # All done
    return result
