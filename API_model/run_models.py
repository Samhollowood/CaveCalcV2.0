#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 23 14:55:49 2024

@author: samhollowood - please contact samuel.hollowood@bnc.ox.ac.uk for any questions

This code is used to provide a user with an easy way to run models 
as part as a .py script. This produces a .csv output of each model.

The settings of the model can be found via s = {}. Most inputs are in their default values

Please change the values to suit your study. Multiple values in a list for one
variable will cause several models to be ran.

"""

'Import modules'
from cavecalc.forward_models import ForwardModels
import cavecalc.analyse as cca


'STEP 1: Define the settings'        
s =  {#Atmospheric  Gas End-member  
      'atm_O2': 0.21,   #DEFAULT | atmospheric O2 (%) 
      'atm_d18O': -10,  #DEFAULT | Rainfall d18O (‰,SVMOW)
      'atm_pCO2': 270,  #DEFAULT | atmospheric pCO2 (ppmv)
      'atm_d13C': -7,   #DEFAULT | atmospheric CO2 d13C (‰,VPDB)
      'atm_R14C': 100,  #DEFAULT | atmospheric CO2 R14C (pmc)
      
      #Soil Gas End-member 
      'soil_O2': 0,      #DEFAULT | soil end-member O2 (%)
      'soil_R14C': 100,  #DEFAULT | soil end-member R14C (pmc)
      'soil_d13C': -25,  #DEFAULT | end-member soil gas d13C (‰, VPDB)
      'soil_pCO2': [1000,2000,3000,4000,8000], #Example of placing values in a list
      
      #Atmospheric and soil gas mixing 
      'atmo_exchange':		0,	#DEFAULT | Atmospheric contribution to soil gas CO2 (0-1)
      'init_O2':     'mix',     #DEFAULT | actual soil gas O2 content (%)
      'init_R14C':		'mix',	#DEFAULT | actual soil gas R14C* (pmc)
      'init_d13C':		'mix',	#DEFAULT | actual soil gas d13C* (‰, VPDB)
      'init_pCO2':		'mix',	#DEFAULT | actual soil gas pCO2* (ppmv). 'atm' to equilibrate with atmospheric, 'soil' to equilibrate with soil_pCO2 (after atmospheric mixing)
 
      #Soil metals
      'soil_Ba':              0,    	#DEFAULT | soil water Ba concentration (mmol/kg water)
      'soil_Ca':              0,    	#DEFAULT | water Ca concentration (mmol/kg water)
      'soil_Mg':              0,    	#DEFAULT | soil water Mg concentration (mmol/kg water)
      'soil_Sr':              0,    	#DEFAULT | soil water Sr concentration (mmol/kg water)
      'soil_U':              0,       #DEFAULT | soil water U concentration (mmol/kg water)
      'soil_d44Ca':           0,       #DEFAULT | soil water Ca d44Ca (‰, 915a)

      # Bedrock Chemistry
      'bedrock_BaCa':         0,            #DEFAULT | bedrock Ba/Ca (mmol/mol)
      'bedrock_MgCa':         0,            #DEFAULT | bedrock Mg/Ca (mmol/mol)
      'bedrock_SrCa':         0,            #DEFAULT | bedrock Sr/Ca (mmol/mol)
      'bedrock_UCa':          0,            #DEFAULT | bedrock U/Ca (mmol/mol)
      'bedrock_d13C':         0,            #DEFAULT | bedrock d13C (‰, VPDB)
      'bedrock_d18O':         0,            #DEFAULT | bedrock d18O (‰, VSMOW)
      'bedrock_d44Ca':        0,            #DEFAULT | Bedrock d44Ca (‰, SRM 915a)
      'bedrock_mineral':      'Calcite',  #DEFAULT |  Bedrock mineralogy ('Calcite','Dolomite', or 'Aragonite)

      #Aragonite/Calcite Mode 
      'precipitate_mineralogy': 'Calcite', #DEFAULT | Speleothem mineralogy ('Calcite' or 'Aragonite')    

      # Bedrock Dissolution Conditions
      'bedrock':              10,   #DEFAULT | moles bedrock (defaults to excess)
      'bedrock_pyrite':       0,	        #DEFAULT | moles of pyrite present during bedrock dissolution
      'gas_volume':		      250,	#DEFAULT  Volume of soil gas present during bedrock dissolution (L/kg water)
      'reprecip':             False,    # Allow calcite re-precipitation during bedrock dissolution
      
      # Cave Air | default kinetics mode doesn't involve cave air equilibriation 
      #Kinetics mode of single step degassing initiliases interaction with the cave air
      'cave_O2':             0.21,    
      'cave_pCO2':		       1000,
      'cave_d13C':		       -10,
      'cave_R14C':		       100,
      'cave_d18O':		       0,
      'cave_air_volume':      0,
       
       # General
      'temperature':          20,     #DEFAULT | Temperature(°C)
      'kinetics_mode':       'multi_step_degassing',   #DEFAULT | Specifies how to run the model (see types_and_limits.py for options)

      #Scripting Options
      'co2_decrement':        0.5,    #DEFAULT | Fraction of CO2(aq) removed on each degassing step
      'calcite_sat_limit':    1,      #DEFAULT | Only used if kinetics_mode = 'ss'. CaCO3 only precipitates when saturation index exceeds this value. 
       
     }

dir_model = './run_models_output/' # directory to save model output 

# Run model and EventaAnalyser
model = ForwardModels(settings=s, output_dir= dir_model)
model.run_models()
model.save()

# Save model outputs as .csvs
e = cca.Evaluate()
e.load_data(dir_model)
e.save_csvs(dir_model)


