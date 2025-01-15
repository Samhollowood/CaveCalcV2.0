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
        self.calculate_XCa()
        self.tidy()
        self.calculate_radiocarbon()
        self.set_none()
        self.calculate_oxygen_PCP()
        self.VSMOW_to_VPDB()
        self.results_df = pd.DataFrame()
        self.EventAnalyser()     
        self.kinetic_fractionation()
    


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
        """Converts d18O(VSMOW) to d18O(PDB)"""
        
        if self.s.settings['precipitate_mineralogy'] == 'Calcite':
            d18O = self.s.output.get('d18O_Calcite', []) 
            d18O_PDB = [x * 0.97001 - 29.99 if x is not None else np.nan for x in d18O]
            self.s.output['d18O_PDB'] = d18O_PDB
        elif self.s.settings['precipitate_mineralogy'] == 'Aragonite':  
            d18O = self.s.output.get('d18O_Aragonite', [])     
            d18O_PDB = [x * 0.97001 - 29.99 if x is not None else np.nan for x in d18O]
            self.s.output['d18O_PDB'] = d18O_PDB
            
            
        

          
                 
        
    def calculate_oxygen_PCP(self):
        """Caculate and return the d18O as a reuslt of Prior Carbonate Precipitation
        
        
        """
        
      
        # Check if PCarbP_d18O is explicitly set to True or False
        if self.s.settings['PCarbP_d18O'] == True: 
            print("WARNING: PCarbP will impact on d18O")
        else:     
            return  # Exit the function if PCarbP_d18O is not True
           

        # Check precipitate mineralogy setting
        T = self.s.settings.get('temperature',298.15)
        
        # Get the initial Ca concentration (when f_ca = 1) and data for each step
        init = output_filter(self.s.output, 'step_desc', 'dissolve')
        
        if not init or 'Ca(mol/kgw)' not in init or len(init['Ca(mol/kgw)']) < 1:
            raise ValueError("Insufficient data for 'Ca(mol/kgw)' or 'step_desc' filter issue.")
            
        #Gets model Ca (mol/kgw) results for current iteration 
        ca_values = self.s.output.get('Ca(mol/kgw)', [])
        
        # Select d18O based on mineralogy
        if self.s.settings['precipitate_mineralogy'] == 'Calcite':
            d18O = self.s.output.get('d18O_Calcite', []) 
            alpha_CaCO3_H2O =  np.exp((18.03/(T+273.15) - 0.03242)) #O'Neil, 1997
            alpha18HCO3_H2O = 1 / (((2590000 * ((T + 273.15) ** -2)) + 1.89) / 1000 + 1)
            alpha18HCO3_CaCO3 = alpha18HCO3_H2O * alpha_CaCO3_H2O
        elif self.s.settings['precipitate_mineralogy'] == 'Aragonite':  
            d18O = self.s.output.get('d18O_Aragonite', []) 
            alpha18H2O_CaCO3 = np.exp((17.88/(T+273.15) - 0.03114)) # Kim et al., 2007
            alpha18HCO3_H2O = 1 / (((2590000 * ((T + 273.15) ** -2)) + 1.89) / 1000 + 1)
            alpha18HCO3_CaCO3 = alpha18HCO3_H2O * alpha18H2O_CaCO3
    
        # Transform d18O values
        d18O_PDB = [x * 0.97001 - 29.99 if x is not None else None for x in d18O]
    
        if len(ca_values) < 2:
            raise ValueError("Not enough data for 'Ca(mol/kgw)' to determine initial concentration.")
            
        # Use the second row value as Cai
        pcp_influence = self.s.settings.get('flow_path_influence', ())  # Default to 100% if not specified
        Cai = (pcp_influence/100)*ca_values[1]
    
        # List to store the d18O_PCP values
        d18O_PCP = [] 
        
        # Calculate fractionation factors
        alpha18HCO3_H2O = np.exp(-1/1000 * (2.59e6 / ((T+273.15)**2) + 1.89))  #Directly from database
        alpha18H2O_CO2aq = np.exp(1/1000 * (2.52e6 / ((T+273.15)**2) + 12.12)) #Directly from database
        alpha18CO2aq_CO2g = 1 / ((-1.9585 + (1.44176 * 10**3 / (T + 273.15)) + (-0.160515 * 10**6 / (T + 273.15) ** 2)) / 1000 + 1) #Vogel et al., 1970
        alpha18HCO3_CO2 = alpha18HCO3_H2O * alpha18H2O_CO2aq * alpha18CO2aq_CO2g
        d18Ofrac = alpha18HCO3_H2O / 6 + alpha18HCO3_CaCO3 / 2 + alpha18HCO3_CO2 / 3 - 1
        
        # Calculate d18O_PCP values and store them in the list
        for ca_value in ca_values:
            if ca_value == 0:
                # Skip the value if it's zero
                continue
            
            if ca_value >= Cai: 
                d18O_PCP.append(d18O_PDB[2])  # Use NaN if Cai is 0 or ca_value >= Ca 
                continue
            
            if Cai == 0:
                raise ZeroDivisionError("Cai is zero, which would lead to division by zero.")
                
            try:
                d18O_PCP_value = ((ca_value / Cai) ** d18Ofrac - 1) * 1000
            except ZeroDivisionError:
                print(f"Error: Division by zero encountered with ca_value: {ca_value}, Cai: {Cai}, d18Ofrac: {d18Ofrac}")
                d18O_PCP_value = float('inf')  # or handle as appropriate
            
            d18O_PCP_combined = d18O_PDB[2] + d18O_PCP_value    
            d18O_PCP.append(d18O_PCP_combined)
            
            # Output the d18O_PCP values
        
        self.s.output['d18O_PCP'] = d18O_PCP
        
    def kinetic_fractionation(self):
        if self.s.settings['kinetic_fractionation'] == True and self.s.settings['precipitate_mineralogy'] =='Calcite':
            print("Kinetic fractionation: ON... finding appropiate values from Hansen et al., 2019")
        else: 
            return 
            
        #Extract model input and outputs 
        T = self.s.settings.get('temperature',298.15)
        cave_air = self.s.settings.get('cave_pCO2',[])
        ca_init = self.s.output.get('Ca(mol/kgw)',[])
        ca_init = ca_init[1]*1000
        
        Hansen_fractionation_factors = [
            (30, 1000, 5, -10.5),
            (30, 3000, 5, -9.2),
            (30, 1000, 2, -4.7),
            (20, 1000, 5, -13.7),
            (20, 3000, 5, -12.1),
            (20, 1000, 3, -9.8),
            (10, 1000, 5, -11.9),
            (10, 3000, 5, -7.4)]
        
        # Initialize variables to track the closest match
        min_dist = float('inf')
        closest_epsilon = None

        # Calculate the Euclidean distance and find the closest match
        for known_T, known_cave_air, known_ca_init, epsilon in Hansen_fractionation_factors:
            dist = np.sqrt((T - known_T)**2 + (cave_air - known_cave_air)**2 + (ca_init - known_ca_init)**2)
            if dist < min_dist:
                min_dist = dist
                closest_epsilon = epsilon
                
         # Calculate alpha from closest_epsilon
        alpha = np.exp(closest_epsilon / 1000) 
        epsilon_oxygen = ((16.516*1000)/(T+273.15)) - 26.141 #Hansent et al., 2019
        alpha_oxygen = np.exp(epsilon_oxygen / 1000)
        
        d18O_H2O =  self.s.output.get('d18O', [])[1]
       
        d18Ocalcite_kinetic_values = []
        d18O_calcite_kinetic = (alpha_oxygen*(d18O_H2O+1000)) - 1000
        d18Ocalcite_kinetic_values.append(d18O_calcite_kinetic)
        self.s.output['d18O_calcite_kinetic'] =  d18Ocalcite_kinetic_values
    
                
         
        # Calculate ro
        d13C_HCO3 = self.s.output.get('d13C_HCO3-', [])
        ro = (d13C_HCO3[2]/1000) + 1 
        
        # Initialize a list to store the results
        d13Ccalcite_kinetic_values = []
        
       # Check the precipitate mineralogy
        if self.s.settings['precipitate_mineralogy'] == 'Calcite':
            fca = self.s.output.get('f_ca',[])
            

            # Assume init_ca, alpha, ro, and ca_values are defined elsewhere in your code.
            for f in fca:  
                # Ensure f is not zero to avoid invalid operations  
                if f == 0 or f == 1: 
                    d13Ccalcite_kinetic_values.append(None)  # or some other indicator value
                    continue
                                
                # Calculate rs using the provided equation
                rs = (f ** (alpha - 1)) * (ro*alpha)

                # Calculate d13Ccalcite_kinetic
                d13Ccalcite_kinetic = (rs - 1) * 1000
                d13Ccalcite_kinetic_values.append(d13Ccalcite_kinetic)
                    
            self.s.output['d13C_calcite_kinetic'] = d13Ccalcite_kinetic_values
        

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
        
    def EventAnalyser(self):
        """Performs the EventAnalyser 
        
        Extract users input data 
        Extracts the last index of the model data for current iteration
        Define key input settings
        Caclulates the residual (input data - modeled data) at each point in time-seris
        Checks whether residual falls within tolerance level
        If it does - there is a successful match 
        Appends input settings and residual values to EventAnalyser.xlsx
        
        """
        # Retrieve the output directory from settings 
        output_dir = self.s.settings.get('out_dir', '')
        
        # If output_dir is provided, use it; otherwise, default to the current working directory 
        output_dir = output_dir or os.getcwd() 
        
        # Construct the full path for the Excel file 
        excel_file = os.path.join(output_dir, 'EventAnalyser.xlsx') 
        
        # Ensure the directory exists; create it if it does not 
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = self.s.settings['user_filepath']

        if not file_path:
            return

        try:
            # Load the users time-series excel file
            df = pd.read_excel(file_path)
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
        
        # Check if kinetic fractionation is enabled and adjust the 'Calcite' mapping accordingly 
        if self.s.settings['kinetic_fractionation'] == True: 
            keys_map['Calcite']['d13C'] = 'd13C_calcite_kinetic' 
            keys_map['Calcite']['d18O'] = 'd18O_calcite_kinetic' 

        
       # Get the mineralogy setting 
        mineralogy = self.s.settings.get('precipitate_mineralogy') 
        if mineralogy not in keys_map: 
            print('Unknown precipitate mineralogy') 
            return
        
        
        
        # Retrieve and process spel values 
        keys = keys_map[mineralogy] 
        d13C_spel = self.s.output.get(keys['d13C'], [None])[-1] 
        d18O_spel = self.s.output.get(keys['d18O'], [None])[-1] 
        d18O_spel = [(d18O_spel * 0.97001) - 29.99 if d18O_spel is not None else np.nan]
        MgCa_spel = self.s.output.get(keys['MgCa'], [None])[-1] 
        SrCa_spel = self.s.output.get(keys['SrCa'], [None])[-1] 
        BaCa_spel = self.s.output.get(keys['BaCa'], [None])[-1] 
        UCa_spel = self.s.output.get(keys['UCa'], [None])[-1] 
        dcp_spel = self.s.output.get(keys['dcp'], [None])[-1] 
        d44Ca_spel = self.s.output.get(keys['d44Ca'], [None])[-1] 
        # Convert MgCa_spel if presen 
        MgCa_spel = MgCa_spel * 1000 if MgCa_spel is not None else None 
        SrCa_spel = SrCa_spel * 1000 if SrCa_spel is not None else None 
        BaCa_spel = BaCa_spel * 1000 if BaCa_spel is not None else None 
        UCa_spel = UCa_spel * 1000 if UCa_spel is not None else None 
        
        # Check if d13C_spel is available 
        if d13C_spel is None: 
            print('No match as model did not produce precipitate')
            return

        # Extract key input settings for the current iteration
        soil_pCO2 = self.s.settings['soil_pCO2']
        d13Csoil = self.s.settings['soil_d13C']
        f_ca = self.s.output.get('f_ca',[])
        f_ca = f_ca[-1]
        cave_pCO2 = self.s.settings['cave_pCO2']
        gas_volume = self.s.settings['gas_volume']
        temp = self.s.settings['temperature']
        d13C_DIC = self.s.output.get('d13C',[])
        d13C_DIC = d13C_DIC[1]
        rainfall_d18O = self.s.settings['atm_d18O']
        
        #Extract soil and bedrock for trace metals and d44Ca
        bedrock_Mg = self.s.settings['bedrock_MgCa']
        soil_Mg = self.s.settings['soil_Mg']
        bedrock_Sr = self.s.settings['bedrock_SrCa']
        soil_Sr = self.s.settings['soil_Sr']
        bedrock_Ba = self.s.settings['bedrock_BaCa']
        soil_Ba = self.s.settings['soil_Ba']
        bedrock_U = self.s.settings['bedrock_UCa']
        soil_U = self.s.settings['soil_U']
        bedrock_Ca = self.s.settings['bedrock_d44Ca']
        soil_Ca = self.s.settings['soil_d44Ca']

         # Iterate through the data points
        for index in range(len(age_data)):
            # Handle d13C_value and calculate its residual
            d13C_value = d13C_data[index] if d13C_data and index < len(d13C_data) else np.nan
            residual = d13C_spel - d13C_value if d13C_value is not np.nan else np.nan
            
            # Base dictionary with common keys for EventAnalyser.xlsx 
            base_record = { 
                'Age': age_data[index], 
                'd13C': d13C_value,
                'CaveCalc d13C': d13C_spel,
                'd13C residual': residual,
                'soil_pCO2 (ppmv)': soil_pCO2,
                'Soil d13C': d13Csoil,
                'cave_pCO2 (ppmv)': cave_pCO2,
                'f_{ca}': f_ca,
                'gas volume (L/kg)': gas_volume,
                'd13C_init': d13C_DIC,
                'T(°C)': temp  
            } 
            
            # Compute residuals
            d18O_residual  = d18O_spel - d18O_data[index] if d18O_data else None
            MgCa_residual = MgCa_spel - MgCa_data[index] if MgCa_data else None
            dcp_residual = dcp_spel - dcp_data[index] if dcp_data else None
            d44Ca_residual = d44Ca_spel - d44Ca_data[index] if d44Ca_data else None 
            SrCa_residual = SrCa_spel - SrCa_data[index] if SrCa_data else None
            BaCa_residual = BaCa_spel - BaCa_data[index] if BaCa_data else None
            UCa_residual = UCa_spel - UCa_data[index] if UCa_data else None
            
            # Check if residuals are within tolerance
            residual_check = abs(residual) <= tolerance if d13C_data else True
            d18O_check = abs(d18O_residual) <= d18O_tolerance if d18O_data else True
            MgCa_check = abs(MgCa_residual) <= mg_tolerance if MgCa_data else True
            dcp_check = abs(dcp_residual) <= dcp_tolerance if dcp_data else True
            d44Ca_check = abs(d44Ca_residual) <= d44Ca_tolerance if d44Ca_data else True 
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
                   'rainfall d18O': rainfall_d18O  
                   })
    
                    # Add flow path influence only if PCarbP_d18O is True
                    if self.s.settings['PCarbP_d18O'] is True:  
                        extended_record.update({'flow path influence': self.s.settings['flow_path_influence']}) 
                if MgCa_data: 
                    extended_record.update({'MgCa': MgCa_data[index], 'CaveCalc MgCa': MgCa_spel, 'MgCa Residual': MgCa_residual, 'bedrock MgCa': bedrock_Mg, 'soil MgCa': soil_Mg}) 
                if dcp_data: 
                    extended_record.update({'DCP': dcp_data[index], 'CaveCalc DCP': dcp_spel, 'DCP residual': dcp_residual}) 
                if d44Ca_data: 
                    extended_record.update({'d44Ca': d44Ca_data[index], 'CaveCalc d44Ca': d44Ca_spel, 'd44Ca residual': d44Ca_residual, 'bedrock d44Ca': bedrock_Ca, 'soil d44Ca': soil_Ca})
                if SrCa_data: 
                    extended_record.update({'SrCa': SrCa_data[index], 'CaveCalc SrCa': SrCa_spel, 'SrCa residual': SrCa_residual, 'bedrock SrCa': bedrock_Sr, 'soil SrCa': soil_Sr})
                if BaCa_data: 
                    extended_record.update({'BaCa': BaCa_data[index], 'CaveCalc BaCa': BaCa_spel, 'BaCa residual': BaCa_residual, 'bedrock BaCa': bedrock_Ba, 'soil BaCa': soil_Ba})
                if UCa_data: 
                    extended_record.update({'UCa': UCa_data[index], 'CaveCalc UCa': UCa_spel, 'UCa residual': UCa_residual, 'bedrock UCa': bedrock_U, 'soil UCa': soil_U})    

                results.append(extended_record) 
                match_found = True               
         
                
        # Prepare tolerance DataFrame
        tolerance_data = { 
            'Proxy': [
            'd13C', 'd18O', 'MgCa', 'DCP', 'd44Ca', 'SrCa', 'BaCa', 'UCa' 
            ], 
            'Tolerance Value': [tolerance, d18O_tolerance, mg_tolerance, dcp_tolerance,
            d44Ca_tolerance, sr_tolerance, ba_tolerance, u_tolerance] 
            }
        
        tolerance_df = pd.DataFrame(tolerance_data) 
        
        # Prepare Input Ranges DataFrame
        input_ranges_data = {
            'Variable': ['soil_pCO2', 'd13Csoil', 'cave_pCO2', 'gas_volume', 'temp', 'rainfall_d18O'],
            'Minimum': [None] * 6,
            'Maximum': [None] * 6
        }
        input_ranges_df = pd.DataFrame(input_ranges_data)
        
        all_record = []
        # Iterate through the data points
        for index in range(len(age_data)):
            # Handle d13C_value
            d13C_value = d13C_data[index] if d13C_data and index < len(d13C_data) else np.nan
            
            # Base dictionary with common keys for EventAnalyser.xlsx 
            all_records = { 
                'Age': age_data[index], 
                'd13C': d13C_value,
                'CaveCalc d13C': d13C_spel,
                'd13C residual': d13C_value - d13C_spel,
                'soil_pCO2 (ppmv)': soil_pCO2,
                'Soil d13C': d13Csoil,
                'cave_pCO2 (ppmv)': cave_pCO2,
                'f_{ca}': f_ca,
                'gas volume (L/kg)': gas_volume,
                'd13C_init': d13C_DIC,
                'T(°C)': temp  
            } 
            
            # Extend the base record with all available data
            all_all_records = all_records.copy() 
            if d18O_data:  
                all_all_records.update({
                    'd18O': d18O_data[index],
                    'CaveCalc d18O': d18O_spel,
                    'rainfall d18O': rainfall_d18O, 
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

            # Append the extended record to results
            all_record.append(all_all_records) 

        # Convert results to a DataFrame
        all_record_df = pd.DataFrame(all_record)

        
        # Check if the Excel file exists
        if not os.path.exists(excel_file):
            # Create a new Excel file and write the Tolerances and Input Ranges sheets
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                tolerance_df.to_excel(writer, sheet_name='Tolerances', index=False)
                input_ranges_df.to_excel(writer, sheet_name='Input Ranges', index=False)
                all_record_df.to_excel(writer, sheet_name='All outputs', index=False) 
            print(f"Created new file '{excel_file}' and saved Tolerances and Input Ranges.")
        else:
            with pd.ExcelWriter(excel_file, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer: 
                startrow = writer.sheets['All outputs'].max_row if 'All outputs' in writer.sheets else 0 
                all_record_df.to_excel(writer, sheet_name='All outputs', index=False, header=startrow == 0, startrow=startrow) 
                # Tolerances sheet handling 
                if 'Tolerances' in writer.sheets: 
                    # Remove existing Tolerances sheet
                    writer.book.remove(writer.sheets['Tolerances']) 
                    # Write the tolerance_df to the Tolerances sheet 
                tolerance_df.to_excel(writer, sheet_name='Tolerances', index=False) 
                
                # Input Ranges sheet handling 
                if 'Input Ranges' in writer.sheets: 
                    # Read the existing Input Ranges sheet 
                    existing_df = pd.read_excel(excel_file, sheet_name='Input Ranges') 
                    # Update or add variables in the input_ranges_data 
                    for variable in input_ranges_data['Variable']: 
                        if variable in existing_df['Variable'].values: 
                            # Update minimum and maximum values 
                            existing_df.loc[existing_df['Variable'] == variable, 'Minimum'] = min( 
                                existing_df.loc[existing_df['Variable'] == variable, 'Minimum'].dropna().tolist() + [eval(variable)], 
                                default=None) 
                            existing_df.loc[existing_df['Variable'] == variable, 'Maximum'] = max( 
                                existing_df.loc[existing_df['Variable'] == variable, 'Maximum'].dropna().tolist() + [eval(variable)], 
                                default=None)
                        else: 
                            # Add new variable 
                            new_row = pd.DataFrame({ 
                                'Variable': [variable], 
                                'Minimum': [eval(variable)], 
                                'Maximum': [eval(variable)] 
                                }) 
                            existing_df = pd.concat([existing_df, new_row], ignore_index=True) 
                    # Write updated DataFrame back to Excel
                    existing_df.to_excel(writer, sheet_name='Input Ranges', index=False)
                else: 
                    # Create the Input Ranges sheet if it doesn't exist 
                    input_ranges_df.to_excel(writer, sheet_name='Input Ranges', index=False)
     

        
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

               # Save the cumulative DataFrame and the aggregated DataFrame to EventAnalyser.xlsx 
               if not os.path.exists(excel_file): 
                   # If the file does not exist, create it and write the DataFrame 
                   with pd.ExcelWriter(excel_file, engine='openpyxl') as writer: 
                       self.results_df.to_excel(writer, sheet_name='Matches', index=False) 
                       print(f"Created new file '{excel_file}' and saved results.") 
               else: 
                   # If the file exists, append new results to it 
                   with pd.ExcelWriter(excel_file, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer: 
                       startrow = writer.sheets['Matches'].max_row if 'Matches' in writer.sheets else 0 
                       self.results_df.to_excel(writer, sheet_name='Matches', index=False, header=startrow == 0, startrow=startrow) 
                       print(f"Appended results to existing file '{excel_file}'.") 
                       
        
            

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
    
    In the resulting .csv, columnns are arranged alphabetically by header.
    
    Args:
        dictionary: The dictionary to write to file.
    """
    
    r = OrderedDict(sorted(dictionary.items()))
    a, b = zip(*[(k,v) for (k,v) in r.items()])
    c = zip(*b)
    
    with open(filename,'w', newline='') as f:
        writer = csv.writer(f,dialect='excel')
        writer.writerow(a)
        for row in c:
            writer.writerow(row)
            
            

    

