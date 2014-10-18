# System imports
import unittest
from os.path import dirname, join
from sys import version_info

# owls-hep imports
from owls_hep.module import load


class TestModule(unittest.TestCase):
    def test(self):
        # Load the module
        module = load(join(dirname(__file__), 'example_module.py'),
                      {'surname': 'Adams'})

        # Check exported information
        self.assertEqual(module.python_version,
                         (version_info[0], version_info[1], version_info[2]))
        self.assertEqual(module.test_data, {
            1: 'George Washington',
            2: 'John Adams'
        })
        self.assertEqual(module.test_name, 'John Adams')
        self.assertTrue(hasattr(module, 'version_info'))
        self.assertFalse(hasattr(module, 'does_not_exist'))

        # Reload the module with a different configuration
        module = load(join(dirname(__file__), 'example_module.py'),
                      {'surname': 'Kennedy'})
        self.assertEqual(module.test_name, 'John Kennedy')


# Run the tests if this is the main module
if __name__ == '__main__':
    unittest.main()
