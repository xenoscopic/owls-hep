# System imports
import unittest
from os.path import join, dirname

# owls-hep imports
from owls_hep.config import load


# Compute the path to the test configuration file
config_path = join(dirname(__file__), 'config.yml')


class TestLoading(unittest.TestCase):
    def test(self):
        # Load data
        config = load(config_path)

        # Make sure it is correct
        self.assertEqual(len(config), 2)
        self.assertEqual(config['George'], 'Washington')
        self.assertEqual(config['John'], 'Kennedy')


# Run the tests if this is the main module
if __name__ == '__main__':
    unittest.main()
