"""Contains the Evaluate object, which has methods to load data from Cavecalc
.pkl output files, display data and write it to other file formats.

Classes defined here:
    Evaluate
"""

import pickle
import os
import pandas as pd
import copy
import matplotlib
import sys
from sys import platform

# Check platform and set backend accordingly
if platform in ['win32', 'darwin', 'linux']:  # Windows, macOS, or Linux
    matplotlib.use('TkAgg')  # Use TkAgg for GUI support
else:
    if 'ipykernel' in sys.modules:  # Check if running in Jupyter (e.g., Binder or WSL2)
        matplotlib.use('nbAgg')  # Use nbAgg backend for Jupyter Notebooks
    else:
        matplotlib.use('Agg')  # Use Agg backend for headless environments
        
from matplotlib import pyplot as plt
import matplotlib.patches as patches
import numpy as np
import cavecalc.util as ccu
import scipy.io as sio
import seaborn as sns
from matplotlib.lines import Line2D

class Evaluate(object):
    """Processes of Cavecalc model output.
    
    Evaluate contains methods to load, process, format and display Cavecalc
    model data saved in .pkl files. It allows model output to be saved to .csv
    and .mat files for further processing.
    
    Evaluate objects may be used directly (see examples), and are also used
    under the hood by the output GUI.
    
    Methods:
    settings_report - Get a dict summarising model settings
        load_data           - Load .pkl files from a directory
        save_csvs           - Save all loaded model output to .csv files
        save_all_mat        - Save all loaded model output to a .mat file
        filter_out_noprecip - Filter out all model steps that don't
                              precipitate calcite.
        filter_by_index     - Filter model steps in/out based on a model step 
                              index.
        filter_by_results   - Filter model steps in/out based on any output 
                              parameter.
        filter_by_settings  - Filter whole models in/out based in any input 
                              parameter.
        plot_models         - Plot all loaded models.
        plot_points         - Plot selected steps from all loaded models.
    """
    
    def __init__(self):
        """Initialise an Evaluate object.
        
        After initialisation, load_data must be called to read data from .pkl
        files.
        """
        
        self._models = []
        self._settings = []
      

    @property
    def model_settings(self):
        """Return a list of dicts containing model settings.
        
        Generates a list of dicts from from all loaded SettingsObjects by
        calling their .dict() method.
        
        Returns:
            A list of settings dicts.
        """
        
        if not self._settings:
            raise ValueError("Object %r has no models loaded." % self)
        
        o = [s.dict() for s in self._settings]
        for d in o:
            try:
                d.pop('id')
            except KeyError:
                pass
            
        if o:
            return copy.deepcopy(o)
        else:
            raise ValueError("Object %r has no models loaded." % self)
    
    @property
    def model_results(self):
        """Return a list of dicts containing model output.
        
        Returns:
            A list of results dicts.
        """
        
        if self._models:
            return copy.deepcopy(self._models)
        else:
            raise ValueError("Object %r has no models loaded." % self)
    
    def get_settings_report(self):
        """Get a summary of the range of model settings.

        Returns:
        A dict of model settings, with one entry for each unique value detected.
        """

        d = self.model_settings[0]
        o = dict.fromkeys(d.keys(),[])
        for s in self.model_settings:
            for k, v in s.items():
                if v not in o[k]:
                    o[k].append(v)
        try:
            o.pop('id')
        except KeyError:
            pass
        return o

    def load_data(self, *args):
        """Load .pkl data into the Evaluate object for processing.
        
        Data is loaded from a directory. The directory must contain
        settings.pkl and results.pkl. load_data may be called multiple times
        to merge different model suites for comparison.
        
        Args:
            *args: The directories to load data from.
        """        

        ret_dir = os.getcwd()
        
        if len(args) == 0:
            args = (ret_dir,)
            
        for d in args:
            os.chdir(d)
            try:
                print("Attempting to load data from %s..." % d, end="")
                with open('settings.pkl', 'rb') as f:
                    self._settings.extend(pickle.load(f))

                with open('results.pkl', 'rb') as f:
                    r = pickle.load(f)
                    self._models.extend([a for (a,b) in r])
                print(" Done")
            finally:
                os.chdir(ret_dir)

    def save_csvs(self, directory=None):
        """Save model output to .csv files.
        
        One file is saved for each model loaded. Note that only model output
        can be saved to csv, not the settings used.
        
        csv files may be easily read in any spreadsheet program.
        
        Args:
            directory (str): The directory to save output to.
        """
        
        if not directory:
            directory = os.getcwd()
        
        for (id, model) in enumerate(self._models):
            f = os.path.join(directory, "out_%i.csv" % id)
            ccu.save_csv(model, os.path.join(f))
    



    def save_all_mat(self, file):
        """Save all loaded data to a .mat file.
        
        Data is saved as two matlab structs, reflecting the data structures
        inside settings.pkl and results.pkl respectively.
        
        Args:
            file: Filename to save to (.mat will be auto-appended)
        """

        s = dict()
        
        for i, SO in enumerate(self._settings):            # for each model
            set = SO.dict()         # settings dict
            res = self._models[i]    # results dict
            
            # remove any 'None' values from output (savemat can't handle them)
            # replace with -999 value, like PHREEQC
            n_res = dict()
            for k,v in res.items():
                nv = []
                for e in v:
                    if e is None:
                        nv.append(-999)
                    else:
                        nv.append(e)
                n_res[k] = nv
        
            o = {k:(v if type(v) is list else [v]) for k,v in set.items()}
            
            a = ccu.numpify(o)                          # settings
            b = ccu.numpify(n_res)                      # output
            
            c = { 'settings' : a,
                  'results'  : b   }
            
            name = "m" + str(i)
            s[name] = c

        sio.savemat(file, s)

    def filter_out_noprecip(self):
        """Returns a filtered copy of the Evalulate object.
        
        Models are filtered out of they do not include any precipitation
        reactions. This is useful for 'eq' mode analyses to remove 
        non-precipitating solutions.
        """
        
        A = Evaluate()
        
        for i,m in enumerate(self._models):
            a = False
            for s in m['step_desc']:
                if 'precip' in s:
                    a = True
                    break
            
            if a:
                A._models.append(copy.deepcopy(m))
                A._settings.append(copy.deepcopy(self._settings[i]))
        
        return A
    
    def filter_by_index(self, ind, n=False):
        """Return a filtered copy of the Evaluate object.
        
        Filter the model output data contained in the object. Data is filtered
        based on list index position - this corresponds to the calculation step
        in the model. This method is useful for subsetting data in preparation 
        for plotting. It works similarly to filter_by_results.
        
        Example:
            e = Evaluate()
            e.load_data('./my_data/')
            f = e.filter_by_index(-1) # extracts the final dripwater chemistry
           
        Args:
            ind: An integer index to filter by. This corresponds to a model
                step number. E.g. index 0 is the first PHREEQC calculation
                (initial water chemistry), index 1 is the bedrock dissolution
                product, index -1 is the final solution chemistry.
            n: Optional boolean argument. If True, the filter is inverted.
                Default False.
                
        Returns:
            A modified copy of the object. The copy only contains model output
            that meet the filter criteria.
        """
        A = Evaluate()
        A._settings = copy.deepcopy(self._settings)
        
        for m in self._models:
            if ind < 0:
                explicitIndex = len(m['step_desc']) + ind
            else:
                explicitIndex = ind

            if n is False:
                fil = {k : [a[explicitIndex]] for k,a in m.items()}
            else:
                fil = {k : [v for i,v in enumerate(a) if i != explicitIndex] for k,a in m.items()}
            A._models.append(fil)
            
        
        rem = []
        for i,r in enumerate(A._models):
            if max([len(v) for k,v in r.items()]) == 0:
                rem.append(i)
                
        [A._models.pop(i) for i in rem]
        [A._settings.pop(i) for i in rem]
        
        return copy.deepcopy(A)
            
    def filter_by_results(self, key, value, n=False):
        """Return a filtered copy of the Evaluate object. 
        
        Filter the model output data contained in the object. Data is filtered
        based on a key, value combination. This method is useful for 
        subsetting data in preparation for plotting. It works similarly to 
        filter_by_index.
        
        Example:
            e = Evaluate()
            e.load_data('./my_data/')
            f = e.filter_by_settings('step_desc', 'degas')
            # f includes only data from the degassing steps
        
        Args:
            key: Key in model output dicts to filter by.
            value: Value to filter 'key' by. Accepts substrings for step_desc.
            n: Optional boolean argument. If True, the filter is inverted.
                Default False.
                
        Returns:
            A filtered copy of the Evaluate object.
        """

        A = Evaluate()
        A._models = []
        A._settings = self._settings

        # filter object
        for i, m in enumerate(self._models):
            fil = {}
            a = m[key]
            for j, v in m.items():
                if len(v) == len(a):
                    if n:
                        fil[j] = [v[k] for k in range(len(v)) if value not in a[k]]
                    else:
                        fil[j] = [v[k] for k in range(len(v)) if value in a[k]]
                else:
                    fil[j] = v
            A._models.append(fil)
        return copy.deepcopy(A)

    def filter_by_settings(self, setting, value, n=False):
        """Return a filtered copy of the Evaluate object.
        
        The returned Evaluate object contains a subset of the models in the
        original. Models are filtered based on the settings, value combination
        provided. Models that meet the critera have their data included in the
        copy.
        
        Args:
            setting (str): model parameter to filter by (e.g. 'gas_volume')
            value: value of 'setting' to include (e.g. 20).
            n: Optional boolean argument. If True, the filter is inverted.
                Default False.
        Returns:
            A filtered copy of the Evaluate object.
        """

        A = Evaluate()
        A._models = []
        A._settings = []

        for i, b in enumerate(self._settings):
            d = b.dict()
            if n:
                if isinstance(value, str):
                    if value not in d[setting]:
                        A._models.append(self._models[i])
                        A._settings.append(b)
                else:
                    if d[setting] != value:
                        A._models.append(self._models[i])
                        A._settings.append(b)
            else:
                if isinstance(value, str):
                    if value in d[setting]:
                        A._models.append(self._models[i])
                        A._settings.append(b)
                else:
                    if d[setting] == value:
                        A._models.append(self._models[i])
                        A._settings.append(b)

        return copy.deepcopy(A)

    def plot_models(self, *args, x_key=None, y_key=None, 
                    label_with=None, ax=None, **kwargs):
        """Plot Model results with one series per model.
        
        Creates a simple matplotlib figure. Useful, for example, to quickly
        display the degassing evolution of a suite of models. May be combined
        with filter_by_settings, filter_by_results or filter_by_index to
        include / exclude certain parts of the dataset.
        
        Args:
            *args: Optional formatting parameters passed to pyplot.plot()
            x_key: Model output to plot on x-axis
            y_key: Model output to plot on y-axis
            label_with (optional): Model input parameter to annotate series
            ax (optional): Add data to a pre-existing matplotlib axis
            **kwargs (optional): kwargs to be passed to pyplot.plot()
        Returns:
            Axes object.
        """
        
        sns.set_style('darkgrid')
        if not ax:
            fig, ax = plt.subplots()
            ax.set_ylabel(y_key)
            ax.set_xlabel(x_key)
        for i, m in enumerate(self._models):
            if label_with:
                s = self._settings[i].get(label_with)
                a = "%s: %s" % (label_with, s)
                ax.plot(m[x_key], m[y_key], label = a, *args, **kwargs)
                ax.legend(prop={'size':6})
            else:
                ax.plot(m[x_key], m[y_key], *args, **kwargs)
            
            

        return ax

    def plot_points(self, *args, x_key=None, y_key=None, plot_index=1, 
                    label_with=None, ax=None, **kwargs):
        """Plot Model results for a point-by-point inter-model comparison.
        
        Useful, for example, to show different bedrock dissolution products
        across a suite of models.
        
        Args:
            x_key: Model output or setting parameter to plot on x-axis
            y_key: Model output to plot on y-axis
            *args (optional): Formatting parameters passed to pyplot.plot()
            plot_index: Which point to plot. e.g. 0 (initial water), 1 (bedrock
            dissolution product), -1 (fully degassed solution)
            label_with (optional): Model input parameter to label points with
            ax (optional): Add data to a pre-existing plot
            **kwargs (optional): kwargs to be passed to pyplot.plot()
        Returns:
            Axes object.
        """
        sns.set_style('darkgrid')
        
        x_vals = []
        y_vals = []
        labels = []

        # look for x_key in results
        if x_key in list(self._models[0].keys()):
            for i, m in enumerate(self._models):
                try:
                    x_vals.append(m[x_key][plot_index])
                except IndexError:
                    pass

        # otherwise, find it in settings
        else:
            for i, s in enumerate(self._settings):
                x_vals.append(s.dict()[x_key])

        for i, m in enumerate(self._models):
            if label_with:
                s = self._settings[i].dict()
            try:
                y_vals.append(m[y_key][plot_index])
                if label_with:
                    labels.append(s[label_with])
            except IndexError:
                pass
        
        if not ax:
            fig, ax = plt.subplots()
            ax.set_ylabel(y_key)
            ax.set_xlabel(x_key)
        ax.plot(x_vals, y_vals, *args, **kwargs)
        if label_with:
            for lab, x, y in zip(labels, x_vals, y_vals):
                ax.annotate('%s=%s' % (label_with, lab),
                            xy=(x, y), fontsize=8)
                     
        return ax 
     
        

# =============================================================================
# LAYOUT CONSTANTS
# =============================================================================

# Header band, measured in INCHES from the top of the figure. Using inches
# rather than figure fractions means the header does not drift when the
# number of subplot rows changes the figure height.
HDR_TITLE_IN = 0.35      # main title
HDR_LEGEND_IN = 0.72     # legend row, directly under the title
HDR_TOP_IN = 1.20        # first line of the annotation columns
HDR_LINE_IN = 0.22       # line spacing within a column
HDR_BAND_IN = 2.60       # total reserved height above the axes

# Header column x positions (figure fraction, left-aligned)
HDR_COLS = (0.10, 0.40, 0.70)

# Axes margins, in INCHES, so the border never clips tick labels or the
# y-axis label regardless of figure size.
MARGIN_LEFT_IN = 1.00
MARGIN_RIGHT_IN = 0.45
MARGIN_BOTTOM_IN = 1.10

FS_HDR_TITLE = 10
FS_HDR_BODY = 9.5
FS_PANEL = 9.5           # panel letter + subtitle

# Horizontal separation between the three scatter groups within a panel,
# in units of the age-index spacing (1.0 = one full age slot).
GROUP_OFFSET = 0.24

# Style for the "all modelled data" cloud.
#   'range'   - a light grey vertical bar spanning the modelled range (default)
#   'scatter' - the original point cloud, but faint
ALL_OUTPUT_STYLE = "range"
ALL_OUTPUT_PCTL = (2.5, 97.5)     # percentiles for the range bar
ALL_OUTPUT_COLOUR = "0.72"

MATCHED_COLOUR = "darkgreen"
MEASURED_COLOUR = "black"

BORDER_PAD_IN = 0.22

PROXY_LABELS = {
    "d13c": "\u03b4\u00b9\u00b3C",
    "d18o": "\u03b4\u00b9\u2078O",
    "d44ca": "\u03b4\u2074\u2074Ca",
    "mgca": "Mg/Ca",
    "srca": "Sr/Ca",
    "baca": "Ba/Ca",
    "uca": "U/Ca",
    "dcp": "DCP",
}


# =============================================================================
# MODULE-LEVEL HELPERS
# =============================================================================

def _top_frac(fig, inches_from_top):
    """Convert a distance in inches below the figure top into a y fraction."""
    return 1.0 - inches_from_top / fig.get_figheight()


def _draw_header_column(fig, x, title, lines, top_in=HDR_TOP_IN):
    """
    Draw one left-aligned header column: a bold title then plain lines.

    Returns the inches-from-top position of the next free line, so columns
    of different lengths can be extended without hardcoding positions.
    """
    y_in = top_in
    fig.text(
        x, _top_frac(fig, y_in), title,
        ha="left", va="top", fontsize=FS_HDR_TITLE, fontweight="bold",
    )
    y_in += HDR_LINE_IN * 1.25

    for line in lines:
        if not line:
            continue
        fig.text(
            x, _top_frac(fig, y_in), line,
            ha="left", va="top", fontsize=FS_HDR_BODY,
        )
        y_in += HDR_LINE_IN

    return y_in


# =============================================================================
# CDAPlotter
# =============================================================================

class CDAPlotter:
    """Class for creating CDA (Cave Data Analysis) plots."""

    def __init__(self):
        # Set font for subscript support
        matplotlib.rcParams["font.family"] = "DejaVu Sans"

        # Column mappings
        self.column_mapping = {
            "d13c": "CaveCalc d13C", "mgca": "CaveCalc MgCa",
            "dcp": "CaveCalc DCP", "d44ca": "CaveCalc d44Ca",
            "srca": "CaveCalc SrCa", "baca": "CaveCalc BaCa",
            "uca": "CaveCalc UCa", "d18o": "CaveCalc d18O",
        }

        self.axis_labels = {
            "d13c": "\u03b4\u00b9\u00b3C$_{CaCO_3}$ (\u2030, VPDB)",
            "d18o": "\u03b4\u00b9\u2078O$_{CaCO_3}$ (\u2030, VPDB)",
            "d44ca": "\u03b4\u2074\u2074Ca$_{CaCO_3}$ (\u2030)",
            "mgca": "Mg/Ca$_{CaCO_3}$ (mmol/mol)",
            "dcp": "DCP$_{CaCO_3}$ (%)",
            "srca": "Sr/Ca$_{CaCO_3}$ (mmol/mol)",
            "baca": "Ba/Ca$_{CaCO_3}$ (mmol/mol)",
            "uca": "U/Ca$_{CaCO_3}$ (mmol/mol)",
        }

        self.trace_metals = ["Mg", "Sr", "Ba", "U", "d44"]
        self._test_cols = set()

    # -------------------------------------------------------------------------
    # DATA LOADING
    # -------------------------------------------------------------------------

    def load_data(self, dir1, dir2):
        """Load all required CSV files."""
        data = {}

        csv_files = {
            "matches": os.path.join(dir2, "Matches.csv"),
            "tolerances": os.path.join(dir2, "Tolerances.csv"),
            "input_ranges": os.path.join(dir2, "Input_Ranges.csv"),
            "all_outputs": os.path.join(dir2, "All_outputs.csv"),
            "test": dir1,
        }

        for key, path in csv_files.items():
            if key == "matches":
                data[key] = pd.read_csv(
                    path, on_bad_lines="skip", low_memory=False
                )
            else:
                data[key] = pd.read_csv(path, low_memory=False)

        # Clean test data columns
        test_cols = data["test"].columns
        data["test"].columns = [test_cols[0]] + [
            col.strip().lower().replace(r"[^a-z0-9]", "")
            for col in test_cols[1:]
            .str.strip().str.lower()
            .str.replace(r"[^a-z0-9]", "", regex=True)
        ]

        self._test_cols = set(
            map(str, data["test"].columns.str.strip().str.lower())
        )

        # Filter out invalid data
        data["matches"] = data["matches"][
            data["matches"]["CaveCalc d13C"] != -999
        ]
        data["all_outputs"] = data["all_outputs"][
            data["all_outputs"]["CaveCalc d13C"] != -999
        ]

        return data

    def find_age_columns(self, df_main, df_test):
        """Find age columns in both datasets."""
        age_main = next(
            (col for col in df_main.columns if "age" in col.lower()), None
        )
        age_test = next(
            (col for col in df_test.columns if "age" in col.lower()), None
        )

        if not age_main or not age_test:
            raise ValueError(
                "Could not find 'Age' column in one or both datasets."
            )

        return age_main, age_test

    def format_trace_metals(self, df_main):
        """Return (bedrock_text, soil_text) summaries of trace metal inputs."""
        bedrock_values, soil_values = {}, {}
        col_map = {
            "d13C": ("bedrock_d13C", "soil_d13C"),
            "d18O": ("bedrock_d18O", "soil_d18O"),
            "d44Ca": ("bedrock_d44Ca", "soil_d44Ca"),
        }

        for metal in self.trace_metals:
            bedrock_col, soil_col = col_map.get(
                metal, (f"bedrock_{metal}Ca", f"soil_{metal}Ca")
            )
            if bedrock_col in df_main.columns:
                bedrock_values[metal] = df_main[bedrock_col].dropna().unique()
            if soil_col in df_main.columns:
                soil_values[metal] = df_main[soil_col].dropna().unique()

        # Display names: isotope ratios take a delta and a per-mil, trace
        # metals take an X/Ca. 'd44' is the workbook key, not a label.
        isotope_labels = {
            "d44": "\u03b4\u2074\u2074Ca",
            "d44Ca": "\u03b4\u2074\u2074Ca",
            "d18O": "\u03b4\u00b9\u2078O",
            "d13C": "\u03b4\u00b9\u00b3C",
        }

        def format_text(vals):
            parts = []
            for metal, v in vals.items():
                if len(v) == 0 or not all(x != 0 for x in v):
                    continue
                joined = ", ".join(map(str, v))
                if metal in isotope_labels:
                    parts.append(f"{isotope_labels[metal]}: {joined} \u2030")
                else:
                    parts.append(f"{metal}/Ca: {joined}")
            return ", ".join(parts)

        return format_text(bedrock_values), format_text(soil_values)

    # -------------------------------------------------------------------------
    # SHARED PANEL DRAWING
    # -------------------------------------------------------------------------

    def create_boxplot_with_scatter(self, ax, df, age_col, var_col, color,
                                    marker, positions=None):
        """Create boxplot with scatter overlay."""
        unique_ages = np.sort(df[age_col].unique())
        grouped_data = df.groupby(age_col)[var_col].apply(list)

        if positions is None:
            positions = np.arange(len(grouped_data))
            data_for_boxplot = grouped_data.tolist()
        else:
            data_for_boxplot = [grouped_data.get(age, []) for age in unique_ages]

        box_width = (
            (positions.max() - positions.min()) / (len(positions) * 4)
            if len(positions) > 1 else 0.1
        )
        ax.boxplot(
            data_for_boxplot, positions=positions, widths=box_width,
            patch_artist=True,
            boxprops=dict(facecolor="none", color="0.35", linewidth=0.9),
            medianprops=dict(color="black", linewidth=1.2),
            whiskerprops=dict(color="0.35", linewidth=0.9),
            capprops=dict(color="0.35", linewidth=0.9),
            showfliers=False,
        )

        scatter_positions = np.interp(df[age_col], unique_ages, positions)
        ax.scatter(
            scatter_positions, df[var_col], marker=marker, color=color,
            s=26, alpha=0.75, edgecolor="none", zorder=3,
        )

        # Faint alternating age bands
        for slot in positions[::2]:
            ax.axvspan(slot - 0.5, slot + 0.5, color="0.965", zorder=0)

        ax.set_xticks(positions)
        ax.set_xticklabels(
            [f"{a:g}" for a in unique_ages], rotation=45, ha="right",
            fontsize=8.5,
        )
        ax.set_xlim(-0.6, len(positions) - 0.4)
        ax.tick_params(axis="y", labelsize=8.5)
        ax.grid(axis="y", color="0.9", linewidth=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

        return positions

    def add_subplot_annotations(self, ax, title, subtitle, index=None):
        """
        Add a panel letter and subtitle above the axes, wrapped onto extra
        rows when the text is wider than the panel.

        Call this AFTER add_figure_elements, so the axes have their final
        width and the wrapping is measured against it.
        """
        label = f"{title}\u2003{subtitle}"
        fig = ax.get_figure()

        # Panel width in points, from the (already adjusted) axes position.
        panel_pt = ax.get_position().width * fig.get_figwidth() * 72.0

        def _width_pt(text):
            """Rendered width of `text` in points, with a crude fallback."""
            probe = fig.text(0, 0, text, fontsize=FS_PANEL, fontweight="bold")
            try:
                renderer = fig.canvas.get_renderer()
                w = probe.get_window_extent(renderer=renderer).width
                w *= 72.0 / fig.dpi
            except Exception:
                # No renderer yet (some backends): approximate.
                w = len(text) * FS_PANEL * 0.52
            finally:
                probe.remove()
            return w

        # Wrap onto as many rows as needed. Splitting on whitespace only,
        # so mathtext groups such as $_{soil-CO_2}$ are never broken.
        if _width_pt(label) > panel_pt:
            words = label.split(" ")
            lines, current = [], ""
            for word in words:
                trial = f"{current} {word}".strip()
                if current and _width_pt(trial) > panel_pt:
                    lines.append(current)
                    current = word
                else:
                    current = trial
            if current:
                lines.append(current)
            label = "\n".join(lines)

        ax.text(
            0.0, 1.04, label, transform=ax.transAxes,
            fontsize=FS_PANEL, fontweight="bold",
            ha="left", va="bottom", linespacing=1.35,
        )

    # -------------------------------------------------------------------------
    # FIGURE FURNITURE
    # -------------------------------------------------------------------------

    def add_figure_elements(self, fig, title, color, legend_elements=None):
        """Add common figure elements (title, legend, border, watermark)."""
        fig_w = fig.get_figwidth()
        fig_h = fig.get_figheight()

        # All margins fixed in inches: the header band stays a constant
        # physical size, and the bottom margin always leaves room for the
        # rotated tick labels, the x-label and the watermark.
        fig.subplots_adjust(
            left=MARGIN_LEFT_IN / fig_w,
            right=1.0 - MARGIN_RIGHT_IN / fig_w,
            top=1.0 - HDR_BAND_IN / fig_h,
            bottom=MARGIN_BOTTOM_IN / fig_h,
            hspace=0.62, wspace=0.30,
        )

        fig.suptitle(
            title, fontsize=15, fontweight="bold",
            y=_top_frac(fig, HDR_TITLE_IN), va="top",
        )

        # Watermark: bottom-left, between the axes and the border.
        pad_x = BORDER_PAD_IN / fig_w
        pad_y = BORDER_PAD_IN / fig_h
        fig.text(
            pad_x + 0.012, pad_y + 0.010, "Produced by CaveCalc v2.0",
            ha="left", va="bottom", fontsize=8, color="0.55",
        )

        if legend_elements:
            fig.legend(
                handles=legend_elements["handles"],
                labels=legend_elements["labels"],
                loc="upper center",
                bbox_to_anchor=(0.5, _top_frac(fig, HDR_LEGEND_IN)),
                ncol=legend_elements.get("ncol", 4),
                fontsize=FS_HDR_BODY,
                frameon=False,
                handletextpad=0.6,
                columnspacing=2.0,
            )

        # Border, inset by a fixed number of inches so it does not clip text.
        rect = patches.FancyBboxPatch(
            (pad_x, pad_y), 1 - 2 * pad_x, 1 - 2 * pad_y,
            transform=fig.transFigure,
            boxstyle="round,pad=0.005",
            edgecolor=color, linewidth=2.5, fill=False,
            clip_on=False, zorder=1000,
        )
        fig.patches.append(rect)

    def _missing_proxy_lines(self):
        """Proxies absent from the test CSV, wrapped into rows of four."""
        missing = [
            PROXY_LABELS.get(p, p)
            for p in self.column_mapping
            if p not in self._test_cols
        ]
        if not missing:
            return ["(none \u2014 all proxies supplied)"]
        return [
            "   ".join(missing[i:i + 4])
            for i in range(0, len(missing), 4)
        ]

    def add_input_annotations(self, fig, input_ranges_df, bedrock_text,
                              soil_text, mode="standard"):
        """
        Add input parameter annotations as three tidy header columns.

        mode:
            'standard' - soil inputs | miscellaneous inputs | missing proxies
            'flowpath' - bedrock inputs | miscellaneous inputs | missing proxies
        """

        def _range_line(var, label):
            row = input_ranges_df[input_ranges_df["Variable"] == var]
            if row.empty:
                return None
            return (
                f"{label}: {row['Minimum'].values[0]} to "
                f"{row['Maximum'].values[0]}"
            )

        # --- Column 1 ---
        if mode == "flowpath":
            col1_title = "Bedrock inputs"
            col1_lines = [v.strip() for v in bedrock_text.split(",") if v.strip()]
            gas_line = _range_line("gas_volume", "gas-to-water ratio (L/kg)")
            if gas_line:
                col1_lines.append(gas_line)
        else:
            col1_title = "Soil inputs"
            col1_lines = [
                _range_line("soil_pCO2", "soil-gas pCO\u2082 (ppmv)"),
                _range_line(
                    "soil_d13C",
                    "\u03b4\u00b9\u00b3C$_{soil-CO_2}$ (\u2030)",
                ),
            ]
            col1_lines += [v.strip() for v in soil_text.split(",") if v.strip()]

        _draw_header_column(fig, HDR_COLS[0], col1_title, col1_lines)

        # --- Column 2: miscellaneous inputs ---
        misc_lines = [
            _range_line("temperature", "T (\u00b0C)"),
            _range_line("cave_pCO2", "cave air pCO\u2082 (ppmv)"),
        ]
        _draw_header_column(fig, HDR_COLS[1], "Miscellaneous inputs", misc_lines)

        # --- Column 3: measurements not supplied ---
        _draw_header_column(
            fig, HDR_COLS[2], "Measurements not supplied",
            self._missing_proxy_lines(),
        )

    # -------------------------------------------------------------------------
    # PLOT 1: CO2 PROCESSES
    # -------------------------------------------------------------------------

    def plot_co2_processes(self, data):
        """Create CO2 processes plot."""
        df_main = data["matches"]
        age_col_main, _ = self.find_age_columns(df_main, data["test"])

        variables = ["soil_d13C", "soil_pCO2", "cave_pCO2", "d13C_init"]
        custom_labels = {
            "soil_d13C": (
                "\u03b4\u00b9\u00b3C$_{soil-CO_2}$ (\u2030, VPDB)"
            ),
            "soil_pCO2": "Soil gas pCO\u2082 (ppmv)",
            "cave_pCO2": "Cave air pCO\u2082 (ppmv)",
            "d13C_init": "\u03b4\u00b9\u00b3C$_{initial\\ solution}$ (\u2030, VPDB)",
        }
        subplot_titles = ["[A]", "[B]", "[C]", "[D]"]
        subtitles = [
            "Viable \u03b4\u00b9\u00b3C$_{soil-CO_2}$ values that match "
            "measured speleothem data",
            "Viable soil gas pCO\u2082 values that match "
            "measured speleothem data",
            "Viable cave air pCO\u2082 values that match "
            "measured speleothem data",
            "Viable \u03b4\u00b9\u00b3C$_{initial\\ solution}$ values that match "
            "measured speleothem data",
        ]

        fig, axs = plt.subplots(2, 2, figsize=(12, 2 * 2.9 + HDR_BAND_IN + MARGIN_BOTTOM_IN))
        axs = axs.flatten()
        pending_annotations = []

        for i, var in enumerate(variables):
            if var in df_main.columns:
                color = "darkblue" if var == "d13C_init" else "darkgreen"
                marker = "s" if var == "d13C_init" else "o"

                self.create_boxplot_with_scatter(
                    axs[i], df_main, age_col_main, var, color, marker
                )
                axs[i].set_ylabel(custom_labels[var], fontsize=9.5)
                pending_annotations.append(
                    (axs[i], subplot_titles[i], subtitles[i])
                )
            else:
                axs[i].axis("off")

        for ax in axs[-2:]:
            ax.set_xlabel("Age (ka)", fontsize=9.5)

        legend_elements = {
            "handles": [
                Line2D([0], [0], marker="o", color="darkgreen",
                       linestyle="None", markersize=8),
                Line2D([0], [0], marker="s", color="darkblue",
                       linestyle="None", markersize=8),
            ],
            "labels": ["Model inputs", "Model outputs"],
            "ncol": 2,
        }
        self.add_figure_elements(fig, "CO\u2082 Processes", "firebrick",
                                 legend_elements)

        # Annotate now that the axes have their final width, so the
        # subtitles wrap against the real panel size.
        for ax, letter, subtitle in pending_annotations:
            self.add_subplot_annotations(ax, letter, subtitle)

        bedrock_text, soil_text = self.format_trace_metals(df_main)
        self.add_input_annotations(
            fig, data["input_ranges"], bedrock_text, soil_text
        )

        return fig

    # -------------------------------------------------------------------------
    # PLOT 2: FLOW PATH CONTROLS
    # -------------------------------------------------------------------------

    def plot_flow_path_controls(self, data):
        """Create Flow Path Controls plot."""
        df_main = data["matches"]
        age_col_main, _ = self.find_age_columns(df_main, data["test"])

        variables = ["gas_volume", "f_ca"]
        subplot_titles = ["[A]", "[B]"]
        subtitles = [
            "Viable Soil gas-to-water ratios that match "
            "measured speleothem data",
            "Viable f$_{Ca}$ values that match "
            "measured speleothem data",
        ]
        y_labels = {
            "gas_volume": "Soil gas-to-water ratio (L/kg)",
            "f_ca": "f$_{Ca}$",
        }

        fig, axs = plt.subplots(1, 2, figsize=(12, 2.9 + HDR_BAND_IN + MARGIN_BOTTOM_IN))
        axs = np.atleast_1d(axs).flatten()
        pending_annotations = []

        for i, var in enumerate(variables):
            if var in df_main.columns:
                color = "darkgreen" if var == "gas_volume" else "darkblue"
                marker = "s" if var == "f_ca" else "o"

                self.create_boxplot_with_scatter(
                    axs[i], df_main, age_col_main, var, color, marker
                )
                axs[i].set_xlabel("Age (ka)", fontsize=9.5)
                axs[i].set_ylabel(y_labels.get(var, var), fontsize=9.5)
                pending_annotations.append(
                    (axs[i], subplot_titles[i], subtitles[i])
                )
            else:
                axs[i].axis("off")

        legend_elements = {
            "handles": [
                Line2D([0], [0], marker="o", color="darkgreen",
                       linestyle="None", markersize=8),
                Line2D([0], [0], marker="s", color="darkblue",
                       linestyle="None", markersize=8),
            ],
            "labels": ["Model inputs", "Model outputs"],
            "ncol": 2,
        }
        self.add_figure_elements(fig, "Flow Path Controls", "steelblue",
                                 legend_elements)

        for ax, letter, subtitle in pending_annotations:
            self.add_subplot_annotations(ax, letter, subtitle)

        bedrock_text, soil_text = self.format_trace_metals(df_main)
        self.add_input_annotations(
            fig, data["input_ranges"], bedrock_text, soil_text,
            mode="flowpath",
        )

        # NOTE: the previous version returned None here whenever every proxy
        # was supplied, because of a bare `return` in the annotation block.
        return fig

    # -------------------------------------------------------------------------
    # PLOT 3: MODEL-DATA COMPARISON
    # -------------------------------------------------------------------------

    def plot_model_data_comparison(self, data):
        """Create Model-Data comparison plot."""
        df_main = data["matches"]
        df_test = data["test"]
        df_all_outputs = data["all_outputs"]
        df_tolerances = data["tolerances"]

        age_col_main, age_col_test = self.find_age_columns(df_main, df_test)

        num_plots = len(self.column_mapping)
        num_rows = int(np.ceil(num_plots / 2))

        fig, axs = plt.subplots(
            num_rows, 2,
            figsize=(13, 2.6 * num_rows + HDR_BAND_IN + MARGIN_BOTTOM_IN),
        )
        axs = np.atleast_1d(axs).flatten()

        unique_ages = np.sort(np.unique(np.concatenate([
            df_main[age_col_main].unique(),
            df_test[age_col_test].unique(),
            df_all_outputs[age_col_main].unique(),
        ])))
        positions = np.arange(len(unique_ages))

        for i, (key, mapped_col) in enumerate(self.column_mapping.items()):
            ax = axs[i]

            has_model = mapped_col in df_main.columns
            has_measured = key in df_test.columns

            if not (has_model and has_measured):
                # Empty panel: strip it back so it reads as absent, not as a
                # real 0-1 axis with meaningless ticks.
                ax.text(
                    0.5, 0.5,
                    f"No {PROXY_LABELS.get(key, key)} data provided",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=10, color="0.45",
                )
                ax.set_xticks([])
                ax.set_yticks([])
                for spine in ax.spines.values():
                    spine.set_visible(False)
                ax.set_ylabel(
                    self.axis_labels.get(key, key), fontsize=9, color="0.45"
                )
                continue

            tolerance_row = df_tolerances[
                df_tolerances["Proxy"].str.lower() == key.lower()
            ]
            tolerance = (
                tolerance_row["Tolerance Value"].values[0]
                if not tolerance_row.empty else 0
            )

            # Three groups, evenly separated about the age slot centre.
            pos_main = np.searchsorted(unique_ages, df_main[age_col_main])
            pos_test = np.searchsorted(unique_ages, df_test[age_col_test])
            pos_all = np.searchsorted(
                unique_ages, df_all_outputs[age_col_main]
            )

            # Faint alternating age bands, drawn first
            for slot in positions[::2]:
                ax.axvspan(slot - 0.5, slot + 0.5, color="0.965", zorder=0)

            # --- All modelled output: context, not ink ---
            if mapped_col in df_all_outputs.columns:
                if ALL_OUTPUT_STYLE == "range":
                    vals = df_all_outputs[mapped_col].to_numpy(dtype=float)
                    for slot in np.unique(pos_all):
                        sel = vals[pos_all == slot]
                        sel = sel[np.isfinite(sel)]
                        if not sel.size:
                            continue
                        y_lo, y_hi = np.percentile(sel, ALL_OUTPUT_PCTL)
                        ax.plot(
                            [slot - GROUP_OFFSET] * 2, [y_lo, y_hi],
                            color=ALL_OUTPUT_COLOUR, linewidth=6,
                            solid_capstyle="butt", zorder=1,
                        )
                else:
                    ax.scatter(
                        pos_all - GROUP_OFFSET, df_all_outputs[mapped_col],
                        marker="o", color=ALL_OUTPUT_COLOUR, s=12,
                        alpha=0.35, linewidths=0, zorder=1,
                    )

            # --- Matched modelled data ---
            ax.scatter(
                pos_main, df_main[mapped_col],
                marker="o", facecolor=MATCHED_COLOUR, edgecolor="none",
                s=32, alpha=0.85, zorder=3,
            )

            # --- Measured data, with tolerance whiskers ---
            ax.scatter(
                pos_test + GROUP_OFFSET, df_test[key],
                marker="s", facecolor=MEASURED_COLOUR, edgecolor="none",
                s=34, zorder=4,
            )
            for j, slot in enumerate(pos_test):
                test_val = df_test[key].iloc[j]
                ax.vlines(
                    slot + GROUP_OFFSET,
                    test_val - tolerance, test_val + tolerance,
                    colors=MEASURED_COLOUR, linestyles="--", linewidth=1.0,
                    zorder=3,
                )

            ax.set_xticks(positions)
            ax.set_xticklabels(
                [f"{a:g}" for a in unique_ages], rotation=45, ha="right",
                fontsize=8.5,
            )
            ax.set_xlim(-0.6, len(unique_ages) - 0.4)
            ax.set_ylabel(self.axis_labels.get(key, key), fontsize=9)
            ax.tick_params(axis="y", labelsize=8.5)
            ax.grid(axis="y", color="0.9", linewidth=0.6)
            ax.set_axisbelow(True)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)

        # Only the bottom row carries the x-label
        for ax in axs[-2:]:
            ax.set_xlabel("Age (ka)", fontsize=9.5)

        for j in range(len(self.column_mapping), len(axs)):
            axs[j].axis("off")

        all_handle = (
            Line2D([0], [0], color=ALL_OUTPUT_COLOUR, linewidth=6)
            if ALL_OUTPUT_STYLE == "range"
            else Line2D([0], [0], marker="o", color=ALL_OUTPUT_COLOUR,
                        linestyle="None", markersize=8, alpha=0.5)
        )

        legend_elements = {
            "handles": [
                all_handle,
                Line2D([0], [0], marker="o", color=MATCHED_COLOUR,
                       linestyle="None", markersize=8),
                Line2D([0], [0], marker="s", color=MEASURED_COLOUR,
                       linestyle="None", markersize=8),
                Line2D([0], [0], color=MEASURED_COLOUR, linestyle="--", lw=1.5),
            ],
            "labels": [
                (
                    f"All modelled ({ALL_OUTPUT_PCTL[0]:g}\u2013"
                    f"{ALL_OUTPUT_PCTL[1]:g}th pct)"
                    if ALL_OUTPUT_STYLE == "range" else "All modelled"
                ),
                "Matched modelled",
                "Measured",
                "Tolerance interval",
            ],
            "ncol": 4,
        }
        self.add_figure_elements(
            fig, "Model-Data comparison", "0.25", legend_elements
        )

        bedrock_text, soil_text = self.format_trace_metals(df_main)
        self.add_input_annotations(
            fig, data["input_ranges"], bedrock_text, soil_text
        )

        return fig

    # -------------------------------------------------------------------------
    # ENTRY POINT
    # -------------------------------------------------------------------------

    def plot_CDA(self, dir1, dir2, dpi=400, show=True):
        """
        Extract headings and data from files and create CDA plots.

        Figures are saved as PNG and PDF alongside the input CSVs in dir2.

        Args:
            dir1: Path to the test CSV file
            dir2: Path to the directory containing the output CSV files
            dpi: Resolution for the PNG export
            show: Display each figure as it is created
        Returns:
            A list of figures created from the data
        """
        data = self.load_data(dir1, dir2)
        figures = []

        specs = (
            (self.plot_co2_processes, "CO2_processes"),
            (self.plot_flow_path_controls, "flow_path_controls"),
            (self.plot_model_data_comparison, "model_data_comparison"),
        )

        for plot_func, stem in specs:
            fig = plot_func(data)
            if fig is None:
                print(f"[WARN] {stem}: no figure returned")
                continue
            figures.append(fig)

            for ext in ("png", "pdf"):
                path = os.path.join(dir2, f"{stem}.{ext}")
                fig.savefig(path, dpi=dpi, facecolor="white")
                print(f"[INFO] saved {os.path.abspath(path)}")

            if show:
                plt.show()

        return figures



# Usage example:
# import cavecalc.analyse as cca
# plotter = cca.CDAPlotter()
# figures = plotter.plot_CDA('path/to/test.csv', 'path/to/data/directory')

      
         
 
    
      

