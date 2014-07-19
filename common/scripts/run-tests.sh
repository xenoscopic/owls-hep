#!/bin/sh

# Compute the path to the scripts directory
SCRIPTS_PATH=$(dirname "$0")

# Move to the source directory
cd "$SCRIPTS_PATH/../.."

# Run unit tests, excluding any OWLS modules
nosetests --exclude=owls_*
