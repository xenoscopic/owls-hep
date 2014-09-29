# System imports
from sys import version_info, exit


def owls_python_version_check():
    """Checks that the current version of Python is supported by OWLS packages,
    exiting if not.
    """
    # Get the Python version, up to the minor revision
    python_version = version_info[0:2]

    # Don't let OWLS modules install an unsupported python version
    supported_python_versions = (
        (2, 7),
        (3, 3),
        (3, 4),
    )
    if python_version not in supported_python_versions:
        exit('unsupported Python version')
