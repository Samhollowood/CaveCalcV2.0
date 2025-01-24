#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 23 14:55:49 2024

@author: samhollowood - please contact samuel.hollowood@bnc.ox.ac.uk for any questions

This code is used to provide a user with an easy way to run the CDA mode 
as part as a .py script 

The settings of the model can be found via s = {}.

Please change/add inputs to suit your study. Refer to manual for full list of available inputs

Contact me for any more information/debugging/guidance.
"""

'Import modules'
from cavecalc.forward_models import ForwardModels
import cavecalc.analyse as cca


'Important note before running'
'Change users_filepath and out_dir in the settings dictionary s = {}'


'STEP 1: Define the settings for the CDA'        
s =  {'soil_d13C': -25,  #DEFAULT | end-member soil gas d13C (‰, VPDB)
      'soil_pCO2': [260,410,600,1000,2000,3000,4000,5000,6000,8000], #NON-DEFAULT - example of placing values in a list
      'atm_d18O': -10 #DEFAULT | rainwater isotopic composition in VSMOW
      
      #Soil metals
      'soil_Ba':              0,    	#DEFAULT | soil water Ba concentration (mmol/kg water)
      'soil_Ca':              0,    	#DEFAULT | water Ca concentration (mmol/kg water)
      'soil_Mg':              0,    	#DEFAULT | soil water Mg concentration (mmol/kg water)
      'soil_Sr':              0,    	#DEFAULT | soil water Sr concentration (mmol/kg water)
      'soil_U':               0,       #DEFAULT | soil water U concentration (mmol/kg water)
      'soil_d44Ca':           0,       #DEFAULT | soil water Ca d44Ca (‰, 915a)

      # Bedrock Chemistry *PLEASE CHANGE IF TRACE METALS ARE WITHIN EVENANALYSER*
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
      'gas_volume':		   [0,50,100,150,200,250,300,350,400,450,500],	#NON-DEFAULT  Volume of soil gas present during bedrock dissolution (L/kg water)
     
      # General
      'temperature':          [5,10,15,20],     #NON-DEFAULT | Temperature(°C)
      'kinetics_mode':       'multi_step_degassing',   #DEFAULT | Specifies how to run the model (see types_and_limits.py for options)

      #cave air 
      'cave_pCO2': [260,410,1500,2500,4500,5550,6500],
      
      #CDA Mode
      'user_filepath': "path/to/data",       # Please change for EventAnalyser mode
      'tolerance_d13C': 0.5,      #DEFAULT | Tolerance level for d13C (‰, VPDB)
      'tolerance_d18O': 0.5,      #DEFAULT | Tolerance level for d18O (‰, VPDB)
      'tolerance_DCP':  1.5,      #DEFAULT | Tolerance level for DCP (%)
      'tolerance_d44Ca': 0.5,     #DEFAULT | Tolerance level for d44Ca (‰, 915a)
      'tolerance_MgCa': 0.3,      #DEFAULT | Tolerance level for MgCa (mmol/mol)
      'tolerance_SrCa': 0.3,      #DEFAULT | Tolerance level for SrCa (mmol/mol)
      'tolerance_BaCa': 0.3,      #DEFAULT | Tolerance level for BaCa (mmol/mol)
      'tolerance_UCa': 0.3,       #DEFAULT | Tolerance level for UCa (mmol/mol)

      #output directory
      'out_dir' = './path/to/CDA'

     }

# Run model and CDA
model = ForwardModels(settings=s, output_dir= s['out_dir'])
model.run_models()
model.save()



