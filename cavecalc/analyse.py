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
        get_settings_report - Get a dict summarising model settings
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
     
        
 
    def plot_CDA(self,dir1,dir2): 
        """
        Extract headings and data from a file and return as a dictionary.

        param directory: Path to the directory containing the .xlsx files 
        return: A list of figures created from the data 
         """ 
         
        # Construct file paths for the CSV files
        matches_csv = os.path.join(dir2, 'Matches.csv')
        tolerances_csv = os.path.join(dir2, 'Tolerances.csv')
    
        # Load the 'Matches' CSV as df_main
        df_main = pd.read_csv(matches_csv, on_bad_lines="skip")
    
        # Load the 'Tolerances' CSV as df_tolerances
        df_tolerances = pd.read_csv(tolerances_csv)
        
        df_test = pd.read_csv(dir1)        
        # Dynamically find the 'Age' column in both datasets 
        age_column_main = next((col for col in df_main.columns if 'age' in col.lower()), None)
        age_column_test = next((col for col in df_test.columns if 'age' in col.lower()), None)  
        
        if not age_column_main or not age_column_test:  
            raise ValueError("Could not find 'Age' column in one or both datasets.") 
            
         # Map the relevant column names in the main dataset to match the test dataset columns 
        column_mapping_main = {
        'd13C': 'CaveCalc d13C','Mg/Ca': 'CaveCalc MgCa', 'DCP': 'CaveCalc DCP','d44Ca': 'CaveCalc d44Ca',
        'Sr/Ca': 'CaveCalc SrCa','Ba/Ca': 'CaveCalc BaCa','U/Ca': 'CaveCalc UCa', 'd18O': 'CaveCalc d18O'}  
               
        # Extract and format trace metal values 
        trace_metals = ['Mg', 'Sr', 'Ba', 'U', 'd44'] 
        bedrock_XCa_values = {metal: df_main.get(f'bedrock_{metal}Ca', pd.Series(dtype='float64')).dropna().unique() for metal in trace_metals}
        soil_XCa_values = {metal: df_main.get(f'soil_{metal}', pd.Series(dtype='float64')).dropna().unique() for metal in trace_metals}

        # Format trace metals correctly 
        format_XCa_text = lambda XCa_values, unit: ', '.join( 
            f"{metal}/Ca: {', '.join(map(str, values))} {unit}" if metal != 'd44' else f"{metal}: {', '.join(map(str, values))} ‰"
    for metal, values in XCa_values.items() if values.size > 0 and all(value != 0 for value in values)  
    )
    
        # Get formatted texts
        bedrock_XCa_text = format_XCa_text(bedrock_XCa_values, "mmol/mol")
        soil_XCa_text = format_XCa_text(soil_XCa_values, "mmol/kgw")
        
        # Initialize the dictionary to store extracted data and create plots  
        figures = []  
        
       # Initialize variables and labels
        variables = ['soil_d13C', 'soil_pCO2', 'cave_pCO2', 'd13C_init']
        custom_labels = {
            'soil_d13C': 'Soil d13C',
            'soil_pCO2': 'Soil gas pCO2 (ppmv)',
            'cave_pCO2': 'Cave air pCO2 (ppmv)',
            'd13C_init': 'd13C initial solution'
        }
        subplot_titles = [r'[A]', r'[B]', r'[C]', r'[D]']
        subtitles = [
            'Viable soil d13C, constrained by matches between modeled and measured CaCO3',
            'Viable soil gas pCO2, constrained by matches between modeled and measured CaCO3',
            'Viable cave air pCO2, constrained by matches between modeled and measured CaCO3',
            'd13C initial solution outputs from viable soil d13C, soil gas pCO2, and gas-to-water ratio'
        ]

        # Set up subplots
        num_vars = len(variables)
        num_cols = 2
        num_rows = int(np.ceil(num_vars / num_cols))
        fig, axs = plt.subplots(num_rows, num_cols, figsize=(15, 5 * num_rows))
        plt.subplots_adjust(hspace=0.25)
        axs = axs.flatten()

        # Loop through each variable and plot
        for i, var in enumerate(variables):
            if var in df_main.columns:
                age_values = df_main[age_column_main].dropna()
                var_values = df_main[var].dropna()
                
                # Group data by age for boxplot
                grouped_data = df_main.groupby(age_column_main)[var].apply(list)
                positions = np.arange(len(grouped_data))  # Create evenly spaced positions for the boxplots
                data_for_boxplot = grouped_data.tolist()
                
                # Compute box plot width and plot
                box_width = (positions.max() - positions.min()) / (len(positions) * 4)
                axs[i].boxplot(data_for_boxplot, positions=positions, widths=box_width, patch_artist=True,
                               boxprops=dict(facecolor='none', color='black'),
                               medianprops=dict(color='black'),
                               whiskerprops=dict(color='black'),
                               capprops=dict(color='black'),
                               flierprops=dict(marker='o', color='black', markersize=5),
                               showfliers=False)
                
                # Overlay scatter plot
                color, marker = ('darkblue', 's') if var == 'd13C_init' else ('darkgreen', 'o')
                # Map the actual age values to the new, evenly spaced positions 
                scatter_positions = np.interp(df_main[age_column_main], np.sort(age_values.unique()), positions)

                # Plot the scatter points with the adjusted positions
                axs[i].scatter(scatter_positions, df_main[var], marker=marker, color=color, s=50, label='Modeled Data')

               #  Set x-axis labels as the original age values
                axs[i].set_xticks(positions)
                axs[i].set_xticklabels(np.sort(age_values.unique()))

                # Titles and labels
                axs[i].set_xlabel('Age')
                axs[i].set_ylabel(custom_labels[var])
                axs[i].text(0.02, 1.01, subplot_titles[i], transform=axs[i].transAxes, fontsize=12, fontweight='bold', ha='center')
                
                # Subtitle handling with line breaks if necessary
                subtitle = subtitles[i]
                if len(subtitle) > 100:
                    first_line, second_line = subtitle[:100], subtitle[100:]
                    axs[i].text(0.05, 1.06, first_line, transform=axs[i].transAxes, fontsize=10, ha='left')
                    axs[i].text(0.05, 1.01, second_line, transform=axs[i].transAxes, fontsize=10, ha='left')
                else:
                    axs[i].text(0.05, 1.01, subtitle, transform=axs[i].transAxes, fontsize=10, ha='left')
            else:
                axs[i].axis('off')  # Turn off unused subplots
      
        # Add faint text to the top left corner and main title
        fig.text(0.013, 0.99, 'Produced by CaveCalcv2.0', ha='left', va='top', fontsize=10, color='black', alpha=0.5)
        fig.suptitle('CO2 Processes', fontsize=16, fontweight='bold', y=0.98)

        # Create and add custom legend
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='darkgreen', label='Model Inputs', markersize=10, linestyle='None'),
            Line2D([0], [0], marker='s', color='darkblue', label='Model Outputs', markersize=10, linestyle='None')
        ]
        fig.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 0.96), ncol=2, fontsize=12, frameon=False)

        # Position for the 'User miscellaneous input' heading
        fig.text(0.50, 0.90, 'User miscellaneous inputs', ha='center', va='center', fontsize=10, fontweight='bold')
        miscellaneous_values_y_position = 0.88

        # Load and filter input ranges
        input_ranges_df = pd.read_csv(os.path.join(dir2, 'Input_Ranges.csv'))
        miscellaneous_inputs = {'temperature': 'T', 'cave_pCO2': 'cave air pCO2'}

        # Display miscellaneous input ranges
        for input_var, label in miscellaneous_inputs.items():
            row = input_ranges_df[input_ranges_df['Variable'] == input_var]
            if not row.empty:
                fig.text(0.50, miscellaneous_values_y_position, f"{label}: ({row['Minimum'].values[0]} to {row['Maximum'].values[0]})", ha='center', va='center', fontsize=10)
                miscellaneous_values_y_position -= 0.025

        # Position for the 'User soil inputs' heading
        fig.text(0.20, 0.95, 'User soil inputs', ha='center', va='center', fontsize=10, fontweight='bold')
        soil_values_y_position = 0.93

        # Display soil input ranges
        soil_inputs = {'soil_pCO2': 'soil-gas pCO2', 'soil_d13C': 'd13Cₛₒᵢₗ'}
        for input_var, label in soil_inputs.items():
            row = input_ranges_df[input_ranges_df['Variable'] == input_var]
            if not row.empty:
                fig.text(0.20, soil_values_y_position, f"{label}: ({row['Minimum'].values[0]} to {row['Maximum'].values[0]})", ha='center', va='center', fontsize=10)
                soil_values_y_position -= 0.025

        # Display soil values
        for value in soil_XCa_text.split(', '):
            fig.text(0.20, soil_values_y_position, value, ha='center', va='center', fontsize=10)
            soil_values_y_position -= 0.025

        # Position for the 'Available measurements' heading
        fig.text(0.80, 0.95, 'Available measurements', ha='center', va='center', fontsize=10, fontweight='bold')
        available_measurements_y_position = 0.92
        num_columns, spacing_x, spacing_y = 3, 0.05, 0.025

        # Display available measurements
        column_mapping_main = {
            'd13C': 'CaveCalc d13C', 'Mg/Ca': 'CaveCalc MgCa', 'DCP': 'CaveCalc DCP', 'd44Ca': 'CaveCalc d44Ca',
            'Sr/Ca': 'CaveCalc SrCa', 'Ba/Ca': 'CaveCalc BaCa', 'U/Ca': 'CaveCalc UCa', 'd18O': 'CaveCalc d18O'
        }
        for index, (proxy, column) in enumerate(column_mapping_main.items()):
            x_position, y_position = 0.75 + (index % num_columns) * spacing_x, available_measurements_y_position - (index // num_columns) * spacing_y
            if column not in df_main.columns or df_main[column].isnull().all():
                fig.text(x_position, y_position, proxy, ha='center', va='center', fontsize=10)

        # Adjust subplot and add red rectangle around figure
        fig.subplots_adjust(left=0.05, right=0.95, top=0.77, bottom=0.10)
        rect_flow_path = patches.FancyBboxPatch(
            (0.05, 0.05), 0.90, 0.90, transform=fig.transFigure, boxstyle="round,pad=0.05", edgecolor='red', linewidth=5, fill=False
        )
        fig.patches.append(rect_flow_path)

       
        plt.show(block=False)
        figures.append(fig)
  
        
  
        
        # Plot for Flow Path Hydrology
        variables_flow_path = ['gas_volume', 'fCa']
        
        # Titles for the subplots [A], [B], [C], [D] 
        subplot_titles = [r'[A]', r'[B]'] 
        
        # Custom subtitles for each subplot 
        subtitles = [ 
            'Viable gas-to-water ratio, constrained by matches between modeled and measured CaCO3', 
            'Viable fca outputs constrained by matches between modeled and measured CaCO3'
   
        ]
        

        # Determine the number of rows and columns for the subplot grid
        num_cols_flow_path = 2  # Number of columns in the grid (including an extra column for d44Ca)
        num_rows_flow_path = 1  # One row for all subplots
    
        # Create a figure with a grid of subplots
        fig, axs_flow_path = plt.subplots(num_rows_flow_path, num_cols_flow_path, figsize=(18, 6)) 

        # Flatten the axs array for easy iteration if it's a 2D array
        axs_flow_path = axs_flow_path.flatten()  
        
        
    
        for i, var in enumerate(variables_flow_path):   
            if var in df_main.columns:  
                # Compute min and max values 
                age_values = df_main[age_column_main] 
                var_values = df_main[var] 

                # Prepare data for custom boxplot 
                data_for_boxplot = [] 
                for age in age_values.unique():   
                    age_mask = df_main[age_column_main] == age 
                    data_for_boxplot.append(var_values[age_mask]) 
                    

                # Group data by age for boxplot
                grouped_data = df_main.groupby(age_column_main)[var].apply(list)
                positions = np.arange(len(grouped_data))  # Create evenly spaced positions for the boxplots
                data_for_boxplot = grouped_data.tolist()
                
                # Compute box plot width and plot
                box_width = (positions.max() - positions.min()) / (len(positions) * 4)
                axs_flow_path[i].boxplot(data_for_boxplot, positions=positions, widths=box_width, patch_artist=True,
                               boxprops=dict(facecolor='none', color='black'),
                               medianprops=dict(color='black'),
                               whiskerprops=dict(color='black'),
                               capprops=dict(color='black'),
                               flierprops=dict(marker='o', color='black', markersize=5),
                               showfliers=False)
                
                # Custom box plot that spans the full range of data 
                for age in age_values.unique():  
                    age_mask = df_main[age_column_main] == age
                    age_min = var_values[age_mask].min()
                    age_max = var_values[age_mask].max() 
                    
                # Overlay scatter plot on top of the custom box plot
                color = 'darkgreen' if var == 'gas_volume' else 'darkblue'  # Use dark green for gas volume
 
                # Set marker to 's' only for fca, otherwise 'o' 
                if var == 'fCa' :
                    marker = 's'
                else:
                    marker = 'o'
                
                # Map the actual age values to the evenly spaced positions 
                scatter_positions = np.interp(df_main[age_column_main], np.sort(age_values.unique()), positions) 
                
                # Plot the scatter points with the adjusted positions 
                axs_flow_path[i].scatter(scatter_positions, df_main[var], marker=marker, color=color, s=50, label='Modeled Data') 
                
                # Set x-axis labels as the original age values 
                axs_flow_path[i].set_xticks(positions) 
                axs_flow_path[i].set_xticklabels(np.sort(age_values.unique()))

                axs_flow_path[i].set_xlabel('Age')
                # Set the y-label with the specific changes for gas volume and fca 
                if var == 'gas volume (L/kg)':  
                    axs_flow_path[i].set_ylabel('gas-to-water ratio (L/kg)')  # Updated label 
                elif var == 'fCa': 
                        axs_flow_path[i].set_ylabel('fCa')  # Updated label for f_c 
                else:  
                    axs_flow_path[i].set_ylabel(var)
                
                # Corrected title plotting line 
                axs_flow_path[i].text(0.02, 1.01, subplot_titles[i], transform=axs_flow_path[i].transAxes,  
                                      fontsize=12, fontweight='bold', ha='center')
                
                
            
                # Add custom subtitle for each subplot
                subtitle = subtitles[i]  # Get the corresponding subtitle
                max_length = 70  # Define a character limit before breaking into two lines   
                if len(subtitle) > max_length:   
                    # Split the subtitle into two parts  
                    first_line = subtitle[:max_length] 
                    second_line = subtitle[max_length:] 
            
                    # Display the first line at the usual position 
                    axs_flow_path[i].text(0.05, 1.04, first_line, transform=axs_flow_path[i].transAxes,  
                                          fontsize=10, fontweight='normal', ha='left') 
                    
                    # Display the second line slightly lower to avoid overlap 
                    axs_flow_path[i].text(0.05, 1.00, second_line, transform=axs_flow_path[i].transAxes,  
                                          fontsize=10, fontweight='normal', ha='left')  
                else:  
                    # If subtitle is short, display it on a single line   
                    axs_flow_path[i].text(0.05, 1.01, subtitle, transform=axs_flow_path[i].transAxes,  
                                          fontsize=10, fontweight='normal', ha='left')
                                        

        #Add a blue rectangle around the entire figure
        fig.subplots_adjust(left=0.08, right=0.92, top=0.79, bottom=0.13)
        # Create a FancyBboxPatch instead of Rectangle 
        rect_flow_path = patches.FancyBboxPatch( 
            (0.05, 0.05), 0.9, 0.9,  # (x, y, width, height) in figure coordinates 
            transform=fig.transFigure,  # Use figure coordinates 
            boxstyle="round,pad=0.05",  # You can adjust padding here 
            edgecolor='blue',  # Border color 
            linewidth=5,  # Border widt 
            fill=False  # No fill, just the border 
            ) 
        # Add the patch to the figure 
        fig.patches.append(rect_flow_path) 
        
       
         #Set the main title 
        fig.suptitle('Flow Path Controls', fontsize=16, fontweight='bold',y=0.98) 
        
        # Define handles and labels for the legend  
        handles = [plt.Line2D([0], [0], marker='o', color='darkgreen', linestyle='None', markersize=10), 
                   plt.Line2D([0], [0], marker='s', color='darkblue', linestyle='None', markersize=10)]
        labels = ['Model inputs', 'Model ouputs'] 
        
        fig.legend(handles, labels, loc='lower center', ncol=3, fontsize=10, bbox_to_anchor=(0.5, 0.90),frameon=False)
                                
        

                
        # Add faint text to the top left corner 
        fig.text(0.013, 0.99, 'Produced by CaveCalcv2.0', ha='left', va='top', fontsize=10, color='black', alpha=0.5) 
        
        fig.text(0.235, 0.96, 'User bedrock inputs', ha='center', va='center', fontsize=10, fontweight='bold')  
        bedrock_values_y_position = 0.94 
        
        # Split bedrock values into two columns 
        bedrock_values = bedrock_XCa_text.split(', ') 
        num_values = len(bedrock_values)
        num_per_column = (num_values + 1) // 2  # Distribute roughly evenly across two columns 
         
        for index, value in enumerate(bedrock_values):   
            col = index // num_per_column  # Determine column (0 or 1) 
            row = index % num_per_column  # Determine row position within the column 
            x_pos = 0.17 + col * 0.12  # Adjust x-position for two columns 
            y_pos = bedrock_values_y_position - row * 0.025 
            fig.text(x_pos, y_pos, f"{value}", ha='center', va='center', fontsize=10, color='black') 
            
        # Add gas_volume under bedrock inputs   
        row = input_ranges_df[input_ranges_df['Variable'] == 'gas_volume']    
        if not row.empty:     
            # Update the annotation to reflect 'gas-to-water ratio'  
            variable_text = f"gas-to-water ratio: ({row['Minimum'].values[0]} to {row['Maximum'].values[0]})"   
            fig.text(0.20, bedrock_values_y_position - (num_per_column + 1) * 0.025, variable_text, ha='center', va='center', fontsize=10, color='black') 

        
        # Position for the 'Available measurements' heading 
        fig.text(0.80, 0.96, 'Available measurements', ha='center', va='center', fontsize=10, fontweight='bold')  # Adjusted y-position for heading 
        available_measurements_y_position = 0.93
        num_columns = 3  # Number of columns for annotations 
        spacing_x = 0.05  # Horizontal spacing between columns 
        spacing_y = 0.025  # Vertical spacing between rows
        
        # Map the relevant column names in the main dataset to match the test dataset columns  
        column_mapping_main = {
    'd13C': 'CaveCalc d13C',
    'Mg/Ca': 'CaveCalc MgCa',
    'DCP': 'CaveCalc DCP',
    'd44Ca': 'CaveCalc d44Ca',
    'Sr/Ca': 'CaveCalc SrCa',
    'Ba/Ca': 'CaveCalc BaCa',
    'U/Ca': 'CaveCalc UCa',
    'd18O': 'CaveCalc d18O' 
         } 
    
        # Loop through the column mapping  
        for index, (proxy, column) in enumerate(column_mapping_main.items()): 
            # Calculate row and column position 
            row_index = index // num_columns 
            col_index = index % num_columns

            # Calculate x and y positions 
            x_position = 0.75 + col_index * spacing_x 
            y_position = available_measurements_y_position - row_index * spacing_y

            if column not in df_main.columns or df_main[column].isnull().all(): 
                # If the column is missing or all values are NaN, annotate that the data is unavailable  
                fig.text(x_position, y_position, f"{proxy}", ha='center', va='center', fontsize=10, color='black') 

        
        plt.show(block=False) 
        figures.append(fig) 
 
        
        outputs_csv = os.path.join(dir2, 'All_outputs.csv')
 
        df_all_outputs = pd.read_csv(outputs_csv)
        df_all_outputs = df_all_outputs[df_all_outputs['CaveCalc d13C'] != -999]
        relative_offset_fraction = 0.05  # Adjust this value to control the offset proportionally 
        

        # Strip, lowercase, and remove non-alphanumeric characters from column names, except for the first column (assumed to be 'age') 
        df_test.columns = [df_test.columns[0]] + df_test.columns[1:].str.strip().str.lower().str.replace(r'[^a-z0-9]', '', regex=True).tolist()


        
        # Map the relevant column names in the main dataset to match the test dataset columns 
        column_mapping_main = {
       'd13c': 'CaveCalc d13C','mgca': 'CaveCalc MgCa', 'dcp': 'CaveCalc DCP','d44ca': 'CaveCalc d44Ca',
       'srca': 'CaveCalc SrCa','baca': 'CaveCalc BaCa','uca': 'CaveCalc UCa', 'd18o': 'CaveCalc d18O'}  
       
        
        # Define the number of columns and rows for the subplots
        num_cols_comparisons = 2  # Number of columns for the comparison plots
        num_rows_comparisons = int(np.ceil(len(column_mapping_main) / num_cols_comparisons))  # Calculate the number of rows needed

        # Create a figure with subplots for each valid comparison  
        fig, axs_comparisons = plt.subplots(num_rows_comparisons, num_cols_comparisons, figsize=(15, 5 * num_rows_comparisons))  
        
        # Adjust the spacing between su[,p;bplots 
        plt.subplots_adjust(hspace=0.40)  # Adjust wspace for horizontal space, hspace for vertical space

        # Flatten the axs array for easy iteration if it's a 2D array  
        axs_comparisons = axs_comparisons.flatten() 
               
        # Define a dictionary for axis labels 
        axis_labels = { 
            'd13c': 'd13C$_{CaCO3}$ (‰, VPDB)', 
            'd18o': 'd18O$_{CaCO3}$ (‰, VPDB)', 
            'd44ca': 'd44Ca$_{CaCO3}$ (‰)', 
            'mgca': 'Mg/Ca$_{CaCO3}$ (mmol/mol)', 
            'dcp': 'DCP$_{CaCO3}$ (%)', 
            'srca': 'Sr/Ca$_{CaCO3}$ (mmol/mol)', 
            'baca': 'Ba/Ca$_{CaCO3}$ (mmol/mol)',
            'uca': 'U/Ca$_{CaCO3}$ (mmol/mol)' 
            }
        
        df_main = df_main[df_main['CaveCalc d13C'] != -999]

     
        
        
        for i, (key, mapped_col) in enumerate(column_mapping_main.items()):   
            ax = axs_comparisons[i] 
        
            
            if mapped_col in df_main.columns and key in df_test.columns: 
                # Convert both the key and 'Proxies' values to lowercase for comparison
                tolerance_row = df_tolerances[df_tolerances['Proxy'].str.lower() == key.lower()]

                if not tolerance_row.empty: 
                    tolerance_value = tolerance_row['Tolerance Value'].values[0]
                else: 
                    tolerance_value = 0  # Default if no tolerance is found
               
                # Custom box plot that spans the full range of data
                for age in df_main[age_column_main].unique():   
                    age_mask = df_main[age_column_main] == age 

                # Get all unique ages across df_main, df_test, and df_all_outputs 
                unique_ages = np.sort( 
                    np.unique( 
                        np.concatenate((df_main[age_column_main].unique(), 
                        df_test[age_column_test].unique(), 
                        df_all_outputs[age_column_main].unique()))) 
                    ) 
                
                # Create evenly spaced positions for the boxplots and scatter points 
                positions = np.arange(len(unique_ages)) 
                
                # Map the ages to their respective positions 
                scatter_positions_main = np.searchsorted(unique_ages, df_main[age_column_main]) 
                scatter_positions_test = np.searchsorted(unique_ages, df_test[age_column_test]) + relative_offset_fraction 
                scatter_positions_all_outputs = np.searchsorted(unique_ages, df_all_outputs[age_column_main]) - relative_offset_fraction 
                
                # Plot modeled data (df_main) only where available 
                if mapped_col in df_main.columns: 
                    ax.scatter(scatter_positions_main, df_main[mapped_col], marker='o', color='darkgreen', s=100, label=f'Modeled {key}') 
                    
                # Always plot measured data (df_test)  
                ax.scatter(scatter_positions_test, df_test[key], marker='s', color='black', s=100, label=f'Measured {key}') 
                
                # Always plot all outputs (df_all_outputs) if the column exists 
                if mapped_col in df_all_outputs.columns: 
                    ax.scatter(scatter_positions_all_outputs, df_all_outputs[mapped_col], marker='o', color='black', s=80, label=f'Output {key}', alpha=0.7) 
                    
                # Add vertical lines with ± tolerance for each measured data point 
                for j, age in enumerate(df_test[age_column_test]): 
                    ax.vlines(x=scatter_positions_test[j], ymin=df_test[key][j] - tolerance_value, ymax=df_test[key][j] + tolerance_value, color='black', linestyles='--')
               
              
        
            else:    
                # Define specific messages for certain keys 
                if key == 'baca':  
                    message = 'No Ba/Ca data provided' 
                elif key == 'dcp':
                    message = 'No DCP data provided'
                elif key == 'mgca': 
                    message = 'No Mg/Ca data provided' 
                elif key == 'srca': 
                    message = 'No Sr/Ca data provided' 
                elif key == 'uca': 
                    message = 'No U/Ca data provided' 
                else: 
                    message = f'No {key} data provided' 
                    
                # Add the message to the empty plot 
                ax.text(0.5, 0.5, message, horizontalalignment='center', verticalalignment='center', transform=ax.transAxes, fontsize=12, color='black')
            
            # Set x-axis labels as the original age values 
            ax.set_xticks(positions)  # Ensure the number of tick positions matches unique_ages 
            ax.set_xticklabels(unique_ages, rotation=45)  # Ensure equal labels for each tick
            ax.set_xlabel('Age')
            ax.set_ylabel(axis_labels.get(key, key), fontsize=10)    
            
        # Ensure any extra subplots are turned off
        for j in range(len(column_mapping_main), len(axs_comparisons)):  
            axs_comparisons[j].axis('off')          
            
        # Add a black rectangle around the entire figure 
        fig.subplots_adjust(left=0.05, right=0.95, top=0.80, bottom=0.07)
        rect_flow_path = patches.FancyBboxPatch(  
                (0.05, 0.05), 0.9, 0.9,  # (x, y, width, height) in figure coordinates  
                transform=fig.transFigure,  # Use figure coordinates  
                boxstyle="round,pad=0.05",  # You can adjust padding here  
                edgecolor='black',  # Border color  
                linewidth=5,  # Border widt  
                fill=False  # No fill, just the border  
                ) 
            
        # Add the patch to the figure 
        fig.patches.append(rect_flow_path)  
            
        # Collect unique handles and labels for the legend 
        handles = [] 
        labels = [] 
        for ax in axs_comparisons: 
            for h, l in zip(*ax.get_legend_handles_labels()): 
                if l not in labels:  # Add only if the label hasn't been added before 
                      handles.append(h) 
                      labels.append(l)
            
        # Set the main title for flow path hydrology 
        fig.suptitle('Model-Data comparison', fontsize=16, fontweight='bold', y=0.99)     
            
        # Define handles and labels for the legend  
        handles = [plt.Line2D([0], [0], marker='o', color='black', linestyle='None', markersize=10),
                   plt.Line2D([0], [0], marker='o', color='darkgreen', linestyle='None', markersize=10), 
                   plt.Line2D([0], [0], marker='s', color='black', linestyle='None', markersize=10),
                   plt.Line2D([0], [1], color='black', linestyle='--', lw=2)  ]  
        labels = ['All modeled data', 'Matched modeled Data', 'Measured Data','Tolerance Interval'] 
                       
        # Add text for headings and content, placing them horizontally 
        #fig.text(0.1, 1, 'Data', ha='center', va='center', fontsize=14, fontweight='bold') 
        fig.legend(handles, labels, loc='lower center', ncol=3, fontsize=10, bbox_to_anchor=(0.5, 0.92),frameon=False)
        
        # Add faint text to the top left corner 
        fig.text(0.013, 0.99, 'Produced by CaveCalcv2.0', ha='left', va='top', fontsize=10, color='black', alpha=0.5)
        
        # Position for the 'User miscellaneous input' heading 
        fig.text(0.80, 0.91, 'User miscellaneous inputs', ha='center', va='center', fontsize=10, fontweight='bold') 
        miscellaneous_values_y_position = 0.889
        
        
        
        # Filter for specific miscellaneous inputs with custom labels 
        miscellaneous_inputs = {'temperature': 'T', 'cave_pCO2': 'cave air pCO2'} 
        for input_var, label in miscellaneous_inputs.items(): 
            row = input_ranges_df[input_ranges_df['Variable'] == input_var] 
            if not row.empty: 
                variable_text = f"{label}: ({row['Minimum'].values[0]} to {row['Maximum'].values[0]})" 
                fig.text(0.80, miscellaneous_values_y_position, variable_text, ha='center', va='center', fontsize=10, color='black') 
                miscellaneous_values_y_position -= 0.025  # Adjust position for next input 
                
        # Position for the 'User bedrock inputs' heading 
        fig.text(0.50, 0.91, 'User bedrock inputs', ha='center', va='center', fontsize=10, fontweight='bold') 
        bedrock_values_y_position = 0.89  
        
        # Split bedrock values into two columns  
        bedrock_values = bedrock_XCa_text.split(', ')  
        
        # Add gas-to-water ratio if available 
        row = input_ranges_df[input_ranges_df['Variable'] == 'gas_volume']  
        if not row.empty:    
            gas_text = f"gas-to-water ratio: ({row['Minimum'].values[0]} to {row['Maximum'].values[0]})" 
            bedrock_values.append(gas_text)  # Add gas-to-water ratio to the list 
            
            num_values = len(bedrock_values)  
            num_per_column = (num_values + 1) // 2  # Distribute roughly evenly across two columns  
            
        for index, value in enumerate(bedrock_values):    
            col = index // num_per_column  # Determine column (0 or 1) 
            row = index % num_per_column  # Determine row position within the column 
            x_pos = 0.42 + col * 0.12  # Adjust x-position for two columns 
            y_pos = bedrock_values_y_position - row * 0.025 
            fig.text(x_pos, y_pos, f"{value}", ha='center', va='center', fontsize=10, color='black') 
        
    
        # Position for the 'User soil inputs' heading 
        fig.text(0.20, 0.91, 'User soil inputs', ha='center', va='center', fontsize=10, fontweight='bold') 
        soil_values_y_position = 0.89
                    
        # Display soil X/Ca values and additional soil inputs with custom labels 
        soil_inputs = {'soil_pCO2': 'soil-gas pCO2', 'soil_d13C': 'd13Cₛₒᵢₗ'}  # Custom labels with subscript 
        for input_var, label in soil_inputs.items(): 
            row = input_ranges_df[input_ranges_df['Variable'] == input_var] 
            if not row.empty:  
                variable_text = f"{label}: ({row['Minimum'].values[0]} to {row['Maximum'].values[0]})" 
                fig.text(0.20, soil_values_y_position, variable_text, ha='center', va='center', fontsize=10, color='black') 
                soil_values_y_position -= 0.025  # Adjust position for next input

            
        # Display soil values 
        for index, value in enumerate(soil_XCa_text.split(', ')):  
            fig.text(0.20, soil_values_y_position, f"{value}", ha='center', va='center', fontsize=10, color='black')
            soil_values_y_position -= 0.025  # Adjust position for next input
                   
            
        
        plt.show(block=False) 
        figures.append(fig) 
            
        return figures

   
 
    
      
