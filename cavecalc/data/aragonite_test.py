#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 26 14:55:49 2023

@author: samhollowood
"""
import numpy as np
from scipy import io
import os

from cavecalc.forward_models import ForwardModels
import cavecalc.analyse as cca



#Mixing Line 1
#260, 410, 600, 800, 1000, 2000, 3000, 4000, 5000, 6000, 8000
#-6.33, -13.05, -16.74, -18.72, -19.93, -22.31, -23.11, -23.51, -23.75, -23.90, -24.10

#Mixing Line 2
#260, 410, 600, 800, 1000, 2000, 3000, 4000, 5000, 6000, 8000
#-6.32, -11.94 ,-15.03,-16.70 , -17.70, -19.70, -20.37, -20.70, -20.90, -21.03, -21.20

#Mixing Line 3
#260, 410, 600, 800 1000, 2000, 3000, 4000, 5000, 6000, 8000
#-6.26, -14.10 ,-18.41, -20.73 ,-22.13, -24.91, -25.84, -26.31, -26.59, -26.77, -27.00


#
## STEP 1: Define the non-default settings and run the model
#

s =  {  'bedrock_mineral' :     ['Calcite'],
        'bedrock_MgCa':         107,       
        'bedrock_SrCa':         0.6,       #The reason we do not incorporate Sr/Ca is because the D(Sr) is susceptible to vary
        #'bedrock_d44Ca':        0.58,     #No measured d44Ca in Chile samples
        'temperature':          [25],  #There is an argument above to use todays metadata temperature 

        'soil_pCO2':            [8000], 
        'soil_d13C':             -25, 
        'soil_R14C':            [100], #85 90
        'cave_pCO2' :           [260],
        'cave_R14C':            100, #default value for R14C, as we are only interested in the DCP
        'gas_volume':           [250], #, 250], #, 300, 350, 400, 450, 500], # 

        'atm_R14C':             100, 
        'atm_d13C':             -6.7, #-66.32 Mixing Line 2 and, -6.26 For Mixing Line 3
        #or just -6.7?
        'atm_pCO2':             260,#Shin et al., 2022 8-7.6ka
        #'atmo_exchange':        [0, 0.25, 0.5], # 
        #'bedrock_pyrite':       [0, 0.00001] #, 0.0001
        #'kinetics_mode':         'diss_only' 
        'co2_decrement':          0.5, #default is 5
        'database': 'oxotope_aragonite.dat',
     }

dir = './aragonite_test/' # directory to save model output
p = ForwardModels(  settings =      s,
                    output_dir  =   dir )   # initialise the model
p.run_models()                              # run the model
p.save()                                    # save the model output

#
## STEP 2: Load model output and save new data formats
#
e = cca.Evaluate()      # initialise an 'Evaluate' object
e.load_data( dir )      # load data from dir
f = e.filter_by_index(-1) 

#e.save_all_mat( dir ) #save data to a .mat file
f.save_all_mat( dir )

print('Saved .mat files')

#.mat file will be hidden command + shift + .