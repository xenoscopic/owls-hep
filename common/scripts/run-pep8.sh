#!/bin/sh

# Compute the path to the scripts directory
SCRIPTS_PATH=$(dirname "$0")

# Move to the source directory
cd "$SCRIPTS_PATH/../.."

# Run PEP8 compliance checking on the source
# We ignore the following PEP8 errors:
# E251: Requires no space between argument, equal sign, and default value
# E261: Requires two spaces before inline comment
pep8 --ignore "E251,E261" owls_* testing
