# CaveCalcV2.0: A software tool for forward modelling speleothem chemistry.
version 1 (https://github.com/Rob-Owen/cavecalc)

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Samhollowood/CaveCalcV2.0/main)
![GitHub License](https://img.shields.io/github/license/Samhollowood/CaveCalcV2.0)
![GitHub Release](https://img.shields.io/github/v/release/Samhollowood/CaveCalcV2.0)

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)  
- [Installation](#installation)
- [Usage](#usage)
- [Output](#output)
- [Plotting](#plotting)
- [Citing this work](#citing-this-work)
- [Contributing, questions, and issues](#contributing-questions-and-issues)
- [License](#license)
- [References and Acknowledgements](#references-and-acknowledgements)


## **Introduction**
CaveCalcV2.0 is an updated forward modeling tool for simulating speleothem chemistry. It introduces several new features and improvements for more robust and user-friendly modeling. This repository provides the following resources:

- Source code: `/cavecalc/`  
- Example scripts: `/examples/`  
- API model run examples: `/API_models/`  
- Scripts for the Graphical User Interface (GUI): `/scripts/`  

**Key updates include:**
1. The new Carbonate Data Analyzer (CDA) mode.  
2. Speleothem aragonite precipitation.  
3. U/Ca as a proxy.

## **Features**

- **Forward modeling of speleothem chemistry** with updated tools and examples.  
- **Carbonate Data Analyzer (CDA):** A mode for analysing and matching measured data with model outputs.  
- **Aragonite precipitation modeling** in speleothems.  
- **Flexible plotting capabilities** for visualizing outputs.  
- Supports **Python 3.0 and above** (tested with Python 3.10.12).  



## **Installation**

Follow these steps to install CaveCalcV2.0 (
NOTE: A key difference to installation on CaveCalcV2.0 to CaveCalc is that the installation script automatically configures and compiles the system-specific .dll/.so file for interaction with the IPhreeqc COM server):

1. Clone the repository:
```shell
git clone https://github.com/Samhollowood/CaveCalcV2.0.git
```
   
2. Go to directory:
```shell
cd CaveCalcV2.0
```

3. If you would like to install into anaconda (optional):
```shell
conda activate base
```

3a. Or if you would like to create a local environment
```shell
conda create -n cavecalc_env 
conda activate cavecalc_env
```

4. Install the CaveCalcV2.0 package:
```shell
python setup.py install
```

5. Verify installation by running example:
```shell
cd examples/
```
```shell
python example1.py
```

6. Open the GUI by:
```shell
cd ../scripts
```
```shell
python cc_input_gui.py
```



## Usage

More in-depth examples of running single models, multiple models, and models with the Carbonate Data Analyser (CDA) are provided in the **manual** (). Users can run models via the `run_models.py` script in the `API_models/` directory or the CDA using `run_CDA.py` in the same location. `run_models.py` comes with default model inputs, whereas `run_CDA.py` contains a select number of inputs that vary in a range (to help guide the user on the CDA). For each, inputs can be added, removed and edited. Integrated development environments (IDEs) like **Spyder** and **Jupyter Notebook** are recommended for easily editing `.py` scripts. For further guidance, refer to the **manual** (), which includes a table of all the available model inputs, their model names, realistic ranges, and their influence on speleothem chemistry.

### Defining Inputs for the CDA
Before running the CDA mode, specify the following in the settings dictionary ( `s = {}`) within `API_models/run_CDA.py` :

- **`user_filepath`**: Define this key in the settings dictionary and set it to the path of your measured speleothem data file.
- **`tolerance_X`**: Where X is d13C, d18O, d44Ca, MgCa, SrCa, BaCa, or UCa. You can modify the tolerance values or remove tolerance intervals proxies that are not part of your measured data.
- **model inputs**: These are standard model inputs as per standard CaveCalc model runs (Owens et al., 2018). These can be changed/added in the run_CDA.py

### Optional: Defining Output Directory
For both standard model runs and the CDA, you can specify the output directory by defining the `out_dir` key in the settings dictionary (`s = {}`).

### Running the Scripts
After settings the model inputs, importing the measured data, and settings the tolerance intervals, to run the CDA mode:
```shell
cd CaveCalcV2.0/API_models/
python run_CDA.py
```

If you do not wish to use the CDA, there is no need to define `user_filepath`. Simply define the models inputs and optionally, `out_dir`, in the settings dictionary and run:

```shell
python run_models.py
```


### When the CDA is functioning correctly:

It will print:

```shell
CDA is initialised
```
It will then create a CDA Results folder in the output directory, which will store matches in a .csv file.
For the first match with the measured data, it will print:

```shell
Created new file path/to/out_dir/CDA Results/Matches.csv and saved results.
```


## Output
When running **CaveCalcV2.0**, three outputs are generated:

1. **`settings.pkl`**  
   A pickle file that stores all the input settings for the model.

2. **`results.pkl`**  
   A pickle file that contains all the model results.

3. **`settings_results.csv`**  
   A CSV file that consolidates both the input settings and the model outputs in a single, readable format.

If the CDA is initialised, it will create a CDA Results folder:
```shell
cd /path/to/out_dir/CDA Results/
```

containing:

1. **`Matches.csv`**  
   A CSV file that stores the inputs and outputs of all matches with the measured data (and the residual)

2. **`All_outputs.csv`**  
   A CSV file that stores all inputs and outputs of the CDA model runs (and the residuals)

3. **`Tolerance.csv`**  
   A CSV file that stores the tolerance intervals used for the measured proxy data in the CDA

4. **`Input_ranges.csv`**  
   A CSV file that stores the range of model inputs used in the CDA modle runs


## Plotting
CaveCalc comes with built-in functionalities for generating plots, which are available in the `analyse.py` module. Users can initialize this file and generate plots after running the model. To do this, add the following lines to the bottom of the run_CDA.py or run_models.py script:

```python
import cavecalc.analyse as cca


e = cca.Evaluate()  # Initializes the Evaluate class in analyse.py
e1 = e.filter_by_index(0, n=True) #Filters out first model step
e1.plot_models(x_key='f_ca', y_key='d13C_Calcite', label_with = 'soil_pCO2') #Example plot of fCa on x-axis. d13C on y-axis. Different lines will be coloured depending on the soil_pCO2, and added to the legend
```
Users can observe all the model output keys in the manual.

There is also an option to plot by points (not lines):
```python
import cavecalc.analyse as cca

e = cca.Evaluate()  # Initializes the Evaluate class in analyse.py
e.plot_points(x_key='f_ca', y_key='d13C_Calcite', point_index=-1, label_with = 'soil_pCO2') #Example plot of fCa on x-axis. d13C on y-axis. Plot is scatter, it is taking the value of f_ca and d13C_Calcite at the solution in equilibriium (final index i.e. point_index=-1
```

By default, after a **CDA** run, three plots are generated automatically. However, these plots can also be generated manually. To do so, users need to add the following lines to their `run_CDA.py` script after setting up the model runs:

```python
import cavecalc.analyse as cca

e = cca.Evaluate()  # Initializes the Evaluate class in analyse.py
plot = e.plot_CDA(s['user_flowpath'], s['out_dir'])
```

## Citing this work
If you use CaveCalcV2.0 please site .....

## Contributing, questions, and issues
If you have any suggestions, improvements, questions, or comments - please create an issue, submit a pull request, or [get in touch](mailto:samuel.hollowood@earth.ox.ac.uk).

## License
This project is licensed under the MIT license

## References and Acknowledgements

This repository uses the following open-source software libraries:






Samuel J. Hollowood is funded by a UKRI NERC DTP Award (NE/S007474/1) and gratefully acknowledges their support.

