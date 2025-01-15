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
        self.UCa_mmol_mol()



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
    
    def UCa_mmol_mol(self):
        if self.s.settings['precipitate_mineralogy'] == 'Calcite': 
            UCa_mol_mol_calc = self.s.output.get('U/Ca(mol/mol)_Calcite')
            UCa_mol_mol = self.s.output.get('U/Ca(mol/mol)')
            # Convert it to mmol/mol element-wise
            UCa_mmol_mol = [value * 0.001 for value in UCa_mol_mol]
            UCa_mmol_mol_calc = [value * 0.001 for value in UCa_mol_mol_calc]
            # Replace the original value in the output dictionary
            self.s.output['U/Ca(mol/mol)_Calcite'] = UCa_mmol_mol_calc
            self.s.output['U/Ca(mol/mol)'] = UCa_mmol_mol
            
        elif self.s.settings['precipitate_mineralogy'] == 'Aragonite': 
            UCa_mol_mol_arag = self.s.output.get('U/Ca(mol/mol)_Aragonite')
            UCa_mol_mol = self.s.output.get('U/Ca(mol/mol)')
            UCa_mmol_mol = [value * 0.001 for value in UCa_mol_mol]
            UCa_mmol_mol_arag = [value * 0.001 for value in UCa_mol_mol_arag]
            # Replace the original value in the output dictionary
            self.s.output['U/Ca(mol/mol)_Aragonite'] = UCa_mmol_mol_arag
            self.s.output['U/Ca(mol/mol)'] = UCa_mmol_mol
        else:
            print('No defined mineralogy')
    
    def VSMOW_to_VPDB(self):
        if self.s.settings['precipitate_mineralogy'] == 'Calcite':
            d18O = self.s.output.get('d18O_Calcite', []) 
            d18O_PDB = [x * 0.97001 - 29.99 if x is not None else np.nan for x in d18O]
            self.s.output['d18O_PDB'] = d18O_PDB
        elif self.s.settings['precipitate_mineralogy'] == 'Aragonite':  
            d18O = self.s.output.get('d18O_Aragonite', [])     
            d18O_PDB = [x * 0.97001 - 29.99 if x is not None else np.nan for x in d18O]
            self.s.output['d18O_PDB'] = d18O_PDB
       
        
    def calculate_oxygen_PCP(self):
        """Caculate and return the d18O as a reuslt of Prior Carbonate Precip
        
        
        Use provided equations to calculate the the d18O"""
        
      
        # Check if PCarbP_d18O is explicitly set to True or False
        if self.s.settings['PCarbP_d18O'] == False: 
            print("PCarbP_d18O is not explicitly set to True. Skipping d18O calculation.")
        return  # Exit the function if PCarbP_d18O is not True
           
        print("WARNING: PCarbP will impact on d18O") 

        # Check precipitate mineralogy setting
        T = self.s.settings.get('temperature',298.15)
        
        # Get the initial Ca concentration (when f_ca = 1) and data for each step
        init = output_filter(self.s.output, 'step_desc', 'dissolve')
        
        if not init or 'Ca(mol/kgw)' not in init or len(init['Ca(mol/kgw)']) < 1:
            raise ValueError("Insufficient data for 'Ca(mol/kgw)' or 'step_desc' filter issue.")
            
        init_ca = init['Ca(mol/kgw)'][0]  # Initial concentration after dissolution
        ca_values = self.s.output.get('Ca(mol/kgw)', [])
        
        # Select d18O based on mineralogy
        if self.s.settings['precipitate_mineralogy'] == 'Calcite':
            d18O = self.s.output.get('d18O_Calcite', []) 
            alpha18H2O_CaCO3 =  np.exp((18.03/(T+273.15) - 0.03242)) #O'Neil, 1997
            alpha18HCO3_H2O = 1 / (((2590000 * ((T + 273.15) ** -2)) + 1.89) / 1000 + 1)
            alpha18HCO3_CaCO3 = alpha18HCO3_H2O * alpha18H2O_CaCO3
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
        
        excel_file = 'EventAnalyser.xlsx'
        
        file_path = self.s.settings['user_filepath']

        if not file_path:
            print('No user file path provided, skipping data loading.')
            return

        try:
            # Load the Excel file
            df = pd.read_excel(file_path)
            # Strip whitespace from the headers and search for 'd13C' (case-insensitive)
            df.columns = df.columns.str.strip()
            age_data = df['Age'].tolist()
            d13C_columns = [col for col in df.columns if 'd13c' in col.lower()]
            mgca_column = [col for col in df.columns if 'mgca' in col.lower()]


            if not d13C_columns:
                print("Excel file does not contain a 'd13C' column.")
                return
             
            d13C_data = df[d13C_columns[0]].dropna().tolist()
            MgCa_data = df[mgca_column[0]].dropna().tolist() if mgca_column else None
          

        except Exception as e:
            print(f"Error reading Excel file: {e}")
            return

        tolerance =   0.5
        mg_tolerance = 0.6  #Define mg_tolerance (adjust as needed)
        results = [] 
        all_results = []
        match_found = False  # Flag to check if any match is found


        # Select d13C_spel based on the mineralogy
        if self.s.settings['precipitate_mineralogy'] == 'Calcite':
            d13C_spel = self.s.output.get('d13C_Calcite', [])
            d13C_spel = d13C_spel[-1] if d13C_spel else None
            MgCa_spel = self.s.output.get('Mg/Ca(mol/mol)_Calcite', [])
            MgCa_spel = (MgCa_spel[-1])*1000 if MgCa_spel else None
        elif self.s.settings['precipitate_mineralogy'] == 'Aragonite':
            d13C_spel = self.s.output.get('d13C_Aragonite', [])
            d13C_spel = d13C_spel[-1] if d13C_spel else None
            MgCa_spel = self.s.output.get('Mg/Ca(mol/mol)_Aragonite', [])
            MgCa_spel = (MgCa_spel[-1])*1000 if MgCa_spel else None
        else:
            print('Unknown precipitate mineralogy')
            return

        if d13C_spel is None:
            print('No d13C data available in the model output.')
            return

        # Extract Soil_pCO2 for the current iteration
        soil_pCO2 = self.s.settings['soil_pCO2']
        d13Csoil = self.s.settings['soil_d13C']
        f_ca = self.s.output.get('f_ca',[])
        f_ca = f_ca[-1]
        cave_pCO2 = self.s.settings['cave_pCO2']
        gas_volume = self.s.settings['gas_volume']
        temp = self.s.settings['temperature']
        


        # Compare d13C_spel with d13C_data
        for index, d13C_value in enumerate(d13C_data): 
            adjusted_index = index + 1 
            residual = d13C_spel - d13C_value 
            all_results.append({
            'd13C_index': adjusted_index,
            'Age': age_data[index],
            'd13C': d13C_value,
            'CaveCalc d13C': d13C_spel,
            'd13C residual': residual,
            'MgCa': MgCa_data[index] if MgCa_data else None,
            'CaveCalc MgCa': MgCa_spel,
            'MgCa Residual': MgCa_spel - MgCa_data[index] if MgCa_data else None,
            'soil_pCO2 (ppmv)': soil_pCO2,
            'Soil d13C': d13Csoil,
            'cave_pCO2 (ppmv)': cave_pCO2,
            'f_{ca}': f_ca,
            'gas volume (L/kg)': gas_volume,
            'T(°C)': temp
        })

        if MgCa_data is None:
            if abs(residual) <= tolerance:
                results.append(all_results)
        elif MgCa_data is not None:
            MgCa_residual = MgCa_spel - MgCa_data[index]
            if abs(residual) <= tolerance and abs(MgCa_residual) <= mg_tolerance:
                results.append(all_results)
                match_found = True 
                        
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
                    self.results_df.to_excel(writer, sheet_name='Results', index=False)
                  print(f"Created new file '{excel_file}' and saved results.")
               else:
                # If the file exists, append new results to it 
                   with pd.ExcelWriter(excel_file, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                       startrow = writer.sheets['Results'].max_row if 'Results' in writer.sheets else 0
                       self.results_df.to_excel(writer, sheet_name='Results', index=False, header=startrow==0, startrow=startrow)

                       print(f"Appended results to existing file '{excel_file}'.")
                       print('Match!')

        # Save all results (without constraints) to a separate sheet
        try: 
            all_results_df = pd.DataFrame(all_results)

            if not os.path.exists(excel_file): 
                with pd.ExcelWriter(excel_file, engine='openpyxl') as writer: 
                    all_results_df.to_excel(writer, sheet_name='Results_No_Constraints', index=False) 
                    print(f"Created new file '{excel_file}' and saved all results without constraints.")
            else: 
                with pd.ExcelWriter(excel_file, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer: 
                    startrow = writer.sheets['Results_No_Constraints'].max_row if 'Results_No_Constraints' in writer.sheets else 0 
                    all_results_df.to_excel(writer, sheet_name='Results_No_Constraints', index=False, header=startrow == 0, startrow=startrow) 
                    print(f"Appended all results without constraints to existing file '{excel_file}'.")

        except Exception as e: 
            print(f"Error saving all results without constraints: {e}")
            
            

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
            
            

    

