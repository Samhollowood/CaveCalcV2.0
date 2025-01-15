"""Allows multiple models to be run in sequence and handles model IO. For most
use-cases, cavecalc Models should be run using the ForwardModels class.

Classes defined here:
    ForwardModels
    
Functions defined here:
    run_a_model
    run_async
    run_linear
"""

# built-in modules
import os
import pandas as pd
import multiprocessing as mp
import pickle
# my modules
import cavecalc.caves as ccv
import cavecalc.util as ccu
from cavecalc.setter import SettingsObject, SettingsMaker
from copy import deepcopy
import gc
import cavecalc.analyse as cca

def run_a_model(SO):
    """Run a single cavecalc model.
    
    Args:
        SO (SettingsObject): A SettingsObject describing model input.
    Returns:
        (r, id) where r is the model results dict and id is the 'id' parameter
        in settings. If the model raises an error, (None, id) is returned.
    """
    
    i = SO.id
    sim = ccv.Simulator(SO.dict(), i)
    r = sim.run()
    print("Model %i complete." % i)
    del sim
    gc.collect()  # Manually trigger garbage collection to free memory
    return (r, i)
        
def run_async(SO_list):
    """Run multiple models in parallel.
    
    WARNING: Parallel processing may cause errors in some calculations. Use
    only when absolutely necessary. run_linear() is recommended instead.
    
    Args:
        SO_list: A list SettingsObjects, e.g. from a SettingsMaker
    Returns:
        A list of (r, id) tuples. r is the model results dict and id is the 
        'id' parameter in the settings dict.
    """
    
    s = SO_list
    results = {}
    pool = mp.Pool()
    results = [pool.apply_async(run_a_model, (e.dict(), e.id)) for e in s]
    pool.close()
    pool.join()
    r = [res.get() for res in results]
    r2 = sorted(r, key=lambda tup: tup[1]) # sort by model id
    return r2
    
def run_linear(SO_list):
    """Runs multiple models in sequence.
    
    Args:
        SO_list: A list SettingsObjects, e.g. from a SettingsMaker
    Returns:
        A list of (r, id) tuples. r is the model results dict and id is the 
        'id' parameter in the settings dict.
    """    
    
    return [run_a_model(e) for e in SO_list]


class ForwardModels(object):
    """Runs Cavecalc models.
    
    Handles generation and checking of settings suites, and saving of bundled
    model output. This class provides a flexible interface to cavecalc.caves 
    (the module which actually runs the models), and is the preferred method 
    of running models.
    """
    
    def __init__(self, settings=None, output_dir=None):
        """Initialise the object and process settings.
        
        Args:
            settings (SO): Model input parameters. See defaults.txt for 
                             options.
            settings_file: If no settings arg is given, settings may be loaded
                           from a file.
            output_dir: (Optional) Specify path to directory for saving files.
                        By default files are saved to the current directory.
        """
        
        self.done_input = []
        self.done_results = []
        
        # Get settings objects
        if settings:    self.input = SettingsMaker(**settings).settings()
        else:           self.input = SettingsMaker().settings()
            
        if output_dir:  
            if not os.path.isdir(output_dir): 
                os.mkdir(output_dir)
            self.output_dir = output_dir
        else: self.output_dir=os.getcwd()

    def _check_previous_saves(self, interactive=False, use_by_default=True):
        """Checks output directory for existing output and prompts the user
        to decide whether they want to use it or not."""
        
        
        def dict_find(SO, list_of_SOs):
        
            for i,s in enumerate(list_of_SOs):
            
                # check keys are equal
                if SO.dict().keys() != s.dict().keys():
                    continue
                    
                # check all values are equal
                equal = True
                for k,v in SO.dict().items():
                    if v != s.dict()[k]:
                        equal = False
                if equal:
                    return i
            return None 
        
        try:
            with open(os.path.join(self.output_dir, 'settings.pkl'), 'rb') as f:
                prev_input = pickle.load(f)
                
            with open(os.path.join(self.output_dir, 'results.pkl'), 'rb') as f:
                prev_results = pickle.load(f)
        except FileNotFoundError:
            return

        if (prev_input is None) or (prev_results is None):
            return
        
        new_input = []
        done_input = []
        done_results = []
        
        # for i,prev in enumerate(prev_inputs):
        for s in self.input:
            i = dict_find(s, prev_input)
            if i is None:
                new_input.append(s)
            else:
                done_input.append(prev_input[i])
                done_results.append(prev_results[i])

        print("Previous model output detected for selected input settings.")
        
        if interactive == True:
            a = ''
            while a == '':
                print( "%i out of %i models appear to be repeated." % 
                       (len(done_input), len(self.input)))
                a = input("Re-use old output for these models (y/n)? ")
                if a.capitalize() == 'Y':
                    reuse = True
                elif a.capitalize() == 'N':
                    reuse = False
                else:
                    a = ''
                
        else:
            print("%i out of %i models are repeats." % 
                       (len(done_input), len(self.input)))
            if use_by_default:
                print("Re-using old calculations where available.")
            else:
                print("Re-running all models")
            reuse = use_by_default
        
        if reuse:
            self.input = new_input
            self.done_input = done_input
            self.done_results = done_results
    
    def run_models(self, mode='Serial', **kwargs):
        """Run models for all parameter sets loaded into the object. Output is
        addded to self.results as a list of (r, id) tuples. See run_linear and
        run_async for method. Parallel mode is not currently functional (on
        Windows at least).
        
        Args:
            mode: 'Serial' (default) or 'Parallel'. Running models in parallel
                  is faster but not recommended - results may be inaccurate, as
                  Iphreeqc is not necessarily thread-safe in this 
                  implementation.
        Returns:
            Nothing. Model results list is assigned to self.results. List 
            indices in self.results correspond to indices in self.self.input.
        """

        self._check_previous_saves(**kwargs)
        ret_dir = os.getcwd()
        print("Models to run:\t%s" % len(self.input))
        try:
            os.chdir(self.output_dir)
            if mode.capitalize() == 'Serial': # Run models in order
                results = run_linear(self.input)
            elif mode.capitalize() == 'Parallel': # Run models multithreaded
                print("Warning: Parallel operation accuracy not guaranteed.")
                results = run_async(self.input)
            else:
                raise ValueError("Mode not recognised. Use serial / parallel")
            self.results = results
            
            
            # add re-used output, if any
            self.results.extend(self.done_results)
            self.input.extend(self.done_input)
            
        finally:
            os.chdir(ret_dir)
            
  
            
    def save(self):
        """Save results and settings data to .pkl files. 
        
        The resulting files (results.pkl and settings.pkl) may be read using 
        the cavecalc.analyse module.
        
        results.pkl contains a list of dicts. Each dict contains the output of
        a single model. settings.pkl contains a similar list of 
        SettingsObjects, one for each model run.
        """
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        with open(os.path.join(self.output_dir, 'settings.pkl'), 'wb') as f:
            pickle.dump(self.input, f)
            
        with open(os.path.join(self.output_dir, 'results.pkl'), 'wb') as f:
            pickle.dump(self.results, f)
            
            # Extract user_filepath from input settings
        extracted_values = {}
        for setting in self.input:
            if hasattr(setting, "dict"):  # Ensure the object has a dict method
                setting_dict = setting.dict()
                extracted_values['user_filepath'] = setting_dict.get('user_filepath')
        
        # Check if user_filepath exists and is a string
        user_filepath = extracted_values.get('user_filepath')
        if isinstance(user_filepath, str):
            try:
                # Perform additional logic for cavecalc.analyse
                e = cca.Evaluate()
                dir1 = user_filepath
                dir2 = os.path.join(self.output_dir,'CDA Results')  # Example for dir2
                plot = e.plot_CDA(dir1, dir2)
                print("Plotting completed successfully.")

            
           
    

        
    def _debug(self, i):
        """Runs the specified model and saves the pq_input_log file for 
        debugging. The input log file may be run directly by PHREEQC.
        
        Args:
            i: Index position in self.input to re-run in debug mode.
        """
        s_debug = self.input[i]
        s_debug.set(phreeqc_log_file=True)
        
        dbug = ccv.Simulator(s_debug, id=i)
        dbug.run()
 
'''      
    def Stal_save(self, excel_filename='model_outputs.xlsx'):
        """Extracts the last index of each key (variable) from the model outputs,
        as well as the settings, and saves them into an Excel file with two sheets.
        
        Args:
            excel_filename (str): The name of the Excel file to save the results to.
                                  Defaults to 'model_output.xlsx'.
        Returns:
            None. The data is saved to an Excel file in the specified directory.
        """

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        with open(os.path.join(self.output_dir, 'settings.pkl'), 'wb') as f:
            pickle.dump(self.input, f)
            
        with open(os.path.join(self.output_dir, 'results.pkl'), 'wb') as f:
            pickle.dump(self.results, f)

        # Load the results from the saved pickle file
        results_path = os.path.join(self.output_dir, 'results.pkl')
        if not os.path.exists(results_path):
            raise FileNotFoundError(f"No results file found at {results_path}. Run models and save results before extracting values.")
        
        with open(results_path, 'rb') as f:
            results = pickle.load(f)

        # Load the settings from the saved pickle file
        settings_path = os.path.join(self.output_dir, 'settings.pkl')
        if not os.path.exists(settings_path):
            raise FileNotFoundError(f"No settings file found at {settings_path}. Run models and save settings before extracting values.")
        
        with open(settings_path, 'rb') as f:
            settings = pickle.load(f)

        # Extract the last values from each model's output
        last_values = []
        for model_output in results:
            model_dict = model_output[0]
            model_last_values = {key: values[-1] for key, values in model_dict.items()}
            last_values.append(model_last_values)
        results_df = pd.DataFrame(last_values)
        results_df.insert(0, 'Model', [f'{i+1}' for i in range(len(last_values))])

        # Extract the settings from each SettingsObject
        settings_list = []
        for setting in settings:
            settings_dict = setting.dict()  # Assuming `dict()` method exists for SettingsObject
            settings_list.append(settings_dict)
        settings_df = pd.DataFrame(settings_list)
        settings_df.insert(0, 'Model', [f'{i+1}' for i in range(len(settings_list))])

        # Save both DataFrames to separate sheets in the same Excel file
        excel_path = os.path.join(self.output_dir, excel_filename)
        with pd.ExcelWriter(excel_path) as writer:
            settings_df.to_excel(writer, sheet_name='Settings', index=False)
            results_df.to_excel(writer, sheet_name='Results', index=False)
        
              

        print(f"Excel file '{excel_filename}' has been created successfully with 'Settings' and 'Results' sheets in the directory '{self.output_dir}'.")
        
'''


'''
          
    def rainfall_calculator(self):
        """Extracts specific settings and loads user file to perform rainfall calculations.
        
        Returns:
            dict: A dictionary containing extracted values for 'bedrock_d44Ca',
                  'd44Ca_modern', 'rainfall_amount', 'user_filepath', 'data', 'rs', and 'f_paleo'.
        """
        # Initialize a dictionary to hold the extracted values
        extracted_values = {
            'bedrock_d44Ca': None,
            'd44Ca_modern': None,
            'rainfall_amount': None,
            'user_filepath': None,  # To hold the user's file path
            'data': None            # To hold the loaded data from the user file
        }

        # Loop through the input settings to find the required settings
        for setting in self.input:
            setting_dict = setting.dict()

            # Extract the user_filepath and other required settings
            extracted_values['user_filepath'] = setting_dict.get('user_filepath')
            extracted_values['bedrock_d44Ca'] = setting_dict.get('bedrock_d44Ca')
            extracted_values['d44Ca_modern'] = setting_dict.get('d44Ca_modern')
            extracted_values['rainfall_amount'] = setting_dict.get('rainfall_amount')
            extracted_values['database'] = setting_dict.get('database')
            extracted_values['precipitate_mineralogy'] = setting_dict.get('precipitate_mineralogy')
            extracted_values['temperature'] = setting_dict.get('temperature')
            output_dir = setting_dict.get('out_dir')  # Output directory
            # If output_dir is provided, use it; otherwise, default to the current working directory 
            output_dir = output_dir or os.getcwd()
            extracted_values['out_dir'] = output_dir  # Store it in extracted_values


        # Load the user's time-series Excel file if a filepath is provided
        if extracted_values['user_filepath']:
            try:
                # Load the Excel file
                df = pd.read_excel(extracted_values['user_filepath'])
                # Strip whitespace from the headers and normalize column names by removing special characters
                df.columns = df.columns.str.strip().str.lower().str.replace(r'[^a-z0-9]', '', regex=True)

                # Extract relevant columns
                age_column = [col for col in df.columns if 'age' in col]
                d44Ca_column = [col for col in df.columns if 'd44ca' in col]

                # Collect data from the first found column or set to None if not found
                extracted_values['data'] = {
                    'age_data': df[age_column[0]].dropna().tolist() if age_column else None,
                    'd44Ca_data': df[d44Ca_column[0]].dropna().tolist() if d44Ca_column else None,
                }

            except Exception as e:
                raise ValueError(f"Error loading file: {e}")

        # Check if any required settings were not found and raise an error
        missing_keys = [key for key, value in extracted_values.items() if value is None]
        if missing_keys:
            raise ValueError(f"The following settings were not found in the input settings: {', '.join(missing_keys)}")

        # Create a database reader instance
        db = ccu.DBReader(str(extracted_values['database']))

        # Calculate alpha based on the precipitate mineralogy
        if extracted_values['precipitate_mineralogy'] == 'Calcite':
            alpha = db.get_alpha('44Ca', r'Calcite/Ca(aq)', extracted_values['temperature'] + 273.15)
        elif extracted_values['precipitate_mineralogy'] == 'Aragonite':
            alpha = db.get_alpha('44Ca', r'Aragonite/Ca(aq)', extracted_values['temperature'] + 273.15)
        else:
            raise ValueError("Invalid precipitate mineralogy specified.")

        # Calculate the rs values based on d44Ca_data
        if extracted_values['data']['d44Ca_data'] is not None:
            d44Ca_data = extracted_values['data']['d44Ca_data']
            rs = [(d44Ca / 1000) + 1 for d44Ca in d44Ca_data]  # Store the rs values

            # Calculate f_paleo as an array based on rs values and alpha
            ro = extracted_values['bedrock_d44Ca'] / 1000 + 1  
            f_paleo = [(r / (alpha * ro)) ** (1 / (alpha - 1)) for r in rs]

            r_modern = extracted_values['d44Ca_modern']/1000 + 1
            # Calculate f_modern using d44Ca_modern
            f_modern = (r_modern / (alpha * ro)) ** (1 / (alpha - 1))

            # Calculate rainfall_paleo using the extracted rainfall amount
            rainfall_paleo = [(extracted_values['rainfall_amount'] * f) / f_modern for f in f_paleo]

            # Update extracted_values with calculated rs, f_paleo, f_modern, and rainfall_paleo
            extracted_values['rs'] = rs
            extracted_values['f_paleo'] = f_paleo
            extracted_values['f_modern'] = f_modern
            extracted_values['rainfall_paleo'] = rainfall_paleo
            
            # Prepare DataFrame for output
            output_df = pd.DataFrame({
               'age': extracted_values['data']['age_data'],
               'd44Ca_data': d44Ca_data,
               'f_paleo': f_paleo,
               'rainfall_paleo': rainfall_paleo
            })

            # Ensure the output directory exists
            if not os.path.exists(extracted_values['out_dir']):
                os.makedirs(extracted_values['out_dir'])

            # Define the output file path
            output_file = os.path.join(extracted_values['out_dir'], 'rainfall_calculator.xlsx')

            # Write DataFrame to an Excel file
            output_df.to_excel(output_file, index=False, sheet_name='Rainfall Calculations')

            print(f"Output written to {output_file}")
 '''
