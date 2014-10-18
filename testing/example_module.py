"""Example module for unit tests.
"""


# System imports
from sys import version_info

# owls-hep imports
from owls_hep.module import definitions


# Create some test exports
python_version = (version_info[0], version_info[1], version_info[2])
test_data = {
    1: 'George Washington',
    2: 'John Adams'
}


# Do something fancy with templated variables
test_name = 'John {0}'.format(definitions()['surname'])
