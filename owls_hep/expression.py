"""Provides inspection, manipulation, and composition methods for string-based
expressions.
"""


# System imports
import re


# _property_regex is used to find properties in expression strings
_property_regex = re.compile('[A-Za-z_]\w*(?!\w*\s*\()')


def normalized(expression):
    """Converts the expression to the syntax necessary for Pandas'
    DataFrame.eval method.

    Args:
        expression: The expression to normalize

    Returns:
        A normalized version of the expression usable in Pandas' DataFrame.eval
        method.
    """
    return expression.replace('!', '~').replace('&&', '&').replace('||', '|')


def properties(expression):
    """Creates a list of properties needed to evaluate the expression.

    Args:
        expression: The expression string

    Returns:
        A set of properties necessary to evaluate the expression.
    """
    # Generate a set of matches from the property regex
    return set((m.group(0) for m in _property_regex.finditer(expression)))


def negated(expression):
    """Returns a negated version of the expression.

    Args:
        expression: The expression to negate

    Returns:
        A negated version of the expression.
    """
    return '!({0})'.format(expression)


def variable_negated(expression, variable):
    """Negates all instances of the specified variable within the expression.

    Args:
        expression: The expression string
        variable: The variable name

    Returns:
        A version of the expression with instances of the specified variable
        negated.
    """
    # Define a simple function to do our negation
    def negator(match):
        # Grab the match group
        match_group = match.group(0)

        # Negate accordingly
        if match_group == variable:
            return '!({0})'.format(match_group)
        return match_group

    # Return an expression with all instances of this particular variable
    # negated
    return _property_regex.sub(negator, expression)


def _combined(expression_1, expression_2, operator):
    """Private method to handle binary expression composition

    Args:
        expression_1: The first expression string
        expression_2: The second expression string
        operator: The operator string with which to combine the expressions

    Returns:
        The combined binary expression string.
    """
    return '(({0}) {1} ({2}))'.format(expression_1, operator, expression_2)


def added(expression_1, expression_2):
    """Returns the added expression combing two expressions.

    Args:
        expression_1: The first expression string
        expression_2: The second expression string

    Returns:
        The combined expression string.
    """
    return _combined(expression_1, expression_2, '+')


def subtracted(expression_1, expression_2):
    """Returns the expression subtracting expression_2 from expression_1.

    Args:
        expression_1: The first expression string
        expression_2: The second expression string

    Returns:
        The combined expression string.
    """
    return _combined(expression_1, expression_2, '-')


def multiplied(expression_1, expression_2):
    """Returns the multipled expression combing two expressions.

    Args:
        expression_1: The first expression string
        expression_2: The second expression string

    Returns:
        The combined expression string.
    """
    return _combined(expression_1, expression_2, '*')


def divided(expression_1, expression_2):
    """Returns the expression dividing expression_1 by expression_2 using the
    '/' division operator.

    Args:
        expression_1: The first expression string
        expression_2: The second expression string

    Returns:
        The combined expression string.
    """
    return _combined(expression_1, expression_2, '/')


def floor_divided(expression_1, expression_2):
    """Returns the expression dividing expression_1 by expression_2 using the
    '//' floor division operator.

    Args:
        expression_1: The first expression string
        expression_2: The second expression string

    Returns:
        The combined expression string.
    """
    return _combined(expression_1, expression_2, '//')


def anded(expression_1, expression_2):
    """Returns the 'and' expression combing two expressions.

    Args:
        expression_1: The first expression string
        expression_2: The second expression string

    Returns:
        The combined expression string.
    """
    return _combined(expression_1, expression_2, '&&')


def ored(expression_1, expression_2):
    """Returns the 'or' expression combing two expressions.

    Args:
        expression_1: The first expression string
        expression_2: The second expression string

    Returns:
        The combined expression string.
    """
    return _combined(expression_1, expression_2, '||')


def xored(expression_1, expression_2):
    """Returns the 'xor' expression combing two expressions.

    Args:
        expression_1: The first expression string
        expression_2: The second expression string

    Returns:
        The combined expression string.
    """
    return _combined(expression_1, expression_2, '^')
