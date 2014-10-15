"""Provides abstractions useful for High Energy Physics.
"""


# ROOT imports
import ROOT


# Export the owls-hep version
__version__ = '0.0.1'


# Set ROOT to batch mode
ROOT.gROOT.SetBatch(True)


# HACK: Stop ROOT from trying to hijack argparse.  Seems like this is only an
# issue if you do 'import ROOT' directly.  I weep for future generations.
# http://root.cern.ch/phpBB3/viewtopic.php?f=14&t=15601
ROOT.PyConfig.IgnoreCommandLineOptions = True


# Ignore ROOT info messages and warnings (there are just too many)
ROOT.gErrorIgnoreLevel = ROOT.kSysError
