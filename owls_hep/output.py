"""Some simple output routines.
"""


# Future imports to support fancy print() on Python 2.x
from __future__ import print_function

# System imports
import os
import sys
from contextlib import contextmanager


def print_info(message):
    print(message)


def print_warning(message):
    print('warning: {}'.format(message), file = sys.stderr)


def print_error(message):
    print('error: {}'.format(message), file = sys.stderr)


def print_fatal(message):
    print('fatal: {}'.format(message), file = sys.stderr)
    sys.exit(1)


@contextmanager
def output_redirected(to = os.devnull):
    """Can be used to wrap code in a 'with' statement to redirect stdout/stderr
    to a file.

    This works differently than simply setting sys.stdout/stderr, because it
    uses dup2 to set the underlying libc file descriptors, forcing the
    redirection of any Python C modules as well.

    Usage is:

        with output_redirected(to = filename):
            ...your code here...

    Args:
        to: The filename to which output should be redirected
    """
    # Grab the current stdout/stderr file descriptors
    stdout_fd = sys.stdout.fileno()
    stderr_fd = sys.stderr.fileno()

    # Create a function to redirect the low-level file descriptors
    def _redirect_output(stdout_file, stderr_file):
        # Close the Python output files
        sys.stdout.close()
        sys.stderr.close()

        # Duplicate the new output files into the file descriptors
        os.dup2(stdout_file.fileno(), stdout_fd)
        os.dup2(stderr_file.fileno(), stderr_fd)

        # Create file versions of these file descriptors
        sys.stdout = os.fdopen(stdout_fd, 'w')
        sys.stderr = os.fdopen(stderr_fd, 'w')

    # Do the redirection
    with os.fdopen(os.dup(stdout_fd), 'w') as old_stdout, \
         os.fdopen(os.dup(stderr_fd), 'w') as old_stderr:
        with open(to, 'w') as to_file:
            _redirect_output(to_file, to_file)
        try:
            # Allow code inside the with block to run
            yield
        finally:
            _redirect_output(old_stdout, old_stderr)
