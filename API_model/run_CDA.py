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
import os


'Important note before running'
'Change users_filepath and out_dir in the settings dictionary s = {}'


'STEP 1: Define the settings for the CDA'        
s =  {#Environmental model inputs
      'soil_d13C': [-18,-21,-25],
      'soil_pCO2': [1000, 2000, 5000, 8000],
      'gas_volume': [0,50, 200, 500],
      'cave_pCO2': [260],
      'atm_d18O': [-35.5,-36], #Conveted to VPDB
      'bedrock_MgCa': [50,100,150],

      #And any other environmental model inputs (see run_models.py)
      
      #CDA Mode
      'user_filepath':  os.path.abspath("Example_CDA.csv"),      # Provide path to measured data
      'tolerance_d13C': 0.5,      #DEFAULT | Tolerance level for d13C (‰, VPDB)
      'tolerance_d18O': 0.5,      #DEFAULT | Tolerance level for d18O (‰, VPDB)
      'tolerance_DCP':  1.5,      #DEFAULT | Tolerance level for DCP (%)
      'tolerance_d44Ca': 0.5,     #DEFAULT | Tolerance level for d44Ca (‰, 915a)
      'tolerance_MgCa': 0.3,      #DEFAULT | Tolerance level for MgCa (mmol/mol)
      'tolerance_SrCa': 0.3,      #DEFAULT | Tolerance level for SrCa (mmol/mol)
      'tolerance_BaCa': 0.3,      #DEFAULT | Tolerance level for BaCa (mmol/mol)
      'tolerance_UCa': 0.3,       #DEFAULT | Tolerance level for UCa (mmol/mol)

      #output directory
      'out_dir':'Example_CDA' #Change to an output directory you like

     }

# Run model and CDA
model = ForwardModels(settings=s, output_dir= s['out_dir'])
model.run_models()
model.save()



