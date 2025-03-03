"""Cavecalc module for utility functions and classes.

Contains code to perform file IO, model output post-processing and various
other helpful bits.
"""

import os
import datetime
import math
import pickle
import pandas as pd
import csv
import re
from collections import OrderedDict
from copy import copy
import numpy as np
import scipy.io as sio
import cavecalc.data

class DBReader(object):
    """Reads data from the PHREEQC database file.
    
    DBReader objects are used to extract out database information (e.g. 
    partition coefficients and fractionation factors) that may be needed in
    geochemical calculations coded in caves.py. Thermodynamic parameters are
    not hard-coded into Cavecalc python files.
    
    DBReader objects cache use regular expressions to parse the database file 
    and cache data extracted to improve performance on repeated requests.
    
    Selected Methods:
        get_k_values - get phase definition thermodynamic data
        get_1000lnalpha - get an isotope fractionation factor
        get_alpha - get an isotope fractionation factor
        get_iso_stnd - get the absolute isotope ratio in a standard
    """
    
    def __init__(self, database):
        """Initialise the object.
        
        Args:
            database (str): location of phreeqc database filename.
        """
        
        db_dir = os.path.dirname(cavecalc.data.__file__)
        self.db = os.path.join(db_dir,database)
        
        self.alphas = {}
        self.thermo = {}
        
    def _cc(self, line):
        return line.split('#')[0]
        
    def _database_eval(self, equation, temperature): 
        """Evaluate a database expression for a fractionation factor or
        partition coefficent.
        
        Args:
            equation (list): A list of coefficents for a PHREEQC thermodynamic
                            parameter.
            temperature: Temperature (degrees K) at which to evaluate the
                            equation.
        Returns:
            Value of the expression at the given temperature
        """
        T = temperature
        a = equation
        
        coeffs = [1, T, 1/T, math.log10(T), 1/(T*T), T*T]        
        evaluation = 0
        for i in range(len(a)):
            evaluation += float(a[i])*float(coeffs[i])   # compute 1000ln_alpha
        return evaluation
            
    def _phase_lookup(self, reactants_list):
        
        r = r' \+ '.join(reactants_list)
        rc1 = re.compile(r"\s*?{}\s*=".format(r))
            
        out = []
        
        with iter(open(self.db, 'r')) as f:
            for line in f:
                if re.match(rc1, line):
                    line = next(f)
                    while line.strip() not in ('', '#'):
                        a = self._cc(line.strip()).split()
                        out.append(copy(a))
                        line = next(f)
                    return [o for o in out if o]
        raise Exception("No PHASES entry matched: %s" % r)
        
    def _ne_lookup(self, isotope, species):
        
        def escape_brackets(string):
            s = string.replace(r'(', r'\(')
            s = s.replace(r')',r'\)')
            s = s.replace(r'\\)',r'\)')
            s = s.replace(r'\\(',r'\(')
            s = s.replace(r'\[',r'[')
            s = s.replace(r'\]',r']')
            return s
        
        isotope = escape_brackets(isotope)
        species = escape_brackets(species)
            
        r1 = r"\s*Log_alpha_{}_{}\s*".format(isotope, species)
        rc1 = re.compile(r1)
        out = []
        
        with iter(open(self.db, 'r')) as f:
            for line in f:
                if re.match(rc1, line):
                    line = next(f)
                    while line.strip() not in ('', '#'):
                        a = self._cc(line.strip()).split()
                        out.append(copy(a))
                        line = next(f)
                    return [o for o in out if o]
        raise Exception("No NAMED EXPRESSIONS entry matched: %s" % r1)
                
    def get_k_values(self, reactants_list, temperature=298.15):
        """Get thermodynamic data for a specified phase.
        
        Looks up the reaction specified by 'reactants_list' in the database
        and returns all thermodynamic data found.
        
        Args:
            reactants_list: A list of strings. Each string defines a species
                such that the species listed, all reacted together, specify a
                dissolution reaction (i.e. PHASES defintiion) in the database
                file.
            temperature: The temperature to evaluate any analytical expressions
                at.
                
        Returns:
            A dict containing data found:
            log_k: log_k for the reaction, as defined in the database.
            delta_h: delta_h for the reaction, as defined in the database.
            gamma: gamma for the reaction, as defined in the database.
            analytic_line: string containing analytical K expression constants
            analytic: The evaluation of analytic_line at the specified
                temperature.
                
            Entries not present in the database are returned as None.
        """
        
        if temperature < 50:
            print("Warning! Temperature (K) given as %i. Converting to %i" %
                    (temperature, temperature+273.15))
            temperature = temperature + 273.15
    
        # If possible return cached values
        chk = reactants_list.copy()
        chk.append(str(temperature))
        chk = ' '.join(chk)
        if chk in self.thermo:
            return self.thermo[chk]
            
        thermo = {}
        data = self._phase_lookup(reactants_list)
        for a in data:
            if a[0] == 'log_k':
                thermo[a[0]] = a[1]
            elif a[0] == 'delta_h':
                thermo[a[0]] = a[1]
            elif a[0] == '-gamma':
                thermo[a[0]] = a[1]
            elif a[0] == '-analytic':
                thermo['analytic_line'] = ' '.join(a)
                thermo['analytic_value'] = self._database_eval( a[1:], 
                                                                temperature )
        
        self.thermo[chk] = thermo
        return thermo
                
    def get_1000lnalpha(self, isotope, species, temperature=298.15):
        """Get an isotope fractionation factor from the database.
        
        Returns 1000lnalpha for the specified reaction.
        
        Args:
            isotope (str): the isotope fractionating (e.g. '13C')
            species (str): the species pair involved in the fractionation
                (eg. r'CO2(g)/CO2(aq)')
            temperature: The temperature (degrees K) to calculate 1000lnalpha
                at.
        Returns:
            1000lnalpha for the reaction.
        """
        
        if temperature < 50:
            print("Warning! Temperature (K) given as %i. Converting to %i" %
                    (temperature, temperature+273.15))
            temperature = temperature + 273.15
            
        # Check for cached value
        chk = isotope + species + str(temperature)
        if chk in self.alphas:
            return self.alphas[chk]
        
        
        value = 0
        tmp = self._ne_lookup(isotope, species)
        
        for a in tmp:
            if a[0] == '-add_logk':
                b = a[1].split('_')
                value += self.get_1000lnalpha(b[2], b[3], temperature)*int(a[2])
            elif a[0] == '-ln_alpha1000':
                value += self._database_eval(a[1:], temperature)                
        self.alphas[chk] = value   
        return value
         
   
    def get_alpha(self, isotope, species, temperature=298.15):
        """Get an isotope fractionation factor from the database.
        
        Returns alpha for the specified reaction. Arguments are the same as
        get_1000lnalpha.
        
        Args:
            isotope (str): the isotope fractionating (e.g. '13C')
            species (str): the species pair involved in the fractionation
                (eg. r'CO2(g)/CO2(aq)')
            temperature: The temperature (degrees K) to calculate 1000lnalpha
                at.
        Returns:
            alpha for the reaction.
        """
    
        ln1000a = self.get_1000lnalpha(isotope, species, temperature=298.15)
        return math.exp(0.001*ln1000a)
    
    def get_iso_stnd(self, isotope):
        """Get the absolute isotope ratio in the standard.
        
        Looks up the absolute mole fraction of the specified isotope present
        in the standard. The standard used, and it's composition, are defined
        in the phreeqc database.
        
        Args:
            isotope (str): The isotope desired (e.g. '13C')
        Returns:
            The mole fraction of 'isotope' present in the standard.
        """
        
        a = None
        pat = "([ \t]*?)-isotope([ \t]*?)\[{!s}\][ \t]"
        c = re.compile(pat.format(isotope))
        with open(self.db, 'r') as f:
            for line in f:
                if re.match(c, line):
                    a = line
                    
        if a is None:
            raise Exception("No isotope standard found.")
            
        b = a.split()
        return float(b[3])
            
class PhreeqcInputLog(object):
    """Logs IPhreeqc input to a text file.

    PhreeqcInputLog is a utility class used by caves.Simulator objects to log
    iphreeqc input strings to a .phr text file. The resulting file is useful 
    for understanding how the code runs and debugging failed models. The log 
    file is also valid phreeqc input and can be run directly as a phreeqc 
    script.
    """
    
    def __init__(self, filename, dbpath):
        """Initialise the object and create a log file.
        
        Creates a .phr log file at the specified location. The first few lines
        are initialised with the date, time and full path to the database used.
        
        Args:
            filename (str): Location to write the log file.
            dbpath (str): Path to the database file. Perferably full path.
        """
        
        self.filename = filename
        self.pq_input = open(self.filename,'w')
        self.pq_input.truncate()
        self._preamble()
        
        self.pq_input.write("\nDATABASE %s" % dbpath)
        self.pq_input.close()
        
    def _preamble(self):
        """Write log file preamble."""
        
        now = datetime.datetime.now()
        line1 = "#\tIPhreeqc input log.\n"
        line2 = "#\tDate:\t%i-%i-%i\n" % \
            (now.year, now.month, now.day)
        line3 = "#\tTime:\t%i:%i:%i\n" % \
            (now.hour, now.minute, now.second)
            
        self.pq_input.write(line1 + '\n')
        self.pq_input.write(line2)
        self.pq_input.write(line3)
        
    def _buffer(self):
        """Write break into log file for readability."""
        
        self.pq_input.write("\n\n" + '#' + '-'*20 + "\n\n")
    
    def add(self, string):
        """Write a string to log file.
        
        Args:
            string (str): PHREEQC input text to be added to log file.
        """
        self.pq_input = open(self.filename,'a')
        self._buffer()
        self.pq_input.write(string)
        self.pq_input.close()

class PostProcessor(object):
    """Performs offline calculations and formatting of model results.
    
    Post-processes model output from a caves.Simulator object, adding 
    parameters calculated offline and making the output more readable.
    """
    
    def __init__(self, Simulator):
        """Run the post-processor.
        
        Does the following:
            - Adds f_ca (fraction of Ca remaining) and f_c (fraction of c 
              remaining) parameters to the model output.
            - Calculates X/Ca ratios from mole outputs (Mg, Sr, Ba, U)
            - Rename some outputs to be more readable
            - Remove nonsense radiocarbon calculations from the degassing loop
              results.
            - Formats some PHREEQC-output parameter names to make them more
              readable.
        
        Args:
            Simulator: The Simulator object to operate on.
        """
        
        self.s = Simulator
        self.calculate_f()
        self.VSMOW_to_VPDB()
        self.calculate_XCa()
        self.UCa_mmol_to_mol()
        self.tidy()
        self.calculate_radiocarbon()
        self.set_none()  
        self.results_df = pd.DataFrame()
        self.CDA()     

    


    def calculate_f(self):
        """Calculate the fractions of carbon and calcium remaining at each
        model step.
        
        Calculates f_c (fraction of C) and f_ca (fraction of Ca) remaining in
        the solution at each model step relative to the amount present
        immediately following bedrock dissolution. Calculated values are added 
        to the Simulator output dict.
        """

        init = output_filter(self.s.output, 'step_desc', 'dissolve')
        init_ca = init['Ca(mol/kgw)'][0]
        init_c = init['C(mol/kgw)'][0]
        ca = self.s.output['Ca(mol/kgw)']
        c = self.s.output['C(mol/kgw)']
        self.s.output['f_ca'] = [x / init_ca for x in ca]
        self.s.output['f_c'] = [x / init_c for x in c]
        
  
    
    def VSMOW_to_VPDB(self):
        # Ensure data is loaded
        if not self.s.output:
            print("Warning: self.s.output is empty!")
            return


        # Get mineralogy setting
        mineralogy = self.s.settings.get('precipitate_mineralogy', "").strip()


        # Access d18O data based on mineralogy
        if mineralogy == 'Calcite':
            d18O = self.s.output.get('I_R(18O)_Calcite', [])
        elif mineralogy == 'Aragonite':
            d18O = self.s.output.get('I_R(18O)_Aragonite', [])
        else:
            print("Unsupported mineralogy setting:", mineralogy)
            return

        # Check if d18O was found
        if not d18O:
            print(f"Warning: {mineralogy} data not found in self.s.output!")
            return

        # Process data, skipping the first two indices
        d18O_PDB = []
        for i, x in enumerate(d18O):
            if i < 2:
                d18O_PDB.append(np.nan)
            else:
                d18O_PDB.append(x * 0.97001 - 29.99 if x is not None else np.nan)

        # Save results back to self.s.output
        self.s.output['d18O_PDB'] = d18O_PDB
        

          
                

    def calculate_XCa(self):
        """Calculate X/Ca ratios of solution and precipitates.
        
        X/Ca is calculated at each time step using a Rayleigh distillation
        model. X/Ca ratios for solution and any precipitate are added to the
        Simulator output dict.
        
        X includes Mg, Sr and Ba, U
        """
        
        a = self.s.output
        
        trace_elements = ['Ba', 'Sr', 'Mg','U']
        dissolved_ratios = {k : [] for k in trace_elements}
        precipitate_ratios = {k : [] for k in trace_elements}
        
        for i, desc in enumerate(a['step_desc']):
            w = a['mass_H2O']
            ca = a['Ca(mol/kgw)']
            dissolved_ca = ca[i] * w[i]
            
            if 'CaCO3_precipitation' in desc:
                solid_ca = dissolved_ca - ca[i-1] * w[i-1]
                
            for x in trace_elements:
                x_dissolved = a[x+'(mol/kgw)'][i] * w[i]
                try: 
                    dissolved_ratios[x].append( x_dissolved / dissolved_ca )
                except ZeroDivisionError:
                    dissolved_ratios[x].append( 0 )
                
                # precipitated trace element = amount lost from solution
                if 'CaCO3_precipitation' in desc:
                    x_precip = x_dissolved - a[x+'(mol/kgw)'][i-1] * w[i-1]
                    try: 
                        precipitate_ratios[x].append( x_precip / solid_ca )
                    except ZeroDivisionError:
                        precipitate_ratios[x].append( 0 )
                else:
                        precipitate_ratios[x].append( 0 )
         
        for x in trace_elements:
            self.s.output[x+'/Ca(mol/mol)'] = dissolved_ratios[x]
            precipitate_suffix = '_Calcite' if self.s.settings['precipitate_mineralogy'] == 'Calcite' else '_Aragonite'
            self.s.output[x+'/Ca(mol/mol)' + precipitate_suffix] = precipitate_ratios[x]

           # self.s.output[x+'/Ca(mol/mol)_Calcite'] = precipitate_ratios[x] 
           
            
    def UCa_mmol_to_mol(self):
        """UCa mmol/mol to mol/mol
        
        The bedrock UCa cannot handle small values or 
        ERROR: Elements in species have not been tabulated, 
        C0.988943415[13C]0.011056585O2.993996620[18O]0.006003562.
        
        Thus UCa is modelled as mmol/mol and other X/Ca as mol/mol
        This puts each X/Ca on the same scale"""
        
        if self.s.settings['precipitate_mineralogy'] == 'Calcite':
            UCa_Calcite = self.s.output.get('U/Ca(mol/mol)_Calcite')
            UCa = self.s.output.get('U/Ca(mol/mol)')
            UCa_Calcite = [value * 0.001 if value is not None else None for value in (UCa_Calcite or [])]
            UCa = [value * 0.001 if value is not None else None for value in (UCa or [])]
            self.s.output['U/Ca(mol/mol)_Calcite'] = UCa_Calcite
            self.s.output['U/Ca(mol/mol)'] = UCa
        elif self.s.settings['precipitate_mineralogy'] == 'Aragonite': 
            UCa_Aragonite = self.s.output.get('U/Ca(mol/mol)_Aragonite')
            UCa = self.s.output.get('U/Ca(mol/mol)')
            UCa_Aragonite = [value * 0.001 if value is not None else None for value in (UCa_Aragonite or [])]
            UCa = [value * 0.001 if value is not None else None for value in (UCa or [])]
            self.s.output['U/Ca(mol/mol)_Aragonite'] = UCa_Aragonite
            self.s.output['U/Ca(mol/mol)'] = UCa       
           
        
    def CDA(self):
        """Performs the CDA 
        
        Extract users input data 
        Extracts the last index of the model data for current iteration
        Define key input settings
        Caclulates the residual (input data - modeled data) at each point in time-seris
        Checks whether residual falls within tolerance level
        If it does - there is a successful match 
        Appends input settings and residual values to CDA.xlsx
        
        """
        
        # If output_dir is provided, use it; otherwise, default to the current working directory 
        output_dir = os.getcwd() 
        
        
        # Ensure the directory exists; create it if it does not 
        os.makedirs(output_dir, exist_ok=True)
        
        # Define the new folder name for CDA Results 
        event_analyser_results_dir = os.path.join(output_dir, 'CDA Results') 
        
        # Check if the directory exists; if not, create it 
        if not os.path.exists(event_analyser_results_dir): 
            os.makedirs(event_analyser_results_dir)

        
        ## Paths for separate CSV files within the new folder 
        tolerances_csv = os.path.join(event_analyser_results_dir, 'Tolerances.csv') 
        input_ranges_csv = os.path.join(event_analyser_results_dir, 'Input_Ranges.csv') 
        all_outputs_csv = os.path.join(event_analyser_results_dir, 'All_outputs.csv')
        matches_csv = os.path.join(event_analyser_results_dir, 'Matches.csv')

        file_path = self.s.settings['user_filepath']

        if not file_path:
            return

        try:
            # Load the users time-series excel file
            df = pd.read_csv(file_path)
            # Strip whitespace from the headers and normalize column names by removing special characters
            df.columns = df.columns.str.strip().str.lower().str.replace(r'[^a-z0-9]', '', regex=True)

            age_column = [col for col in df.columns if 'age' in col.lower()]
            d13C_columns = [col for col in df.columns if 'd13c' in col.lower()]
            d18O_columns = [col for col in df.columns if 'd18o' in col.lower()]
            mgca_column = [col for col in df.columns if 'mgca' in col.lower()]
            dcp_column = [col for col in df.columns if 'dcp' in col.lower()]
            d44Ca_column = [col for col in df.columns if 'd44ca' in col.lower()]
            srca_column = [col for col in df.columns if 'srca' in col.lower()]
            baca_column = [col for col in df.columns if 'baca' in col.lower()]
            uca_column = [col for col in df.columns if 'uca' in col.lower()]

            age_data = df[age_column[0]].dropna().tolist()
            d13C_data = df[d13C_columns[0]].dropna().tolist() if d13C_columns else None
            d18O_data = df[d18O_columns[0]].dropna().tolist() if d18O_columns else None
            MgCa_data = df[mgca_column[0]].dropna().tolist() if mgca_column else None
            dcp_data = df[dcp_column[0]].dropna().tolist() if dcp_column else None
            d44Ca_data = df[d44Ca_column[0]].dropna().tolist() if d44Ca_column else None
            SrCa_data = df[srca_column[0]].dropna().tolist() if srca_column else None
            BaCa_data = df[baca_column[0]].dropna().tolist() if baca_column else None
            UCa_data = df[uca_column[0]].dropna().tolist() if uca_column else None
          
            
        except Exception as e:
            print(f"Error reading Excel file: {e}")
            return

        tolerance =    self.s.settings['tolerance_d13C']
        d18O_tolerance = self.s.settings['tolerance_d18O']
        mg_tolerance = self.s.settings['tolerance_MgCa']
        dcp_tolerance = self.s.settings['tolerance_DCP']
        d44Ca_tolerance =  self.s.settings['tolerance_d44Ca']
        sr_tolerance = self.s.settings['tolerance_SrCa'] 
        ba_tolerance = self.s.settings['tolerance_BaCa']
        u_tolerance  = self.s.settings['tolerance_UCa'] 
        results = [] 
        all_record = []
        match_found = False  # Flag to check if any match is found

        # Define the mappings
        keys_map = { 
            'Calcite': { 
                'd13C': 'd13C_Calcite',
                'd18O': 'd18O_Calcite',
                'MgCa': 'Mg/Ca(mol/mol)_Calcite',
                'SrCa':  'Sr/Ca(mol/mol)_Calcite',
                'BaCa':  'Ba/Ca(mol/mol)_Calcite', 
                'UCa':  'U/Ca(mol/mol)_Calcite',                  
                'dcp': 'DCP', 
                'd44Ca': 'd44Ca_Calcite' 
                }, 
            'Aragonite': { 
                'd13C': 'd13C_Aragonite', 
                'd18O': 'd18O_Aragonite',
                'MgCa': 'Mg/Ca(mol/mol)_Aragonite', 
                'SrCa':  'Sr/Ca(mol/mol)_Aragonite',
                'BaCa':  'Ba/Ca(mol/mol)_Aragonite', 
                'UCa':  'U/Ca(mol/mol)_Aragonite',
                'dcp': 'DCP', 
                'd44Ca': 'd44Ca_Aragonite' 
                } 
            }
        
        
       # Get the mineralogy setting 
        mineralogy = self.s.settings.get('precipitate_mineralogy') 
        if mineralogy not in keys_map: 
            print('Unknown precipitate mineralogy') 
            return
        
    
        
        # Retrieve and process spel values 
        keys = keys_map[mineralogy] 
        
        # Determine the minimum length across model outputs to avoid index errors
        lengths = [len(self.s.output.get(keys[k], [])) for k in keys if keys[k] in self.s.output]
        num_data_points = min(lengths) if lengths else 0
        
        for i in range(num_data_points):
           d13C_spel = self.s.output.get(keys['d13C'], [None])[i]
           #d18O_spel =  self.s.output.get(keys['d18O'], [None])[i]
           MgCa_spel =  self.s.output.get(keys['MgCa'], [None])[i]
           SrCa_spel =  self.s.output.get(keys['SrCa'],  [None])[i]
           BaCa_spel =  self.s.output.get(keys['BaCa'], [None])[i]
           UCa_spel = self.s.output.get(keys['UCa'],  [None])[i]
           dcp_spel =  self.s.output.get(keys['dcp'], [None])[i]
           d44Ca_spel = self.s.output.get(keys['d44Ca'],  [None])[i] 
           

           d18O_spel =  self.s.output.get(keys['d18O'], [None])[i] 
           # Convert d18O_spel if present
           d18O_spel = (d18O_spel * 0.97001) - 29.99 if d18O_spel is not None else None
           
      
           MgCa_spel = MgCa_spel * 1000 if MgCa_spel is not None else None 
           SrCa_spel = SrCa_spel * 1000 if SrCa_spel is not None else None 
           BaCa_spel = BaCa_spel * 1000 if BaCa_spel is not None else None 
           UCa_spel = UCa_spel * 1000 if UCa_spel is not None else None 

           
           # Skip to the next iteration if d13C_spel is None
           d13C_spel = -999 if d13C_spel is None else d13C_spel
           d18O_spel = -999 if d18O_spel is None or d18O_spel != d18O_spel else d18O_spel
           d44Ca_spel = -999 if d44Ca_spel is None or d44Ca_spel != d44Ca_spel else d44Ca_spel

           Gkeys = [
    'soil_pCO2', 'soil_d13C', 'cave_pCO2', 'gas_volume', 'temperature', 'atm_d18O', 
    'bedrock_pyrite', 'soil_U', 'bedrock_UCa', 'soil_Mg', 'bedrock_MgCa', 'soil_Ba', 
    'bedrock_BaCa', 'soil_Sr', 'bedrock_SrCa', 'soil_O2', 'soil_R14C', 'atm_pCO2', 'atm_d13C' 
    ] 
    
           # Extract settings into a dictionary
           settings = {key: self.s.settings[key] for key in Gkeys}

           # Automatically create variables from dictionary keys
           locals().update(settings)
           
           f_ca = self.s.output.get('f_ca',[])
           f_ca = f_ca[i]
           ca = self.s.output.get('Ca(mol/kgw)',[])
           ca = ca[i]
 
           d13C_DIC = self.s.output.get('d13C',[])
           d13C_DIC = d13C_DIC[1]
           atm_d18O = self.s.settings['atm_d18O']
         
        
           # Define the keys to keep from self.s.settings **ADD atmo_exhange** 
           desired_keys = [ 
               'atm_O2', 'atm_d18O', 'atm_pCO2', 'atm_d13C', 'atm_R14C',
               'soil_O2', 'soil_R14C', 'soil_d13C', 'soil_pCO2',  
               'soil_Ba', 'soil_Ca', 'soil_Mg', 'soil_Sr', 'soil_U',  
               'bedrock_BaCa', 'bedrock_MgCa', 'bedrock_SrCa',  
               'bedrock_UCa', 'bedrock_d13C', 'bedrock_d44Ca',  
               'bedrock_mineral', 'bedrock_pyrite',  
               'gas_volume', 'reprecip', 'cave_pCO2','cave_R14C','cave_d13C', 'temperature', 'kinetics_mode', 'precipitate_mineralogy']
           

           # Iterate through the data points
           for index in range(len(age_data)): 
               # Handle d13C_value and calculate its residual
               d13C_value = d13C_data[index] if d13C_data and index < len(d13C_data) else np.nan
               residual = d13C_spel - d13C_value if d13C_value is not np.nan else np.nan
     
            
               # Base dictionary with common keys for CDA.xlsx  
               base_record = {  
                   'Age': age_data[index],  
                   'd13C': d13C_value, 
                   'CaveCalc d13C': d13C_spel, 
                   'd13C residual': residual, 
                   'fCa': f_ca, 
                   'd13C_init': d13C_DIC,
                   'Ca (mol/kgw)': ca,
                   } 
               
               # Update base_record with all settings from self.s.settings
               # Filter and add desired settings to base_record 
               filtered_settings = {key: self.s.settings[key] for key in desired_keys if key in self.s.settings} 
               base_record.update(filtered_settings)
                 
               
               d18O_residual  = d18O_spel - d18O_data[index] if d18O_data else None
               MgCa_residual = MgCa_spel - MgCa_data[index] if MgCa_data else None
               dcp_residual = dcp_spel - dcp_data[index] if dcp_data else None
               d44Ca_residual = d44Ca_spel - d44Ca_data[index] if d44Ca_spel is not None and d44Ca_data and d44Ca_data[index] is not None else None 
               SrCa_residual = SrCa_spel - SrCa_data[index] if SrCa_data else None
               BaCa_residual = BaCa_spel - BaCa_data[index] if BaCa_data else None
               UCa_residual = UCa_spel - UCa_data[index] if UCa_data else None
            
               # Check if residuals are within tolerance
               residual_check = abs(residual) <= tolerance if d13C_data else True
               d18O_check = abs(d18O_residual) <= d18O_tolerance if d18O_data else True
               MgCa_check = abs(MgCa_residual) <= mg_tolerance if MgCa_data else True
               dcp_check = abs(dcp_residual) <= dcp_tolerance if dcp_data else True
               d44Ca_check = abs(d44Ca_residual) <= d44Ca_tolerance if d44Ca_data is not None else True
               SrCa_check = abs(SrCa_residual) <= sr_tolerance if SrCa_data else True
               BaCa_check = abs(BaCa_residual) <= ba_tolerance if BaCa_data else True
               UCa_check = abs(UCa_residual) <= u_tolerance if UCa_data else True
            
               if residual_check and MgCa_check and dcp_check and d44Ca_check and SrCa_check and BaCa_check and UCa_check and d18O_check: 
                   extended_record = base_record.copy() 
                   if d18O_data:  
                       extended_record.update({
                   'd18O': d18O_data[index],
                   'CaveCalc d18O': d18O_spel,
                   'd18O Residual': d18O_residual,
                       })
    
                   if MgCa_data: 
                       extended_record.update({'MgCa': MgCa_data[index], 'CaveCalc MgCa': MgCa_spel, 'MgCa Residual': MgCa_residual}) 
                   if dcp_data: 
                       extended_record.update({'DCP': dcp_data[index], 'CaveCalc DCP': dcp_spel, 'DCP residual': dcp_residual}) 
                   if d44Ca_data:  
                       extended_record.update({'d44Ca': d44Ca_data[index], 'CaveCalc d44Ca': d44Ca_spel, 'd44Ca residual': d44Ca_residual})
                   if SrCa_data: 
                       extended_record.update({'SrCa': SrCa_data[index], 'CaveCalc SrCa': SrCa_spel, 'SrCa residual': SrCa_residual})
                   if BaCa_data: 
                       extended_record.update({'BaCa': BaCa_data[index], 'CaveCalc BaCa': BaCa_spel, 'BaCa residual': BaCa_residual})
                   if UCa_data: 
                       extended_record.update({'UCa': UCa_data[index], 'CaveCalc UCa': UCa_spel, 'UCa residual': UCa_residual})    

                   results.append(extended_record) 
                   match_found = True 
                   
                
                
           # Prepare tolerance DataFrame
           tolerance_data = { 
               'Proxy': [
                   'd13C', 'd18O', 'MgCa', 'DCP', 'd44Ca', 'SrCa', 'BaCa', 'UCa' ], 
               'Tolerance Value': [tolerance, d18O_tolerance, mg_tolerance, dcp_tolerance,
                                   d44Ca_tolerance, sr_tolerance, ba_tolerance, u_tolerance]}
        
           tolerance_df = pd.DataFrame(tolerance_data) 
        
        

           input_ranges_data = {
            'Variable': [    'soil_pCO2', 'soil_d13C', 'cave_pCO2', 'gas_volume', 'temperature', 'atm_d18O', 
    'bedrock_pyrite', 'soil_U', 'bedrock_UCa', 'soil_Mg', 'bedrock_MgCa', 'soil_Ba', 
    'bedrock_BaCa', 'soil_Sr', 'bedrock_SrCa', 'soil_O2', 'soil_R14C', 'atm_pCO2', 'atm_d13C'],
            'Minimum': [None] * 19, 
            'Maximum': [None] * 19, 
             }
        
           input_ranges_df = pd.DataFrame(input_ranges_data)
        
           
           # Iterate through the data points
           for index in range(len(age_data)):  
               # Handle d13C_value
               d13C_value = d13C_data[index] if d13C_data and index < len(d13C_data) else np.nan
               
               # Base dictionary with common keys for CDA.xlsx 
               all_records = { 
                'Age': age_data[index],  
                'd13C': d13C_value, 
                'CaveCalc d13C': d13C_spel, 
                'd13C residual': residual, 
                'fCa': f_ca, 
                'd13C_init': d13C_DIC,
                'Ca (mol/kgw)': ca,  
                } 
            
               # Extend the base record with all available data
               all_all_records = all_records.copy() 
               if d18O_data:  
                   all_all_records.update({
                    'd18O': d18O_data[index],
                    'CaveCalc d18O': d18O_spel,
                    'rainfall d18O': atm_d18O, 
                    'd18O residual': d18O_data[index] -  d18O_spel, 
                })
            
               if MgCa_data: 
                   all_all_records.update({
                    'MgCa': MgCa_data[index], 
                    'CaveCalc MgCa': MgCa_spel,
                    'MgCa residual': MgCa_data[index] -  MgCa_spel,
                })
            
               if dcp_data: 
                   all_all_records.update({
                    'DCP': dcp_data[index], 
                    'CaveCalc DCP': dcp_spel,
                    'DCP residual': dcp_data[index] -  dcp_spel, 
                }) 
            
               if d44Ca_data: 
                   all_all_records.update({
                    'd44Ca': d44Ca_data[index], 
                    'CaveCalc d44Ca': d44Ca_spel,
                    'd44Ca residual': d44Ca_data[index] -  d44Ca_spel,
                })
                   
               if SrCa_data: 
                   all_all_records.update({
                    'SrCa': SrCa_data[index], 
                    'CaveCalc SrCa': SrCa_spel,
                    'SrCa residual': SrCa_data[index] -  SrCa_spel,
                })
            
               if BaCa_data: 
                   all_all_records.update({
                    'BaCa': BaCa_data[index], 
                    'CaveCalc BaCa': BaCa_spel,
                    'BaCa residual': BaCa_data[index] -  BaCa_spel, 
                })
            
               if UCa_data: 
                   all_all_records.update({
                    'UCa': UCa_data[index], 
                    'CaveCalc UCa': UCa_spel,
                    'UCa residual': UCa_data[index] -  UCa_spel,
                })
                   
               filtered_settings = {key: self.s.settings[key] for key in desired_keys if key in self.s.settings} 
               all_all_records.update(filtered_settings)

               # Append the extended record to results
               all_record.append(all_all_records) 

                 
         
            

        

        # Convert results to a DataFrame
        all_record_df = pd.DataFrame(all_record)
        
        # Handle 'All outputs' CSV 
        if not os.path.exists(all_outputs_csv):  
            all_record_df.to_csv(all_outputs_csv, index=False) 
            print(f"CDA was initialised for the first time in the output directory. Created new {all_outputs_csv}")
        else: 
            # Append new data to 'All outputs' CSV 
            all_record_df.to_csv(all_outputs_csv, mode='a', header=False, index=False) 
       
         
        # Handle 'Tolerances' CSV (Check if the file exists or create a new one) 
        if not os.path.exists(tolerances_csv):   
            # Create the Tolerances CSV file 
            tolerance_df.to_csv(tolerances_csv, index=False)  
        else: 
            # Overwrite the existing Tolerances CSV file 
            tolerance_df.to_csv(tolerances_csv, index=False) 
        
        # Handle 'Input Ranges' CSV 
        if os.path.exists(input_ranges_csv): 
            existing_df = pd.read_csv(input_ranges_csv) 
            
            for variable in input_ranges_data['Variable']: 
                if variable in existing_df['Variable'].values: 
                    # Update min and max 
                    existing_df.loc[existing_df['Variable'] == variable, 'Minimum'] = min( 
                        existing_df.loc[existing_df['Variable'] == variable, 'Minimum'].dropna().tolist() + [eval(variable)] 
                        ) 
                    existing_df.loc[existing_df['Variable'] == variable, 'Maximum'] = max( 
                        existing_df.loc[existing_df['Variable'] == variable, 'Maximum'].dropna().tolist() + [eval(variable)]
                        ) 
                else: 
                    # Add new variable  
                    new_row = pd.DataFrame({
                'Variable': [variable],
                'Minimum': [eval(variable)],
                'Maximum': [eval(variable)] 
                })  
                    existing_df = pd.concat([existing_df, new_row], ignore_index=True) 
                
            # Save updated Input Ranges CSV 
            existing_df.to_csv(input_ranges_csv, index=False)  
        else: 
            input_ranges_df.to_csv(input_ranges_csv, index=False)
    
     
        # Proceed with results processing only if a match was found
        if match_found: 
            
            # Process results and calculate mean
            if results: 
                new_results_df = pd.DataFrame(results)
            
            # Combine new results with existing results
            if not self.results_df.empty:  
                combined_df = pd.concat([self.results_df, new_results_df], ignore_index=True)
            else:
                combined_df = new_results_df
            
            
            # Update self.results_df to be the aggregated DataFrame
            self.results_df = combined_df

            # Save results to Matches CSV 
            if not os.path.exists(matches_csv): 
                self.results_df.to_csv(matches_csv, index=False) 
                print(f"Match! Created new file '{matches_csv}' and saved results.") 
            else: 
                self.results_df.to_csv(matches_csv, mode='a', header=False, index=False) 
                print(f"Match! Appended to '{matches_csv}' and saved results.")
                       
        
            

    def calculate_radiocarbon(self):
        """Sets all post-dissolution R14C values to be constant.
        
        Radiocarbon distribution is fully calculated during the bedrock 
        dissolution step, but is not included in subsequent degassing /
        precipitation steps for three reasons:
            - It increases computation time.
            - When model steps are very small, 14C may cause non-convergence.
            - d13C-corrected R14C is not expected to change during these 
                processes.
            
        To avoid confusion, spurious post-dissolution R14C values reported by
        IPhreeqc are set equal to the post-dissolution value.
        
        This method also adds a new column ('DCP') to the output. Note that
        the DCP calculation assumes modern = 100 pMC.
        """

        for key in self.s.output.keys():
            if 'R14C' in key:
                pmc = None
                for (i, value) in enumerate(self.s.output[key]):
                    if 'bedrock' in self.s.output['step_desc'][i]:
                        pmc = self.s.output[key][i]
                    elif pmc is not None:
                        self.s.output[key][i] = pmc
                        
        atmo_a14c_init = 100 # placeholder value (pMC)
        self.s.output['DCP'] = [ (1-v/atmo_a14c_init)*100 for v in 
                                 self.s.output['R14C'] ]
                        
    def tidy(self):
        """Rename PHREEQC variable names with more reader-friendly syntax. 
        
        Also removes a couple of unwanted outputs.
        """
        o = self.s.output
        rep_keys = {}
        
        # remove unwanted outputs (not of interest to most users)
        o.pop('soln')
        o.pop('mass_H2O')
        o.pop('pct_err')
        o.pop('temp(C)')
        o.pop('I_R(14C)_CO2(aq)')
        
        # rename some outputs for readability
        for key, data in o.items():
            if key[0:3] == 'I_R': # rename isotopes
                iso = key[key.find('(')+1:key.find(')')]
                if iso == '14C':
                    new_key = 'R' + iso + key[key.find(')')+1:]
                else:
                    new_key = 'd' + iso + key[key.find(')')+1:]
                rep_keys[key] = new_key
            elif key[0:2] == 'm_': # rename molalities
                new_key = key[2:]
                rep_keys[key] = new_key
            elif key[0:2] == 's_':
                new_key = 'moles_' + key[2:]
                rep_keys[key] = new_key
        
        for k1, k2 in rep_keys.items():
            o[k2] = o.pop(k1)
            
    def set_none(self):
        """Set default paramter returns (e.g. d18O = -999) to None."""
        
        for k, lst in self.s.output.items():
            new_lst = []
            for e in lst:
                if not(isinstance(e, str)) and e <= -999:
                    new_lst.append(None)
                else:
                    new_lst.append(e)
            self.s.output[k] = new_lst
       
# Begin radiocarbon calculation functions
def pmc(C14, d13C, stnd14C=1.175887709e-12):
    """Converts 14C/C absolute ratio to a d13C-corrected pMC value.
    
    Args:
        C14 : 14C/C ratio (absolute)
        d13C : V-PDB d13C values
        stnd14C : The 14C/C ratio in the standard
    Returns:
        the standard-normalised radiocarbon value in pMC.
    """
    
    return C14 / stnd14C * 100 * pow(0.975/(1+0.001*d13C),2)
       
def pmc_2_c14(R14C, d13C, stnd14C=1.175887709e-12):
    """Converts a d13C-corrected pMC value to a 14C/C absolute ratio.
    
    Conversion follows Stuvier & Pollach (1977).
    
    Args:
        R14C: A radiocarbon value in d13C corrected percent modern carbon
              (pmc).
        d13C: The corresponding d13C value.
        stnd14C: The standard 14C/C molar ratio. Default is 
                 1.175887709e-12.
    Returns:
        14C/C ratio
    """
    
    return stnd14C * 0.01 * R14C * pow((1+0.001*d13C)/0.975,2)
       
def c14_to_pmc(C12, C13, C14, stnd13C=0.0111802, stnd14C=1.175887709e-12):
    """Returns isotope ratios given relative c isotope abundance data.
    
    Args:
        C12: Mole fraction 12C
        C13: Mole fraction 13C
        C14: Mole fraction 14C
        stnd13C: 13C/12C ratio in the standard. Default is 0.0111802 (VPDB)
        stnd13C: 14C/C ratio in the standard. Default is 1.175887709e-12
        
    Returns:
        d13C, R14C (pMC, d13C-corrected)
    """
    
    d13C = ((C13/C12)/stnd13C - 1) * 1000
    R14C = pmc(C14, d13C, stnd14C)
    return d13C, R14C
        
def pmc_normalise(R14C, d13C, stnd14C=1.175887709e-12):
    """Convert a 14C/C pmc-normalised ratio (returned by PHREEQC) input a 
    'proper' d13C corrected pMC ratiocarbon ratio."""
    
    true_ratio = 0.01 * R14C * stnd14C
    return pmc(true_ratio, d13C, stnd14C)
    
def pmc_denormalise(pMC, d13C, stnd14C=1.175887709e-12):
    """Convert a d13C-corrected R14C (pMC) to a normalised 14C/C ratio, as used
    by PHREEQC."""
    
    c14_ratio = pmc_2_c14(pMC, d13C, stnd14C)
    return 100 * c14_ratio / stnd14C
    
# begin helper function definitions    
def output_filter(src, key, value):
    """Filter lists contained in a dict by the value in one of the lists.
    
    The function takes a dict of lists, where all lists are of equal length. It
    returns a new list of dicts where the lists are shortened: only list 
    entries at indices that meet specified criteria are copied.
    
    Args:
        src: Dictionary to filter. Each entry should be a list of equal length.
        key: The key in src to filter the lists by
        value: value in src[key] to include in output.
    Returns:
        A filtered version of src.
    """
    
    if isinstance(value, str):
        f = lambda v : value in v
    else:
        f = lambda v : value == v
        
    inds = [i for i,a in enumerate(src[key]) if f(a)]
    
    o = {}
    for k, v in src.items():
        o[k] = [a for i,a in enumerate(v) if i in inds]
    return o
    
def matlab_header_parse(dictionary):
    """Remove illegal characters from dictionary keys.
    
    To transfer data to matlab, certain characters are not allowed in field / 
    array names (e.g. brackets, hypens). This function removes these characters
    in preparation for writing dicts (of numpy arrays) to a .mat file.
    
    Args:
        dictionary: A dict
    Returns:
        A dict with modified key names
    """
    
    b = {}
    for k in dictionary:
        new_k = k.replace(')', '') # because matlab is fussy
        new_k = new_k.replace('(','_') # about variable names
        new_k = new_k.replace('-','') # and does not allow these
        new_k = new_k.replace('/','') # characters
        new_k = new_k.replace('[','')
        new_k = new_k.replace(']','')    
        
        b[new_k] = dictionary[k]
    return b
    
def numpify(dictionary):
    """Prepare a dict of lists for writing to a .mat file.
    
    Convert the dict of lists to a dict of numpy arrays. Dict keys are edited
    if they contain matlab-illegal characters. Lists in the dict are converted
    to numpy arrays.
    
    Args:
        dictionary: A dict of lists. Each list should be composed of a single
            type.
    Returns:
        A modified dict, ready for writing to a .mat file.    
    """
    
    a = matlab_header_parse(dictionary)
    b = {}
    for k in a:
        if k == "step_desc":
            b[k] = np.asarray( a[k], order='F' )
        else:
            b[k] = np.asarray( a[k], order='F' )    
    return b
            
def save_mat(dict_of_lists, filename):
    """Save data to a .mat file for use with Matlab/Octave.
    
    Takes a dict of lists (e.g. model results) and saves them to a .mat file.
    Data are prepared for saving using the numpify() function.
    
    Args:
        dict_of_lists: Data to be saved for Matlab use.
    """
        
    out = numpify(dict_of_lists)
    sio.savemat( filename, out )

def save_pkl(data, filename):
    """Save data to a  file for use with Python.
    
    Args:.pkl
        data: a pickle-able Python object.
        filename: Output file name/location.
    """
    
    with open(filename,'wb') as f:
        pickle.dump( data, f)
            
def save_csv(dictionary, filename):
    """Save data to a .csv file.

    For saving data to view in for use with other programs (e.g. Excel). Data
    should be provided as a dict of lists. Dict keys give column headers and
    lists give column values. All lists must be of equal length.
    
    In the resulting .csv, columns are arranged alphabetically by header.
    
    Args:
        dictionary: The dictionary to write to file.
        filename: The name of the file to save the data to.
    """
    
    # Sort the dictionary items alphabetically by key
    sorted_dict = OrderedDict(sorted(dictionary.items()))
    
    # Extract headers and values
    headers = list(sorted_dict.keys())
    values = list(sorted_dict.values())
    
    # Determine the number of rows
    num_rows = len(values[0]) if values else 0
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f, dialect='excel')
        
        # Write headers
        writer.writerow(headers)
        
        # Write values
        for i in range(num_rows):
            row = [values[j][i] if i < len(values[j]) else '' for j in range(len(headers))]
            writer.writerow(row)
            
            
            

    

