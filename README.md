# CaveCalcV2.0: A software tool for forward modelling speleothem chemistry.
version 1 (https://github.com/Rob-Owen/cavecalc)

version 2 and CDALite is still under construction 🚧🚗  So code may be more prone to errors (please still reach out!)


[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Samhollowood/CaveCalcV2.0/main)
![GitHub License](https://img.shields.io/github/license/Samhollowood/CaveCalcV2.0)
![Github Release](https://img.shields.io/github/v/release/Samhollowood/CaveCalcV2.0?include_prereleases&tag=Beta)


## Table of Contents
- [Introduction](#introduction)
- [Features](#features)  
- [Installation](#installation)
- [Usage](#usage)
- [Carbonate Data Analyser](#CDA)
- [Output](#output)
- [Plotting](#plotting)
- [Citing this work](#citing-this-work)
- [Contributing, questions, and issues](#contributing-questions-and-issues)
- [License](#license)
- [References and Acknowledgements](#references-and-acknowledgements)


## **Introduction**
CaveCalcV2.0 is an updated forward modelling tool for simulating speleothem chemistry. It maintains the core fundamentals of the original while adding several new features and improvements for more robust and user-friendly modeling. This repository provides the following resources:

- Source code: `/cavecalc/`  
- Original example scripts: `/examples/`  
- New example scripts for API models: `/API_models/`  
- Scripts to open the Graphical User Interface (GUI): `/scripts/`  

**Key updates include:**
1. The new Carbonate Data Analyzer (CDA) mode.  
2. Speleothem aragonite precipitation.  
3. U/Ca as a proxy.

## **Features**

- **Forward modeling of speleothem chemistry** with updated tools and examples.
- **Easier installation** for Windows and Linux users. 
- **Carbonate Data Analyzer (CDA):** A mode for analysing and matching measured data with model outputs.  
- **Aragonite precipitation modeling** in speleothems.
- **Readable output** now produces a .csv format with the settings and results
- **Flexible plotting capabilities** for visualizing model and CDA outputs.  
- Supports **Python 3.0 and above** (tested with Python 3.10.12).  



## **Installation**

Installing CaveCalcV2.0 requires the use of the terminal (Mac/Linux) or command prompt (Windows). 

The git command (https://git-scm.com/downloads) is recommened for this particular method of installation. Alternatively, users may download the repository as a zip-file for this repository locally.

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
To activate the base anaconda environment. Or you may wish to use your own environment 

4. Install the CaveCalcV2.0 package:
```shell
pip install .
```

Or if you would rather install the package as an .egg file (NOTE: .egg as a method of installation will be deprecated soon):
```shell
python setup.py install
```

If all has worked and no errors popped up, then CaveCalcV2.0 has installed!

5. You can verify the installation by running an example:
```shell
cd examples/
```
```shell
python example1.py
```

6. You can now open the GUI by:
```shell
cd ../scripts
```
```shell
python cc_input_gui.py
```

## Usage

Once installation is complete, the **CaveCalcV2.0** module will be available in your Python or Anaconda environment.  
You can run either a **single model** or a **batch of models** using any of the following methods:

### 1. Graphical User Interface (GUI)

The GUI provides an intuitive interface for setting model inputs and running simulations.  
Once inputs are defined, users can click:

- **Run CaveCalc Only!** — to run the CaveCalc model by itself  
- **Run CaveCalc With CDA!** — to run the CaveCalc model alongside the Carbonate Data Analyser (CDA) mode

Both single and batch model runs are supported in the GUI. To run a batch, users can provide arrays or multiple values for input parameters.

### 2. Python Scripts

For scripting-based workflows, CaveCalc can also be run via:

- `run_models.py` (in the `API_models/` folder)  
- `run_CDA.py` (also in `API_models/`)  
- Custom `.py` scripts using these files as templates

#### `run_models.py`

This script includes a `settings` dictionary containing **all available model inputs** set to their default values.  
You can **add, remove, or modify** any inputs to tailor your simulation. If a key is removed, the value will default to what’s defined in `cavecalc/data/defaults.py`.

#### `run_CDA.py`

Similar in structure to `run_models.py`, this script is optimized for the new **CDA mode**, focusing on a core set of inputs. Some are defined as arrays to support batch processing and exploration of parameter space.

A full list of model inputs is provided in **`manual.pdf`**, Table 3.

### 3. Running Scripts from the Terminal

To execute a model run, open your terminal or command prompt, navigate to the appropriate directory, and run:

```bash
cd API_models
python run_models.py
```

### Aragonite Precipitation 
In the GUI, users should navigate to the calcite/aragonite heading. Here they can define `Aragonite` as the precipitate mineralogy via a drop-down menu. If the user is running models via a .py file, then defining the model_name: `precipitate_mineralogy` as a string `Aragonite' will initialise Aragonite precipitation during model runs. There is no requirement to actively change the database files. The precipitate_mineralogy variable feeds into CaveCalcV2.0 whether the Calcite.dat or Aragonite.dat database should be loaded.

##Carbonate Data Analyser (CDA)
The new Carbonate Data Analyser (CDA) mode aims to automate the comparison between CaveCalcV2.0 model output and measured speleothem data. There are three key steps to the CDA:

- **`user_filepath`**: Users are required to important their measured speleothem data by providing the path as a string.  
- **`tolerance_X`**: Users can optionally define tolerance values for proxies (e.g., `d13C`, `d18O`, `d44Ca`, `MgCa`, `SrCa`, `BaCa`, `UCa`). These tolerance intervals define what consitutues a match.  
- **Model Inputs**: Users will need to define model input variables as per standard CaveCalc model runs, focusing on model inputs they want to constrain.  

A template (`Example_input.csv`) is provided for the measured speleothem data file. This can be modified by adding/removing proxies and rows. 

Within the GUI, users can find the required inputs for the CDA in the CDA Settings heading, which allows users to import their measured data and define tolerance intervals. The rest of the GUI can be used to define the model input variables.

### Optional: Defining Output Directory
By default, outputs are saved in `./cavecalc_output/`. Alternatively, the user can specify the output directory by defining the `out_dir` key in the settings dictionary (`s = {}`). Users may also simply define an output directory on the GUI. 

### Running models
After setting the model inputs, importing the measured data, and setting the tolerance intervals, to run the CDA mode:
```shell
cd CaveCalcV2.0/API_models/
python run_CDA.py
```
If you do not wish to use the CDA, there is no need to define `user_filepath`. Simply define the model inputs and optionally, `out_dir`, in the settings dictionary and run:

```shell
python run_models.py
```


### When the CDA is functioning correctly:
It will print:

```shell
CDA was initialised for the first time in the output directory. Created new 'Path/to/Output_Directory/CDA_Results/All_outputs.csv
```
The CDA creates a new CDA_Results folder within the output directory, which will store matches in a .csv file.

Provided the output directory is left unchanged, runninng extra batches of models will append the results of the CDA AND not replace the previous batch of runs.


## Output
When running **CaveCalcV2.0**, whether it be with the CDA, or without, three model output files are generated:

1. **`settings.pkl`**  
   A pickle file that stores all the input settings for the model.

2. **`results.pkl`**  
   A pickle file that contains all the model results.

3. A new **`settings_results.csv`**  
   This is a new CSV file that consolidates both the input settings and the model outputs in a single, readable format. Model outputs can be osberved for each stage of speleothem chemistry per model (e.g., soil-water equilibriation, bedrock dissolution and C02-degassing and carbonate precipitation). 

There are several model output keys, and the definition of each can be found in the manual.pdf, Table 4. Each model ouput willl have an array of values, which will represent different parts of speleothem chemistry (i.e the values after soil-water equilibriation, bedrock dissolution and C02-degassing steps). 

If the CDA was initialised, it will create a CDA_Results folder within the output directory with additional output files:
```shell
cd /path/to/out_dir/CDA_Results/
```

containing:

1. **`Matches.csv`**  
   A CSV file that stores the inputs and outputs of all matches with the measured data (and the residual)

2. **`All_outputs.csv`**  
   A CSV file that stores all inputs and outputs of the CDA model runs (and the residuals)

3. **`Tolerance.csv`**  
   A CSV file that stores the tolerance intervals used for the measured proxy data in the CDA

4. **`Input_ranges.csv`**  
   A CSV file that stores the range of model inputs used in the CDA model runs


## Plotting
CaveCalcV2.0 comes with built-in functionalities for generating plots, which are available in the `analyse.py` module. Users can initialize this file and generate plots after running models, or even delve into archived models to produce plots. To do this via python scripting, add the following lines to the bottom of the run_CDA.py or run_models.py script:

```python
import cavecalc.analyse as cca

out_dir = 'path/to/output/' #Path to archived output data

e = cca.Evaluate()  # Initializes the Evaluate class
e = load_data(out_dir) #Load data 
e1 = e.filter_by_index(0, n=True) #Filters out first model step

#Example plot of fCa on x-axis and d13C_Calcite on y-axis. Different lines will be coloured depending on the soil_pCO2 (i.e. inputs), and added to the legend
e1.plot_models(x_key='f_ca', y_key='d13C_Calcite', label_with = 'soil_pCO2')
```
This function plots model outputs with an output key on the x-axis and y-axis, with different coloured lines for each input value within label_with. In the example above, the d13C_Calcite will be plotted against f_ca, with each colored line corresponding to a specific input value of soil_pCO2. These can be replaced with any outputs for the x_key and y_key and inputs for label_with. Users can observe all the model output keys in the manual Table 3. Note, that the model key outputs will change slightly whether Calcite or Aragonite is the precipitate_mineralogy.

There is also an option to plot by points:
```python
import cavecalc.analyse as cca

out_dir = 'path/to/output/' #Path to archived output data

e = cca.Evaluate()  # Initializes the Evaluate class
e = load_data(out_dir) #Load data 

#Example plot of fCa on x-axis. d13C on y-axis. Plot is scatter, it is taking the value of f_ca and d13C_Calcite at the equilibrium with cave air value (final index i.e. point_index=-1)
e.plot_points(x_key='f_ca', y_key='d13C_Calcite', point_index=-1, label_with = 'soil_pCO2')
```

By default, after a **CDA** run, three plots are generated automatically. However, these plots can also be generated manually. To do so, users can apply this example to any archived CDA Data:

```python
# Import modules
import cavecalc.analyse as cca

# Initialize the Evaluate class
e = cca.Evaluate()

# Define path to measured data and archived output directory
user_filepath = 'path/to/data.csv' # Path to the measured data used in the CDA run,
out_dir = 'path/to/out_dir/CDA_Results/' # Path to the archived output directory containing CDA_Results,

# Plot CDA_Results
plot = e.plot_CDA(user_filepath, out_dir)
```

It is important to note that the plotting feature for CDA does not plot ALL input variables, only a select amount. However, all input variables can be found in the Matches.csv file.

## Citing this work
If you use CaveCalcV2.0 please cite .....

## Contributing, questions, and issues
If you have any suggestions, improvements, questions, or comments - please create an issue, start a discussion, or [get in touch](mailto:samuel.hollowood@earth.ox.ac.uk).

## License
This project is licensed under the MIT license

## References and Acknowledgements

This repository uses the following open-source software libraries:






Samuel J. Hollowood is funded by a UKRI NERC DTP Award (NE/S007474/1) and gratefully acknowledges their support.

