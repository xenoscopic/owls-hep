# System imports
import unittest

# owls-hep imports
from owls_hep.expression import normalized, properties, negated, \
    variable_negated, added, subtracted, multiplied, divided, floor_divided, \
    anded, ored, xored


class TestProperties(unittest.TestCase):
    def test_properties(self):
        # Check a simple expression with duplicates
        self.assertEqual(properties('electron_pt > (x * x)'),
                         set(['electron_pt', 'x']))


class TestNormalize(unittest.TestCase):
    def test_normalize(self):
        # Check that normalization works
        self.assertEqual(normalized('!x && y || z'),
                         '~x & y | z')


class TestNegation(unittest.TestCase):
    def test_negation(self):
        # Test negating a whole expression
        self.assertEqual(negated('x + y > 7'), '!(x + y > 7)')

    def test_variable_negation(self):
        # Test negating a simple expression
        self.assertEqual(
            variable_negated('particle_is_e && particle_is_el',
                             'particle_is_e'),
            '!(particle_is_e) && particle_is_el'
        )


class TestComposition(unittest.TestCase):
    def setUp(self):
        # Set up expressions
        self.expression_1 = 'x + y > 8'
        self.expression_2 = '3 < (z - y)**2'

    def test_added(self):
        self.assertEqual(added(self.expression_1, self.expression_2),
                         '((x + y > 8) + (3 < (z - y)**2))')

    def test_subtracted(self):
        self.assertEqual(subtracted(self.expression_1, self.expression_2),
                         '((x + y > 8) - (3 < (z - y)**2))')

    def test_multiplied(self):
        self.assertEqual(multiplied(self.expression_1, self.expression_2),
                         '((x + y > 8) * (3 < (z - y)**2))')

    def test_divided(self):
        self.assertEqual(divided(self.expression_1, self.expression_2),
                         '((x + y > 8) / (3 < (z - y)**2))')

    def test_floor_divided(self):
        self.assertEqual(floor_divided(self.expression_1, self.expression_2),
                         '((x + y > 8) // (3 < (z - y)**2))')

    def test_anded(self):
        self.assertEqual(anded(self.expression_1, self.expression_2),
                         '((x + y > 8) && (3 < (z - y)**2))')

    def test_ored(self):
        self.assertEqual(ored(self.expression_1, self.expression_2),
                         '((x + y > 8) || (3 < (z - y)**2))')

    def test_xored(self):
        self.assertEqual(xored(self.expression_1, self.expression_2),
                         '((x + y > 8) ^ (3 < (z - y)**2))')


# Run the tests if this is the main module
if __name__ == '__main__':
    unittest.main()
