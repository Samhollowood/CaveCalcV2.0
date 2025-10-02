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
     
        
 

class CDAPlotter:
    """Class for creating CDA (Carbonate Data Analyser) plots."""
    
    def __init__(self):
        # Set font for subscript support
        matplotlib.rcParams['font.family'] = 'DejaVu Sans'
        
        # Column mappings
        self.column_mapping = {
            'd13c': 'CaveCalc d13C', 'mgca': 'CaveCalc MgCa', 'dcp': 'CaveCalc DCP',
            'd44ca': 'CaveCalc d44Ca', 'srca': 'CaveCalc SrCa', 'baca': 'CaveCalc BaCa',
            'uca': 'CaveCalc UCa', 'd18o': 'CaveCalc d18O'
        }
        
        self.axis_labels = {
            'd13c': 'd13C$_{CaCO3}$ (‰, VPDB)', 'd18o': 'd18O$_{CaCO3}$ (‰, VPDB)',
            'd44ca': 'd44Ca$_{CaCO3}$ (‰)', 'mgca': 'Mg/Ca$_{CaCO3}$ (mmol/mol)',
            'dcp': 'DCP$_{CaCO3}$ (%)', 'srca': 'Sr/Ca$_{CaCO3}$ (mmol/mol)',
            'baca': 'Ba/Ca$_{CaCO3}$ (mmol/mol)', 'uca': 'U/Ca$_{CaCO3}$ (mmol/mol)'
        }
        
        self.trace_metals = ['Mg', 'Sr', 'Ba', 'U', 'd44']

    def load_data(self, dir1, dir2):
        """Load all required CSV files."""
        data = {}
        
        # Load CSV files
        csv_files = {
            'matches': os.path.join(dir2, 'Matches.csv'),
            'tolerances': os.path.join(dir2, 'Tolerances.csv'),
            'input_ranges': os.path.join(dir2, 'Input_Ranges.csv'),
            'all_outputs': os.path.join(dir2, 'All_outputs.csv'),
            'test': dir1
        }
        
        for key, path in csv_files.items():
            if key == 'matches':
                data[key] = pd.read_csv(path, on_bad_lines="skip")
            else:
                data[key] = pd.read_csv(path)
        
        # Clean test data columns
        test_cols = data['test'].columns
        data['test'].columns = [test_cols[0]] + [
            col.strip().lower().replace(r'[^a-z0-9]', '') 
            for col in test_cols[1:].str.strip().str.lower().str.replace(r'[^a-z0-9]', '', regex=True)
        ]
        
        # Filter out invalid data
        data['matches'] = data['matches'][data['matches']['CaveCalc d13C'] != -999]
        data['all_outputs'] = data['all_outputs'][data['all_outputs']['CaveCalc d13C'] != -999]
        
        return data

    def find_age_columns(self, df_main, df_test):
        """Find age columns in both datasets."""
        age_main = next((col for col in df_main.columns if 'age' in col.lower()), None)
        age_test = next((col for col in df_test.columns if 'age' in col.lower()), None)
        
        if not age_main or not age_test:
            raise ValueError("Could not find 'Age' column in one or both datasets.")
        
        return age_main, age_test

    def format_trace_metals(self, df_main):
        """Extract and format trace metal values."""
        bedrock_values = {}
        soil_values = {}
        
        for metal in self.trace_metals:
            bedrock_col = f'bedrock_{metal}Ca' if metal != 'd44' else f'bedrock_{metal}'
            soil_col = f'soil_{metal}Ca' if metal != 'd44' else f'soil_{metal}'
            
            if bedrock_col in df_main.columns:
                bedrock_values[metal] = df_main[bedrock_col].dropna().unique()
            if soil_col in df_main.columns:
                soil_values[metal] = df_main[soil_col].dropna().unique()
        
        def format_text(values_dict, unit):
            return ', '.join([
                f"{metal}/Ca: {', '.join(map(str, values))} {unit}" if metal != 'd44' 
                else f"{metal}: {', '.join(map(str, values))} ‰"
                for metal, values in values_dict.items() 
                if len(values) > 0 and all(v != 0 for v in values)
            ])
        
        return format_text(bedrock_values, "mmol/mol"), format_text(soil_values, "mmol/kgw")

    def create_boxplot_with_scatter(self, ax, df, age_col, var_col, color, marker, positions=None):
        """Create boxplot with scatter overlay."""
        if positions is None:
            grouped_data = df.groupby(age_col)[var_col].apply(list)
            positions = np.arange(len(grouped_data))
            data_for_boxplot = grouped_data.tolist()
        else:
            unique_ages = np.sort(df[age_col].unique())
            grouped_data = df.groupby(age_col)[var_col].apply(list)
            data_for_boxplot = [grouped_data.get(age, []) for age in unique_ages]
        
        # Create boxplot
        box_width = (positions.max() - positions.min()) / (len(positions) * 4) if len(positions) > 1 else 0.1
        ax.boxplot(data_for_boxplot, positions=positions, widths=box_width, patch_artist=True,
                   boxprops=dict(facecolor='none', color='black'),
                   medianprops=dict(color='black'), whiskerprops=dict(color='black'),
                   capprops=dict(color='black'), showfliers=False)
        
        # Add scatter plot
        scatter_positions = np.interp(df[age_col], np.sort(df[age_col].unique()), positions)
        ax.scatter(scatter_positions, df[var_col], marker=marker, color=color, s=50)
        
        # Set x-axis
        ax.set_xticks(positions)
        ax.set_xticklabels(np.sort(df[age_col].unique()))
        
        return positions

    def add_subplot_annotations(self, ax, title, subtitle, index):
        """Add title and subtitle to subplot."""
        ax.text(0.02, 1.01, title, transform=ax.transAxes, fontsize=12, fontweight='bold', ha='center')
        
        max_length = 100 if index < 4 else 70
        if len(subtitle) > max_length:
            first_line, second_line = subtitle[:max_length], subtitle[max_length:]
            ax.text(0.05, 1.06, first_line, transform=ax.transAxes, fontsize=10, ha='left')
            ax.text(0.05, 1.01, second_line, transform=ax.transAxes, fontsize=10, ha='left')
        else:
            ax.text(0.05, 1.01, subtitle, transform=ax.transAxes, fontsize=10, ha='left')

    def add_figure_elements(self, fig, title, color, legend_elements=None):
        """Add common figure elements (title, legend, border, watermark)."""
        # Main title
        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
        
        # Watermark
        fig.text(0.013, 0.99, 'Produced by CaveCalcv2.0', ha='left', va='top', 
                fontsize=10, color='black', alpha=0.5)
        
        # Legend
        if legend_elements:
            fig.legend(handles=legend_elements['handles'], labels=legend_elements['labels'], 
                      loc=legend_elements.get('loc', 'upper center'), 
                      bbox_to_anchor=legend_elements.get('bbox', (0.5, 0.96)), 
                      ncol=legend_elements.get('ncol', 2), fontsize=12, frameon=False)
        
        # Border
        fig.subplots_adjust(left=0.05, right=0.95, top=0.77, bottom=0.10)
        rect = patches.FancyBboxPatch((0.05, 0.05), 0.90, 0.90, transform=fig.transFigure,
                                     boxstyle="round,pad=0.05", edgecolor=color, 
                                     linewidth=5, fill=False)
        fig.patches.append(rect)

    def add_input_annotations(self, fig, input_ranges_df, bedrock_text, soil_text, test_df=None):
        """Add input parameter annotations to figure."""
        # Miscellaneous inputs
        fig.text(0.50, 0.90, 'User miscellaneous inputs', ha='center', va='center', 
                fontsize=10, fontweight='bold')
        y_pos = 0.88
        
        misc_inputs = {'temperature': 'T', 'cave_pCO2': 'cave air pCO2'}
        for var, label in misc_inputs.items():
            row = input_ranges_df[input_ranges_df['Variable'] == var]
            if not row.empty:
                fig.text(0.50, y_pos, f"{label}: ({row['Minimum'].values[0]} to {row['Maximum'].values[0]})", 
                        ha='center', va='center', fontsize=10)
                y_pos -= 0.025
        
        # Soil inputs
        fig.text(0.20, 0.95, 'User soil inputs', ha='center', va='center', 
                fontsize=10, fontweight='bold')
        y_pos = 0.93
        
        soil_inputs = {'soil_pCO2': 'soil-gas pCO2', 'soil_d13C': 'd13Cₛₒᵢₗ'}
        for var, label in soil_inputs.items():
            row = input_ranges_df[input_ranges_df['Variable'] == var]
            if not row.empty:
                fig.text(0.20, y_pos, f"{label}: ({row['Minimum'].values[0]} to {row['Maximum'].values[0]})", 
                        ha='center', va='center', fontsize=10)
                y_pos -= 0.025
        
        # Soil values
        for value in soil_text.split(', '):
            if value:
                fig.text(0.20, y_pos, value, ha='center', va='center', fontsize=10)
                y_pos -= 0.025
        
        # Available measurements - filter out proxies present in test data
        available_proxies = []
        if test_df is not None:
            test_columns_lower = [col.lower() for col in test_df.columns]
            for proxy in self.column_mapping.keys():
                # Check if this proxy is NOT in the test data
                if proxy not in test_columns_lower:
                    available_proxies.append(proxy)
        else:
            available_proxies = list(self.column_mapping.keys())
        
        fig.text(0.80, 0.95, 'Available measurements', ha='center', va='center', 
                fontsize=10, fontweight='bold')
        y_avail, x_spacing, y_spacing = 0.92, 0.05, 0.025
        
        for i, proxy in enumerate(available_proxies): 
            x_pos = 0.75 + (i % 3) * x_spacing 
            y_pos = y_avail - (i // 3) * y_spacing 
            
            label = proxy 
            if label.lower() == 'd44ca': 
                label = 'd44Ca' 
            else: 
                label = label.replace('ca', '/Ca') 
                
            fig.text(x_pos, y_pos, label, ha='center', va='center', fontsize=10)
    def plot_co2_processes(self, data):
        """Create CO2 processes plot."""
        df_main = data['matches']
        age_col_main, _ = self.find_age_columns(df_main, data['test'])
        
        variables = ['soil_d13C', 'soil_pCO2', 'cave_pCO2', 'd13C_init']
        custom_labels = {
            'soil_d13C': 'Soil d13C', 'soil_pCO2': 'Soil gas pCO2 (ppmv)',
            'cave_pCO2': 'Cave air pCO2 (ppmv)', 'd13C_init': 'd13C initial solution'
        }
        subplot_titles = ['[A]', '[B]', '[C]', '[D]']
        subtitles = [
            'Viable soil d13C, constrained by matches between modeled and measured CaCO3',
            'Viable soil gas pCO2, constrained by matches between modeled and measured CaCO3',
            'Viable cave air pCO2, constrained by matches between modeled and measured CaCO3',
            'd13C initial solution outputs from viable soil d13C, soil gas pCO2, and gas-to-water ratio'
        ]
        
        # Create subplots
        fig, axs = plt.subplots(2, 2, figsize=(15, 10))
        plt.subplots_adjust(hspace=0.25)
        axs = axs.flatten()
        
        # Plot each variable
        for i, var in enumerate(variables):
            if var in df_main.columns:
                color = 'darkblue' if var == 'd13C_init' else 'darkgreen'
                marker = 's' if var == 'd13C_init' else 'o'
                
                self.create_boxplot_with_scatter(axs[i], df_main, age_col_main, var, color, marker)
                axs[i].set_xlabel('Age')
                axs[i].set_ylabel(custom_labels[var])
                self.add_subplot_annotations(axs[i], subplot_titles[i], subtitles[i], i)
            else:
                axs[i].axis('off')
        
        # Add figure elements
        legend_elements = {
            'handles': [Line2D([0], [0], marker='o', color='darkgreen', linestyle='None', markersize=10),
                       Line2D([0], [0], marker='s', color='darkblue', linestyle='None', markersize=10)],
            'labels': ['Model Inputs', 'Model Outputs']
        }
        self.add_figure_elements(fig, 'CO2 Processes', 'red', legend_elements)
        
        # Add input annotations
        bedrock_text, soil_text = self.format_trace_metals(df_main)
        self.add_input_annotations(fig, data['input_ranges'], bedrock_text, soil_text)
        
        return fig

    def plot_flow_path_controls(self, data):
        """Create Flow Path Controls plot."""
        df_main = data['matches']
        age_col_main, _ = self.find_age_columns(df_main, data['test'])
        
        variables = ['gas_volume', 'f_ca']
        subplot_titles = ['[A]', '[B]']
        subtitles = [
            'Viable gas-to-water ratio, constrained by matches between modeled and measured CaCO3',
            'Viable fca outputs constrained by matches between modeled and measured CaCO3'
        ]
        
        # Create subplots
        fig, axs = plt.subplots(1, 2, figsize=(18, 6))
        
        # Plot each variable
        for i, var in enumerate(variables):
            if var in df_main.columns:
                color = 'darkgreen' if var == 'gas_volume' else 'darkblue'
                marker = 's' if var == 'f_ca' else 'o'
                
                self.create_boxplot_with_scatter(axs[i], df_main, age_col_main, var, color, marker)
                axs[i].set_xlabel('Age')
                
                # Set custom y-labels
                if var == 'gas_volume':
                    axs[i].set_ylabel('gas-to-water ratio (L/kg)')
                elif var == 'f_ca':
                    axs[i].set_ylabel('fCa')
                else:
                    axs[i].set_ylabel(var)
                
                self.add_subplot_annotations(axs[i], subplot_titles[i], subtitles[i], i + 4)
        
        # Add figure elements
        legend_elements = {
            'handles': [Line2D([0], [0], marker='o', color='darkgreen', linestyle='None', markersize=10),
                       Line2D([0], [0], marker='s', color='darkblue', linestyle='None', markersize=10)],
            'labels': ['Model inputs', 'Model outputs'],
            'bbox': (0.5, 0.90)
        }
        self.add_figure_elements(fig, 'Flow Path Controls', 'blue', legend_elements)
        
        # Add bedrock inputs
        bedrock_text, _ = self.format_trace_metals(df_main)
        fig.text(0.235, 0.96, 'User bedrock inputs', ha='center', va='center', 
                fontsize=10, fontweight='bold')
        
        y_pos = 0.94
        bedrock_values = bedrock_text.split(', ')
        for i, value in enumerate(bedrock_values):
            col = i // ((len(bedrock_values) + 1) // 2)
            row = i % ((len(bedrock_values) + 1) // 2)
            x_pos = 0.17 + col * 0.12
            y_pos_calc = y_pos - row * 0.025
            fig.text(x_pos, y_pos_calc, value, ha='center', va='center', fontsize=10)
        
        # Add gas volume
        row = data['input_ranges'][data['input_ranges']['Variable'] == 'gas_volume']
        if not row.empty:
            gas_text = f"gas-to-water ratio: ({row['Minimum'].values[0]} to {row['Maximum'].values[0]})"
            fig.text(0.20, y_pos - (len(bedrock_values) + 1) * 0.025, gas_text, 
                    ha='center', va='center', fontsize=10)
        
        return fig

    def plot_model_data_comparison(self, data):
        """Create Model-Data comparison plot."""
        df_main = data['matches']
        df_test = data['test']
        df_all_outputs = data['all_outputs']
        df_tolerances = data['tolerances']
        
        age_col_main, age_col_test = self.find_age_columns(df_main, df_test)
        
        # Create subplots
        num_plots = len(self.column_mapping)
        num_rows = int(np.ceil(num_plots / 2))
        fig, axs = plt.subplots(num_rows, 2, figsize=(15, 5 * num_rows))
        plt.subplots_adjust(hspace=0.40)
        axs = axs.flatten()
        
        # Get unique ages
        unique_ages = np.sort(np.unique(np.concatenate([
            df_main[age_col_main].unique(),
            df_test[age_col_test].unique(),
            df_all_outputs[age_col_main].unique()
        ])))
        positions = np.arange(len(unique_ages))
        
        # Plot each comparison
        for i, (key, mapped_col) in enumerate(self.column_mapping.items()):
            ax = axs[i]
            
            if mapped_col in df_main.columns and key in df_test.columns:
                # Get tolerance
                tolerance_row = df_tolerances[df_tolerances['Proxy'].str.lower() == key.lower()]
                tolerance = tolerance_row['Tolerance Value'].values[0] if not tolerance_row.empty else 0
                
                # Calculate positions
                num_ages = len(unique_ages)
                offset = 0.0 * num_ages + 0.022
                
                pos_main = np.searchsorted(unique_ages, df_main[age_col_main])
                pos_test = np.searchsorted(unique_ages, df_test[age_col_test]) + offset
                pos_outputs = np.searchsorted(unique_ages, df_all_outputs[age_col_main]) - offset
                
                # Plot data
                ax.scatter(pos_main, df_main[mapped_col], marker='o', color='darkgreen', 
                          s=100, label=f'Modeled {key}')
                ax.scatter(pos_test, df_test[key], marker='s', color='black', 
                          s=100, label=f'Measured {key}')
                if mapped_col in df_all_outputs.columns:
                    ax.scatter(pos_outputs, df_all_outputs[mapped_col], marker='o', 
                              color='black', s=80, alpha=0.7, label=f'Output {key}')
                
                # Add tolerance lines
                for j, age_idx in enumerate(pos_test):
                    test_val = df_test[key].iloc[j]
                    ax.vlines(age_idx, test_val - tolerance, test_val + tolerance, 
                             colors='black', linestyles='--')
            else:
                # Handle missing data
                messages = {
                    'baca': 'No Ba/Ca data provided', 'dcp': 'No DCP data provided',
                    'mgca': 'No Mg/Ca data provided', 'srca': 'No Sr/Ca data provided',
                    'uca': 'No U/Ca data provided', 'd18o': 'No d18O data provided'
                }
                message = messages.get(key, f'No {key} data provided')
                ax.text(0.5, 0.5, message, ha='center', va='center', 
                       transform=ax.transAxes, fontsize=12)
            
            # Set labels
            ax.set_xticks(positions)
            ax.set_xticklabels(unique_ages, rotation=45)
            ax.set_xlabel('Age')
            ax.set_ylabel(self.axis_labels.get(key, key), fontsize=10)
        
        # Turn off extra subplots
        for j in range(len(self.column_mapping), len(axs)):
            axs[j].axis('off')
        
        # Add figure elements
        legend_elements = {
            'handles': [Line2D([0], [0], marker='o', color='black', linestyle='None', markersize=10),
                       Line2D([0], [0], marker='o', color='darkgreen', linestyle='None', markersize=10),
                       Line2D([0], [0], marker='s', color='black', linestyle='None', markersize=10),
                       Line2D([0], [1], color='black', linestyle='--', lw=2)],
            'labels': ['All modeled data', 'Matched modeled Data', 'Measured Data', 'Tolerance Interval'],
            'bbox': (0.5, 0.96),
            'ncol': 3
        }
        self.add_figure_elements(fig, 'Model-Data comparison', 'black', legend_elements)
        
        # Add input annotations
        bedrock_text, soil_text = self.format_trace_metals(df_main)
        self.add_input_annotations(fig, data['input_ranges'], bedrock_text, soil_text)
        
        
        return fig

    def plot_CDA(self, dir1, dir2):
        """
        Extract headings and data from files and create CDA plots.
        
        Args:
            dir1: Path to the test CSV file
            dir2: Path to the directory containing the .xlsx files
            
        Returns:
            A list of figures created from the data
        """
        # Load data
        data = self.load_data(dir1, dir2)
        
        # Create plots
        figures = []
        figures.append(self.plot_co2_processes(data))
        figures.append(self.plot_flow_path_controls(data))
        figures.append(self.plot_model_data_comparison(data))
        
        # Show all plots
        for fig in figures:
            plt.show(block=False)
        
        return figures


# Usage example:
# import cavecalc.analyse as cca
# plotter = cca.CDAPlotter()
# figures = plotter.plot_CDA('path/to/test.csv', 'path/to/data/directory')

      

         
 
    
      

