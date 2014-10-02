"""Provides minor abstractions on top of ROOT to faciliate somewhat more
elegant plotting.  As with anything that interfaces with ROOT, there are bound
to be... idiosyncrasies, though this module does its best to hide them.  It
provides several functions for manipulating histograms or collections thereof:

    - histogram_iterable
    - combined_histogram
    - maximum_value
    - ratio_histogram
    - histogram_stack

It also provides a class, 'Plot', which can be used to model a ROOT plot,
enabling the following features:

    - Stacked background histograms
    - Data histograms
    - Legend
    - Ratio histograms
    - Statistical error bars
    - Systematic error bars

For more documentation, please see the docstrings for the individual functions
and/or Plot methods.
"""


# System imports
from math import ceil, sqrt
from uuid import uuid4
from itertools import chain

# ROOT imports
# HACK: We import and use SetOwnership because ROOT's memory management is so
# inconsistent and terrible that we have to stop Python from even touching ROOT
# graphical objects or ROOT will crash, often due to a double free or some
# other nonsense.
from ROOT import TCanvas, TPad, TH1, THStack, TLegend, TLine, TLatex, \
    SetOwnership


# Convenience function for generating random IDs
_rand_uuid = lambda: uuid4().hex


# Convenience function to check if an object is a THStack
is_stack = lambda h: isinstance(h, THStack)


def histogram_iterable(histograms_or_stack,
                       unpack_stacks = False,
                       reverse_stacks = False):
    """Convenience method to get an iterable object from a collection of
    histogram (TH1) objects.

    Args:
        histograms_or_stack: A single histogram, an iterable of histograms, or
            a THStack object which represents the collection of histograms
        unpack_stacks: By default, THStack objects are treated as a single
            histogram.  If you would like them to be treated as a collection of
            their constituent TH1 objects, set unpack_stacks = True.
        reverse_stacks: If unpacking stacks, they are typically iterated from
            bottom to top.  Specify True for reverse_stacks to iterate from top
            to bottom.

    Returns:
        An iterable of the histograms in the provided collection.
    """
    # Check if we are using a THStack
    if is_stack(histograms_or_stack):
        if unpack_stacks:
            # Extract histograms from the stack
            result = list(histograms_or_stack.GetHists())

            # Reverse if necessary
            if reverse_stacks:
                result.reverse()

            return result
        else:
            return (histograms_or_stack,)
    elif isinstance(histograms_or_stack, TH1):
        # Create an iterable of the single histogram
        return (histograms_or_stack,)

    # Must already be an iterable
    return histograms_or_stack


def combined_histogram(histograms_or_stack):
    """Returns a combined TH1 object from a collection of histograms with bin
    errors calculated.

    Args:
        histograms_or_stack: A single histogram, a non-empty iterable of
            histograms, or a THStack object which represents the collection of
            histograms

    Returns:
        A single TH1 object which is a combination of the provided histograms
        and which has bin errors calculated.
    """
    # Convert the histograms to an iterable, always unpacking THStack objects
    histograms = histogram_iterable(histograms_or_stack, True)

    # Grab the first histogram, making sure bin errors are calculated before
    # adding the remaining histograms
    result = histograms[0].Clone(_rand_uuid())
    SetOwnership(result, False)
    if result.GetSumw2N() == 0:
        result.Sumw2()

    # Add the other histograms to the result
    map(result.Add, histograms[1:])

    return result


def maximum_value(histograms):
    """Returns the maximum value of all bins of all histograms provided,
    including any errors.

    Args:
        histograms: A list of histogrammy objects, each of which may be a
            single histogram, a THStack object, or a 2-tuple of the form
            (TH1/THStack, TGraphAsymmErrors), where the second element is an
            error band for the histogram.

    Returns:
        The maximum value than any bin takes on in any of the provided
        histograms.
    """
    # Create our initial maximum
    result = 0.0

    # Loop over histograms
    for histogram in histograms:
        # Unpack things if there is an error band
        if isinstance(histogram, tuple):
            histogram, error_band = histogram
        else:
            error_band = None

        # Compute the maximum for this histogram
        maximum = histogram.GetMaximum()

        # NOTE: Clever math hack.  Since histogram may be a THStack, we can't
        # (easily) do a bin-wise pairing and compute (value + error-high) for
        # each bin when looking for a maximum.  However, the bin which has the
        # maximum value will also have the maximum statistical and systematic
        # normalization uncertainty, so we can assume that the value returned
        # by GetMaximum() corresponds to the bin with the greatest error, and
        # thus we can just scan for the largest error and adding that to the
        # GetMaximum() result gives the answer we would get from bin-wise
        # pairing.  Of course, even if we didn't get the exact answer here,
        # we'd still be at-or-above the true maximum value, which is all we
        # really care about for plotting purposes.
        # If there is no error band, we just add enough room for statistical
        # error.
        if error_band is not None:
            maximum_error = 0.0
            for i in xrange(error_band.GetN()):
                maximum_error = max(maximum_error, error_band.GetErrorYhigh(i))
            maximum += maximum_error
        else:
            maximum += sqrt(maximum)

        # Update the result
        result = max(result, maximum)

    return result


def ratio_histogram(numerator, denominator, y_title = 'Data / MC'):
    """Creates a ratio histogram by dividing a numerator histogram by a
    denominator histogram, properly calculating errors.  This method also
    provides some basic styling of the ratio histogram, disabling statistics
    and title, and setting markers appropriately.

    Args:
        numerator: A single histogram, an iterable of histograms, or a THStack
            object which represents the data to use in the numerator of the
            ratio division
        denominator: A single histogram, an iterable of histograms, or a
            THStack object which represents the data to use in the numerator of
            the ratio division.  This must have the same binning as numerator.
        y_title: The title for the y-axis

    Returns:
        A ROOT histogram representing the ratio of numerator/denominator.
    """
    # Create our result based off of the numerator (it will have bin errors
    # enabled)
    result = combined_histogram(numerator)

    # Divide by the denominator
    result.Divide(combined_histogram(denominator))

    # Do some styling on the result
    result.SetTitle('')
    result.SetStats(0)
    result.SetMarkerStyle(21)

    # Set title
    result.GetYaxis().SetTitle(y_title)

    return result


def histogram_stack(*histograms):
    """Creates a THStack object with a unique identifier from the specified
    histograms.

    This method is useful due to THStack freaking out if a new THStack is
    created with the same name.

    Args:
        histograms: Each argument of this function after plot may be a single
            histogram, an iterable of histograms (each of which should be
            plotted), or even an existing THStack object whose component
            histograms should be included in the new stack.  The histograms
            should be specified from top-to-bottom.

    Returns:
        An initialized THStack object containing the specified histograms.
    """
    # Generate an iterable of all histograms provided
    histograms = chain(*(histogram_iterable(h, unpack_stacks = True)
                         for h
                         in histograms))

    # Create a new THStack object with a unique identifier
    stack = THStack(_rand_uuid(), '')
    SetOwnership(stack, False)

    # Add histograms
    map(stack.Add, histograms)

    return stack


class Plot(object):
    """Structural class for representing, accessing, and maintaining references
    to ROOT graphical elements forming a plot, potentially with a ratio
    subplot.
    """

    # Plotting 'constants' for the plot class.  Ideally, one would allow these
    # to be flexible, but unfortunately ROOT's coordinate system is extremely
    # inconsistent and fragile, so it is best to fix these values here.  You
    # can change them dynamically with Plot.Whatever = value, but it is
    # probably best to leave them alone.
    PLOT_WIDTH = 1280 # px
    PLOT_HEIGHT = 1024 # px
    PLOT_MARGINS = (0.125, 0.05, 0.1, 0.1) # Left, Right, Bottom, Top
    PLOT_MARGINS_WITH_RATIO = (0.125, 0.05, 0.025, 0.1)
    PLOT_RATIO_MARGINS = (0.125, 0.05, 0.325, 0.05)
    PLOT_LEFT_MARGIN = 0.1
    PLOT_HEADER_HEIGHT = 400 # px
    PLOT_LEGEND_HEIGHT = 250 # px
    PLOT_LEGEND_LEFT = 0.45
    PLOT_LEGEND_RIGHT = 0.95
    PLOT_LEGEND_BOTTOM = 0.7
    PLOT_LEGEND_BOTTOM_WITH_RATIO = 0.63
    PLOT_LEGEND_TOP = 0.88
    PLOT_LEGEND_TOP_WITH_RATIO = 0.88
    PLOT_LEGEND_TEXT_SIZE = 0.03
    PLOT_LEGEND_TEXT_SIZE_WITH_RATIO = 0.045
    PLOT_LEGEND_N_COLUMNS = 2
    PLOT_RATIO_FRACTION = 0.3 # fraction of canvas height
    PLOT_X_AXIS_TITLE_SIZE = 0.045
    PLOT_X_AXIS_TITLE_SIZE_WITH_RATIO = 0.13
    PLOT_X_AXIS_TITLE_OFFSET = 0.95
    PLOT_X_AXIS_TITLE_OFFSET_WITH_RATIO = 0.96
    PLOT_X_AXIS_LABEL_SIZE_WITH_RATIO = 0.12
    PLOT_Y_AXIS_TITLE_SIZE = PLOT_X_AXIS_TITLE_SIZE
    PLOT_Y_AXIS_TITLE_SIZE_WITH_RATIO = 0.06
    PLOT_Y_AXIS_TITLE_OFFSET = 1.4
    PLOT_Y_AXIS_TITLE_OFSET_WITH_RATIO = 1.05
    PLOT_Y_AXIS_LABEL_SIZE_WITH_RATIO = 0.05
    PLOT_RATIO_Y_AXIS_TITLE_SIZE = 0.12
    PLOT_RATIO_Y_AXIS_LABEL_SIZE = 0.12
    PLOT_RATIO_Y_AXIS_MINIMUM = 0.6
    PLOT_RATIO_Y_AXIS_MAXIMUM = 1.4
    PLOT_ERROR_BAND_FILL_STYLE = 3254 # Diagonal lines
    PLOT_ERROR_BAND_FILL_COLOR = 13 # Gray
    PLOT_ERROR_BAND_LINE_WIDTH = 0
    PLOT_ERROR_BAND_LINE_COLOR = 0
    PLOT_RATIO_ERROR_BAND_FILL_STYLE = 3254 # Diagonal lines
    PLOT_RATIO_ERROR_BAND_FILL_COLOR = 807 # Orange
    PLOT_RATIO_ERROR_BAND_LINE_WIDTH = 0
    PLOT_RATIO_ERROR_BAND_LINE_COLOR = 0
    PLOT_ATLAS_STAMP_LUMINOSITY_SIZE = 0.035
    PLOT_ATLAS_STAMP_LUMINOSITY_SIZE_WITH_RATIO = 0.05
    PLOT_ATLAS_STAMP_TITLE_SIZE = 0.04
    PLOT_ATLAS_STAMP_TITLE_SIZE_WITH_RATIO = 0.055
    PLOT_ATLAS_STAMP_TEXT_COLOR = 1
    PLOT_ATLAS_STAMP_TEXT_FONT = 42
    PLOT_ATLAS_STAMP_ATLAS_TEXT_FONT = 72
    PLOT_ATLAS_STAMP_LEFT = 0.18
    PLOT_ATLAS_STAMP_LUMINOSITY_LEFT = 0.185
    PLOT_ATLAS_STAMP_LUMINOSITY_TOP = 0.78
    PLOT_ATLAS_STAMP_LUMINOSITY_TOP_WITH_RATIO = 0.75
    PLOT_ATLAS_STAMP_SQRT_S_TOP = 0.71
    PLOT_ATLAS_STAMP_SQRT_S_TOP_WITH_RATIO = 0.65
    PLOT_ATLAS_STAMP_LABEL_LEFT_ADDITION = 0.105
    PLOT_ATLAS_STAMP_LABEL_LEFT_ADDITION_WITH_RATIO = 0.102
    PLOT_ATLAS_STAMP_ATLAS_TOP = 0.84
    PLOT_ATLAS_STAMP_ATLAS_TOP_WITH_RATIO = 0.845

    def __init__(self,
                 title = '',
                 x_title = None,
                 y_title = None,
                 plot_header = True,
                 ratio = False,
                 maximum_value = None):
        """Initializes a new instance of the Plot class.

        Args:
            title: The title to set for the histogram
            plot_header: Whether or not to include whitespace at the top of the
                plot for the ATLAS label and legend
            ratio: Whether or not to include a ratio plot
            maximum_value: The maximum Y value for any histogram being plotted.
                If None (the default), this value will be determined by the
                first call to draw_histograms.
        """
        # Store the title
        self._title = title
        self._x_title, self._y_title = x_title, y_title

        # Store whether or not the user wants to create a plot header
        self._plot_header = plot_header

        # Calculate a unique name for the plot components
        name = _rand_uuid()

        # Create a canvas
        self._canvas = TCanvas(name + '_canvas',
                               name,
                               int(self.PLOT_WIDTH),
                               int(self.PLOT_HEIGHT))
        SetOwnership(self._canvas, False)

        # Create the main plot and draw it
        self._plot = TPad(
            name + '_plot',
            name,
            0.0,
            (self.PLOT_RATIO_FRACTION
             if ratio
             else 0.0),
            1.0,
            1.0
        )
        SetOwnership(self._plot, False)
        self._plot.SetMargin(*(self.PLOT_MARGINS_WITH_RATIO
                               if ratio
                               else self.PLOT_MARGINS))
        self._plot.Draw()

        # Store the maximum Y value
        self._set_maximum_value(maximum_value)

        # Switch back to the context of the canvas
        self._canvas.cd()

        # Create a ratio plot and draw it if requested
        if ratio:
            self._ratio_plot = TPad(
                name + '_ratio',
                name,
                0.0,
                0.0,
                1.0,
                self.PLOT_RATIO_FRACTION
            )
            SetOwnership(self._ratio_plot, False)
            self._ratio_plot.SetMargin(*self.PLOT_RATIO_MARGINS)
            self._ratio_plot.SetGridy(True)
            self._ratio_plot.Draw()
        else:
            self._ratio_plot = None

        # Set up axis tracking
        self._plot_axes = None
        self._ratio_plot_axes = None

        # Create a structure to track any histograms we generate internally
        # which need to be added to any legends created
        self._legend_extras = []

    def save(self, path):
        """Saves this plot to file.

        Args:
            path: The path where the plot should be saved.
        """
        # Force an update of the canvas
        self._canvas.Update()

        # Save to file
        self._canvas.SaveAs(path)

    def _get_maximum_value(self):
        """Returns the currently set maximum value (possibly None).
        """
        if hasattr(self, '_maximum_value'):
            return self._maximum_value
        return None

    def _set_maximum_value(self, value):
        """Sets the current maximum value, possibly including room for a plot
        header.

        Args:
            value: The value to set
        """
        # Check if the current value is not None, and if so, throw an error
        # because this property should not be set twice
        if self._get_maximum_value() is not None:
            raise RuntimeError('maximum value should not be set twice')

        # If the value is None, ignore it
        if value is None:
            return

        # If the user wants a plot header, then add space for one
        if self._plot_header:
            # Grab the plot pad height (in pixels)
            plot_height = (
                self.PLOT_HEIGHT * (self._plot.GetY2() - self._plot.GetY1())
            )

            # Adjust the height
            value *= (plot_height + self.PLOT_HEADER_HEIGHT) / plot_height

        # Set the value
        self._maximum_value = value

    def set_log_scale(self, log_scale = True):
        """Set log scale on the Y axis for this plot."""
        self._plot.SetLogy(int(log_scale))

    def draw_histograms(self, *histograms):
        """Plots a collection of histograms to the main plot pad of a plot
        created with plot or plot_with_ratio.  All TH1 objects are drawn with
        error bars.  THStack elements are only drawn with an error band if one
        is provided.

        Args:
            histograms: Each argument of this function after plot may be a
                single histogram, a THStack object, or a 2-tuple of the form
                (TH1/THStack, TGraphAsymmErrors), where the second element is
                an error band for the stack.  Elements are drawn in the order
                that they are provided, so THStack objects should be provided
                first.
        """
        # If there are no histograms, we can bail
        if not histograms:
            return

        # Check if there is a maximum value set, and if not, set it
        if self._get_maximum_value() is None:
            self._set_maximum_value(maximum_value(histograms))

        # Draw the histograms
        map(self._draw_histogram, histograms)

        # HACK: Need to force a redraw of plot axes due to issue with ROOT:
        # http://root.cern.ch/phpBB3/viewtopic.php?f=3&t=14034
        self._plot.RedrawAxis()

    def _draw_histogram(self, histogram):
        """Draws a single histogram to the plot pad.

        Args:
            histogram: The histogram to draw
        """
        # Check if this is the first histogram to be drawn
        first = self._plot_axes is None

        # Check if this histogram is a tuple of (histogram, error_band)
        if isinstance(histogram, tuple):
            histogram, error_band = histogram
        else:
            error_band = None

        # Move to the context of the plot pad
        self._plot.cd()

        # Make a clone of the histogram so we don't modify it
        histogram = histogram.Clone(_rand_uuid())
        SetOwnership(histogram, False)

        # If this is the first histogram, we need to set the title on it
        if first and self._title is not None:
            histogram.SetTitle(self._title)

        # Set the maximum value of the histogram
        histogram.SetMaximum(self._get_maximum_value())

        # Draw the histogram
        histogram.Draw(self._draw_options_for_histogram(histogram))

        # If this was the first histogram, we need to do some styling on the
        # axes and titles
        if first:
            self._set_and_style_plot_axes(histogram)

        # If there is an error band, draw it
        if error_band is not None:
            self._draw_error_band(error_band)

    def _draw_options_for_histogram(self, histogram):
        """Returns options for TH1::Draw or THStack::Draw based on type and
        whether or not axes exist.

        Args:
            histogram: The histogram object

        Returns:
            A string representing draw options.
        """
        # Calculate options
        options = 'hist' if is_stack(histogram) else 'ep'

        # Draw on the same axes if they already exist
        if self._plot_axes:
            options += 'same'

        return options

    def _set_and_style_plot_axes(self, histogram):
        """Sets self._plot_axes and makes sure they are style appropriately.

        Args:
            histogram: The histogram or stack whose axes were ALREADY drawn.
        """
        # Check if this is a stack
        stack = is_stack(histogram)

        # Figure out which histogram to grab axes/titles from
        # NOTE: For GetHistogram() to work, Draw must have been called on
        # the stack, so this has been noted in the function arguments
        axes_histogram = histogram.GetHistogram() if stack else histogram
        title_histogram = histogram.GetHists()[0] if stack else histogram

        # Grab axes
        self._plot_axes = \
            x_axis, y_axis = \
            axes_histogram.GetXaxis(), axes_histogram.GetYaxis()

        # Grab titles from first histogram if not set explicitly
        if self._x_title is None:
            self._x_title = title_histogram.GetXaxis().GetTitle()
        if self._y_title is None:
            self._y_title = title_histogram.GetYaxis().GetTitle()

        # Style x-axis, or hide it if this plot has a ratio plot
        if self._ratio_plot:
            x_axis.SetLabelOffset(999)
            x_axis.SetTitleOffset(999)
        else:
            x_axis.SetTitle(self._x_title)
            x_axis.SetTitleSize(self.PLOT_X_AXIS_TITLE_SIZE)
            x_axis.SetTitleOffset(self.PLOT_X_AXIS_TITLE_OFFSET)

        # Style y-axis
        n_bins = x_axis.GetNbins()
        low_edge = x_axis.GetBinLowEdge(1)
        up_edge = x_axis.GetBinUpEdge(n_bins)
        bin_width = (up_edge - low_edge) / float(n_bins)
        if bin_width == 1 and n_bins < 10:
            bin_label = '1'
        else:
            bin_label = '{0:.1f}'.format(bin_width)

        y_axis.SetTitle(self._y_title.format(bin_label))
        y_axis.SetTitleSize(
            (self.PLOT_Y_AXIS_TITLE_SIZE_WITH_RATIO
             if self._ratio_plot
             else self.PLOT_Y_AXIS_TITLE_SIZE)
        )
        y_axis.SetTitleOffset(
            (self.PLOT_Y_AXIS_TITLE_OFSET_WITH_RATIO
             if self._ratio_plot
             else self.PLOT_Y_AXIS_TITLE_OFFSET)
        )
        if self._ratio_plot:
            y_axis.SetLabelSize(self.PLOT_Y_AXIS_LABEL_SIZE_WITH_RATIO)

        # Redraw the histogram with the new style
        histogram.Draw(self._draw_options_for_histogram(histogram))

    def _draw_error_band(self, error_band):
        """Draws an error band on top of histogram objects.

        Args:
            error_band: The error band to draw (a TGraphAsymmErrors)
        """
        # Style it
        # HACK: Setting the marker style to 0 specifies this should be filled
        # in the legend
        error_band.SetMarkerStyle(0)
        error_band.SetMarkerSize(0)
        error_band.SetFillStyle(self.PLOT_ERROR_BAND_FILL_STYLE)
        error_band.SetFillColor(self.PLOT_ERROR_BAND_FILL_COLOR)
        error_band.SetLineWidth(self.PLOT_ERROR_BAND_LINE_WIDTH)
        error_band.SetLineColor(self.PLOT_ERROR_BAND_LINE_COLOR)

        # Draw it
        error_band.Draw('e2same')

        # Add it to the list of things we need to add to the legend
        self._legend_extras.append(error_band)

    def draw_ratio_histogram(self,
                             histogram,
                             draw_unity = True,
                             error_band = None):
        """Draws a ratio histogram to the ratio pad.

        Args:
            histogram: The ratio histogram to draw (use ratio_histogram)
            draw_unity: Whether or not to draw a line at 1
            error_band: An error band to draw under the ratio histogram
                (see SystematicCalculator.error_band_for_processes_in_region)

        The histogram X axis title is set by draw_histogram if not set
        explicitly. draw_ratio_histogram should therefore be called after
        draw_histogram.
        """
        # Switch to the context of the ratio pad
        self._ratio_plot.cd()

        # Clone the histogram
        histogram = histogram.Clone(_rand_uuid())
        SetOwnership(histogram, False)

        # Style it
        x_axis, y_axis = histogram.GetXaxis(), histogram.GetYaxis()
        x_axis.SetTitleSize(self.PLOT_X_AXIS_TITLE_SIZE_WITH_RATIO)
        x_axis.SetTitleOffset(self.PLOT_X_AXIS_TITLE_OFFSET_WITH_RATIO)
        x_axis.SetLabelSize(self.PLOT_X_AXIS_LABEL_SIZE_WITH_RATIO)
        # NOTE: _x_title is set by draw_histogram if it is not set
        # explicitly.
        x_axis.SetTitle(self._x_title)
        y_axis.SetTitleSize(self.PLOT_RATIO_Y_AXIS_TITLE_SIZE)
        y_axis.SetLabelSize(self.PLOT_RATIO_Y_AXIS_LABEL_SIZE)
        y_axis.SetRangeUser(self.PLOT_RATIO_Y_AXIS_MINIMUM,
                            self.PLOT_RATIO_Y_AXIS_MAXIMUM)
        y_axis.SetNdivisions(504, False)

        # Draw it
        histogram.Draw('ep')

        # Draw a line at unity if requested
        if draw_unity:
            # Calculate the line coordinates
            line_min = histogram.GetBinLowEdge(1)
            max_bin = histogram.GetNbinsX()
            line_max = (histogram.GetBinLowEdge(max_bin)
                        + histogram.GetBinWidth(max_bin))

            # Create and draw the line
            unit_line = TLine(line_min,
                              1.0,
                              line_max,
                              1.0)
            SetOwnership(unit_line, False)
            unit_line.SetLineColor(2) # Red
            unit_line.SetLineWidth(2)
            unit_line.Draw('same')

        # If an error band was provided, draw it and add it to our legend
        # elements
        if error_band:
            # Keep ownership of the error band
            SetOwnership(error_band, False)

            # Style it
            error_band.SetMarkerSize(0)
            error_band.SetFillStyle(self.PLOT_RATIO_ERROR_BAND_FILL_STYLE)
            error_band.SetFillColor(self.PLOT_RATIO_ERROR_BAND_FILL_COLOR)
            error_band.SetLineWidth(self.PLOT_RATIO_ERROR_BAND_LINE_WIDTH)
            error_band.SetLineColor(self.PLOT_RATIO_ERROR_BAND_LINE_COLOR)

            # Draw it
            error_band.Draw('e2same')

        # Now, if we've drawn unity or an error band, redraw our ratio
        # histogram so that its point lie on top of the unity line or error
        # band, but use 'same' so that the axes/ticks don't cover the red line
        if draw_unity or error_band:
            histogram.Draw('epsame')

    def draw_atlas_label(self,
                         luminosity,
                         sqrt_s,
                         ks_test = None,
                         custom_label = None,
                         atlas_label = None):
        """Draws an ATLAS stamp on the plot, with an optional categorization
        label.

        It is recommended that you construct the Plot with plot_header = True
        in order to make space for the label.

        Args:
            luminosity: The integrated luminosity, in pb^-1
            sqrt_s: The center of mass energy, in MeV
            label: The label to put after 'ATLAS', None to exclude the 'ATLAS'
                categorization entirely
        """
        # Change context to the plot pad
        self._plot.cd()

        # Create the latex object
        stamp = TLatex()

        # Style it
        stamp.SetTextColor(self.PLOT_ATLAS_STAMP_TEXT_COLOR)
        stamp.SetTextFont(self.PLOT_ATLAS_STAMP_TEXT_FONT)
        stamp.SetNDC()

        # Draw the luminosity
        stamp.SetTextSize((self.PLOT_ATLAS_STAMP_LUMINOSITY_SIZE_WITH_RATIO
                           if self._ratio_plot
                           else self.PLOT_ATLAS_STAMP_LUMINOSITY_SIZE))
        text = '#int L dt = {0:.1f} fb^{{-1}}'.format(luminosity / 1000.0)
        stamp.DrawLatex(
            self.PLOT_ATLAS_STAMP_LUMINOSITY_LEFT,
            (self.PLOT_ATLAS_STAMP_LUMINOSITY_TOP_WITH_RATIO
             if self._ratio_plot
             else self.PLOT_ATLAS_STAMP_LUMINOSITY_TOP),
            text
        )

        # Draw the center of mass energy and the result of the KS-test, if
        # requested
        text = '#sqrt{{s}} = {0:.1f} TeV'.format(sqrt_s / 1000000.0)
        if ks_test is not None:
            text += ', KS = {0:.2f}'.format(ks_test)
        stamp.DrawLatex(
            self.PLOT_ATLAS_STAMP_LEFT,
            (self.PLOT_ATLAS_STAMP_SQRT_S_TOP_WITH_RATIO
             if self._ratio_plot
             else self.PLOT_ATLAS_STAMP_SQRT_S_TOP),
            text
        )

        # If requested, draw the custom label or the 'ATLAS' label,
        # preferring the former
        if custom_label is not None:
            # Draw the label
            stamp.DrawLatex(
                self.PLOT_ATLAS_STAMP_LEFT,
                (self.PLOT_ATLAS_STAMP_ATLAS_TOP_WITH_RATIO
                 if self._ratio_plot
                 else self.PLOT_ATLAS_STAMP_ATLAS_TOP),
                custom_label
            )

        elif atlas_label is not None:
            # Draw the label
            stamp.SetTextSize((self.PLOT_ATLAS_STAMP_TITLE_SIZE_WITH_RATIO
                               if self._ratio_plot
                               else self.PLOT_ATLAS_STAMP_TITLE_SIZE))
            stamp.DrawLatex(
                self.PLOT_ATLAS_STAMP_LEFT + (
                    self.PLOT_ATLAS_STAMP_LABEL_LEFT_ADDITION_WITH_RATIO
                    if self._ratio_plot
                    else self.PLOT_ATLAS_STAMP_LABEL_LEFT_ADDITION
                ),
                (self.PLOT_ATLAS_STAMP_ATLAS_TOP_WITH_RATIO
                 if self._ratio_plot
                 else self.PLOT_ATLAS_STAMP_ATLAS_TOP),
                atlas_label
            )

            # Draw 'ATLAS'
            stamp.SetTextFont(self.PLOT_ATLAS_STAMP_ATLAS_TEXT_FONT)
            stamp.DrawLatex(
                self.PLOT_ATLAS_STAMP_LEFT,
                (self.PLOT_ATLAS_STAMP_ATLAS_TOP_WITH_RATIO
                 if self._ratio_plot
                 else self.PLOT_ATLAS_STAMP_ATLAS_TOP),
                'ATLAS'
            )

    def draw_legend(self, *histograms):
        """Draws a legend onto the plot with the specified histograms.

        It is recommended that you construct the Plot with plot_header = True
        in order to make space for the legend.

        Args:
            histograms: Each argument of this function after plot may be a
                single histogram, an iterable of histograms (each of which
                should be plotted), or a THStack object.
        """
        # Check if we already have a legend
        if hasattr(self, '_legend'):
            raise RuntimeError('legend already exists on this plot')

        # Switch to the context of the main plot
        self._plot.cd()

        # Create the legend
        self._legend = TLegend(self.PLOT_LEGEND_LEFT,
                               (self.PLOT_LEGEND_BOTTOM_WITH_RATIO
                                if self._ratio_plot
                                else self.PLOT_LEGEND_BOTTOM),
                               self.PLOT_LEGEND_RIGHT,
                               (self.PLOT_LEGEND_TOP_WITH_RATIO
                                if self._ratio_plot
                                else self.PLOT_LEGEND_TOP))
        SetOwnership(self._legend, False)

        # Style it
        self._legend.SetTextSize((
            self.PLOT_LEGEND_TEXT_SIZE_WITH_RATIO
            if self._ratio_plot
            else self.PLOT_LEGEND_TEXT_SIZE
        ))
        self._legend.SetBorderSize(0)
        self._legend.SetFillStyle(0) # transparent
        self._legend.SetNColumns(self.PLOT_LEGEND_N_COLUMNS)

        # Create a chained list of all histograms.  We decompose THStack
        # objects in reverse order, i.e. top-to-bottom.
        histograms = \
            list(chain(*(histogram_iterable(h, True, True)
                         for h
                         in histograms)))

        # Add anything to this list that we created internally
        histograms.extend(self._legend_extras)

        # Because ROOT draws histograms from left-to-right across rows and not
        # top-to-bottom along columns, we need to do a bit of a pivot on the
        # list so that the histograms appear in the vertical order of the stack
        n_entries = len(histograms)
        n_col = self.PLOT_LEGEND_N_COLUMNS
        n_row = int(ceil(float(n_entries) / n_col))
        legend_order = []
        for r in xrange(0, n_row):
            for c in xrange(0, n_col):
                if (r * n_col + c) == n_entries:
                    # Don't need an outer break, this would only happen on the
                    # last row if n_row * n_col != n_entries
                    break
                legend_order.append(histograms[r + c * n_row])

        # Add the histograms
        for histogram in legend_order:
            SetOwnership(histogram, False)
            title = histogram.GetTitle()
            # NOTE: Convention: legend for histograms with a non-default
            # marker style to be drawn with lp
            if histogram.GetMarkerStyle() != 0:
                self._legend.AddEntry(histogram, title, 'lp')
            else:
                self._legend.AddEntry(histogram, title, 'f')

        # Draw the legend
        self._legend.Draw()
