# owls-hep

[![Build Status](https://travis-ci.org/havoc-io/owls-hep.png?branch=master)](https://travis-ci.org/havoc-io/owls-hep)

This is the high energy physics module for the OWLS analysis framework.  This
module implements many of the features of the ROOT analysis framework using the
[Pandas](http://pandas.pydata.org/) data analysis library.  Instead of using
ROOT `TTree` objects, this library relies on the Pandas `DataFrame` structure
and uses the Numexpr JIT `eval()` functionality in Pandas to efficiently
evaluate kinematic and selection expressions.  See the "Usage" section below for
more information.


## Requirements

The OWLS analysis framework supports Python 2.7, 3.3, 3.4, and 3.5.


## Installation

Installation is most easily performed via pip:

    pip install git+https://github.com/havoc-io/owls-hep.git

Alternatively, you may execute `setup.py` manually, but this is not supported.


## Usage

Although this module exposes functionality for low-level expression manipulation
and evaluation, it is more useful for its high-level `Process` and `Region`
manipulation facilties, which expose object-oriented interfaces to automatically
load data and manipulate expressions efficiently.

The `Process` class represents a physical process considered in an analysis.  It
contains a list of ROOT data files containing the simulated or recorded events
for a process as well as metadata describing how to display the process in lists
or plots.

The `Region` class represents a potentially weighted event selection of event.
Processes can be "projected" into regions, and these projections can be used to
compute counts or histograms.  Regions also contain metadata describing their
display parameters.

Finally, the `Calculation` class represents a calculation to be made using a
process/region pair.  This could be something like a count or a histogram, and
indeed implementations of both of these are provided by the library using the
owls-cache/owls-parallel modules for efficiency.

The `Calculation` class is also subclassed by the `HigherOrderCalculation`
class.  `HigherOrderCalculation` implementations are designed to wrap
`Calculation` classes and perform derivative calculations.  They can be used for
things such as background estimation (using a multi-region extrapolation) or
uncertainty estimation (using varied systematics).  Because fundamental
calculations such as counting and histogramming use the owls-cache and
owls-parallel module to batch and parallelize their operations, higher order
calculations can freely compute thousands and thousands of counts or histograms
or any other calculation without worrying about code structure/organization
while still reaping the benefits of caching, batching, and efficient data
loading.

The `Estimation` class is provided as a base for background estimation
calculations, and provides useful, type-agnostic algebraic facilities for counts
and histograms.  The `Uncertainty` class provides a base for uncertainty
estimations, and facilities for plotting those uncertainties.

Facilities for N-dimensional plotting are also provided by the `Plot` class, but
sadly this is really just a wrapper around ROOT's plotting.  Ideally we'd switch
to something like matplotlib, but unfortunately ROOT is the only plotting engine
that provides some of the more obscure features needed for High Energy Physics
plots.

For more information on all of these classes and the various utility functions
that accompany them, see the meticulously crafted Python docstrings.  If you
have access to the owls-hsg4 analysis code, you can see the full OWLS framework
in action.
