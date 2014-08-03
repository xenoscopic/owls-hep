"""Provides facilities to load event estimation techniques.
"""


# owls-hep imports
from owls_hep.config import load as load_config


def load(estimations_path):
    # Load the configuration
    configuration = load_config(estimations_path)

    # Create the function to load individual estimations
    def estimation_loader(name):
        # Grab the full (module-qualified) function name for this estimation
        # technique
        full_method_name = configuration[name]

        # Parse the name into module/function name
        method_module_name, method_name = full_method_name.rsplit('.', 1)

        # Load the module
        method_module = __import__(method_module_name,
                                   fromlist = [method_name])

        # Extract the method
        return getattr(method_module, method_name)

    # Return the loader
    return estimation_loader
