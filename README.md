# CaveCalcV2.0: A software tool for forward modelling speleothem chemistry

Version 1: https://github.com/Rob-Owen/cavecalc

Version 2 and CDA are under active development, so code may be more prone to errors than a stable release (please still reach out with anything you find).

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Samhollowood/CaveCalcV2.0/main)
![GitHub License](https://img.shields.io/github/license/Samhollowood/CaveCalcV2.0)
![Github Release](https://img.shields.io/github/v/release/Samhollowood/CaveCalcV2.0?include_prereleases&tag=Beta)

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Model Inputs](#model-inputs)
- [Carbonate Data Analyser](#carbonate-data-analyser)
- [Aragonite Precipitation](#aragonite-precipitation)
- [Partition Coefficient Overrides](#partition-coefficient-overrides)
- [The d18O Reference Scale: VSMOW vs VPDB](#the-d18o-reference-scale-vsmow-vs-vpdb)
- [Output](#output)
- [Plotting](#plotting)
- [Citing this work](#citing-this-work)
- [Contributing, questions, and issues](#contributing-questions-and-issues)
- [License](#license)
- [References and Acknowledgements](#references-and-acknowledgements)

## Introduction

CaveCalcV2.0 is an updated forward-modelling tool for simulating speleothem chemistry. It keeps the core fundamentals of the original CaveCalc (Owen et al., 2018) while adding several new features aimed at more robust, flexible and user-friendly modelling. This repository provides:

- Source code: `/cavecalc/`
- Original example scripts: `/examples/`
- Example scripts for API-based modelling: `/API_models/`
- Scripts to open the Graphical User Interface (GUI): `/scripts/`

**Key updates in CaveCalcV2.0:**
1. The Carbonate Data Analyser (CDA) mode, for matching model output against measured speleothem data.
2. Aragonite speleothem precipitation, alongside calcite.
3. U/Ca as a trace-element proxy.
4. User-overridable partition coefficients and fractionation factors (`D_MgCa`, `D_SrCa`, `D_BaCa`, `D_UCa`, `D_44Ca`), independent of mineralogy.

## Features

- **Forward modelling of speleothem chemistry**, with updated tools and examples.
- **Easier installation** for Windows and Linux users.
- **Carbonate Data Analyser (CDA):** automatically matches measured speleothem data against a batch of model runs.
- **Aragonite precipitation modelling**, alongside the default calcite pathway.
- **Site-specific partition coefficients and fractionation factors:** override any database default for Mg/Ca, Sr/Ca, Ba/Ca, U/Ca or d44Ca, without editing the thermodynamic database files.
- **Readable output**, consolidated into a single `.csv` of settings and results per run.
- **Flexible plotting**, for both raw model output and CDA results.
- Supports **Python 3.0 and above** (tested with Python 3.10.12).

## Installation

Installing CaveCalcV2.0 requires a terminal (Mac/Linux) or command prompt (Windows).

Git (https://git-scm.com/downloads) is recommended for installation. Alternatively, download the repository as a ZIP file and extract it locally.

1. Clone the repository:
```shell
git clone https://github.com/Samhollowood/CaveCalcV2.0.git
```

2. Move into the directory:
```shell
cd CaveCalcV2.0
```

3. (Optional) Activate an Anaconda environment:
```shell
conda activate base
```
Or use your own environment.

There are two ways to install: `pip install .` (step 4a), which does not generate an `.egg` file, or `python setup.py install` (step 4b), which does. `setup.py install` and `.egg` files are expected to be deprecated in future versions of setuptools/pip, so `pip install .` is the preferred route going forward.

**4a.** Install the package:
```shell
pip install .
```
Then configure phreeqpy (**non-Mac users only**):
```shell
python cavecalc/configure_phreeqpy.py
```
If no errors appear, CaveCalcV2.0 has installed correctly.

**4b.** Alternatively:
```shell
python setup.py install
```
This configures phreeqpy automatically as part of setup. You may need to install `setuptools` first.

5. Verify the installation by running an example:
```shell
cd examples/
python example1.py
```

6. Open the GUI:
```shell
cd ../scripts
python cc_input_gui.py
```

## Usage

Once installed, the **CaveCalcV2.0** module is available in your Python/Anaconda environment. You can run a **single model** or a **batch of models** via:

### 1. Graphical User Interface (GUI)

The GUI exposes model inputs grouped into collapsible sections (Atmospheric End-member, Soil Gas End-member, Bedrock Chemistry, Aragonite/Calcite Mode, Partition Coefficient Overrides, CDA Settings, and so on). Once inputs are set, click:

- **Run CaveCalc Only!** - runs the model by itself.
- **Run CaveCalc With CDA!** - runs the model alongside the Carbonate Data Analyser.

Both single and batch runs are supported in the GUI: giving a field multiple, space-separated values runs the model over all combinations of those values.

### 2. Python Scripts

For scripting-based workflows, use:

- `run_models.py` (in `API_models/`)
- `run_CDA.py` (also in `API_models/`)
- Custom `.py` scripts using either as a template

#### `run_models.py`

Contains a `settings` dictionary with every model input set to its default value (from `cavecalc/data/defaults.py`). Add, remove, or modify any entry to tailor the run; removing a key simply falls back to its default.

#### `run_CDA.py`

Structured like `run_models.py` but set up for CDA mode: a core set of inputs, some given as lists to support batch exploration of parameter space, matched against the measured data in `Example_CDA.csv`.

### 3. Running scripts from the terminal

```bash
cd API_models
python run_models.py
```

## Model Inputs

Every model input is declared in three places that must stay in sync:

- `cavecalc/data/defaults.py` - the default value used if a setting isn't specified.
- `cavecalc/data/types_and_limits.py` - the accepted type/range/options for validation.
- `cavecalc/gui/mapping.py` - the human-readable label shown in the GUI.

A setting is only usable (via `SettingsObject`, `SettingsMaker`, or the GUI) once it appears in all three. `cavecalc/gui/layout.py` additionally places each GUI-exposed setting into a numbered section and widget type (see the module docstring for the section/type codes).

Broad input categories include:
- Atmospheric, soil-gas and cave-air end-members (pCO2, O2, d13C, R14C, d18O)
- Soil-gas mixing (`init_*` settings, `atmo_exchange`)
- Soil and bedrock trace-metal/isotope chemistry (Mg, Sr, Ba, U, d44Ca, d13C, d18O)
- Bedrock dissolution conditions (`bedrock`, `bedrock_pyrite`, `gas_volume`, `reprecip`)
- General run settings (`temperature`, `kinetics_mode`, `precipitate_mineralogy`, `co2_decrement`, `calcite_sat_limit`)
- Partition coefficient / fractionation factor overrides (`D_MgCa`, `D_SrCa`, `D_BaCa`, `D_UCa`, `D_44Ca`) - see [below](#partition-coefficient-overrides)
- CDA settings (`user_filepath`, `tolerance_*`)
- File I/O (`out_dir`, `database`, `phreeqc_log_file`)

A full reference table of every input, its units and its meaning is intended for `manual.pdf`, Table 3 (consult that document for the complete, authoritative list; this guide summarises the categories and documents the newest settings in detail, since those postdate the manual).

## Carbonate Data Analyser

The **Carbonate Data Analyser** (CDA) automatically compares CaveCalcV2.0 model output against measured speleothem data, across a batch of model runs, and reports which runs fall within tolerance of the measured values.

### Step 1: Import measured data

Point `user_filepath` at your data file:
```python
'user_filepath': 'Path/to/template.csv'
```
You don't need to populate every column. CDA only compares model output to the proxies present in the file. Supported proxy columns (matched by substring, so column names don't need to be exact) are: age, d13C, d18O, Mg/Ca, DCP, d44Ca, Sr/Ca, Ba/Ca and U/Ca.

**Reference scale note:** your measured d18O column should be on the **VPDB** scale (the standard convention for carbonates). CaveCalc's modelled d18O output (`d18O_Calcite`/`d18O_Aragonite`) is natively on the **VSMOW** scale (inherited from the database's oxygen isotope standard), so the CDA module converts the model's d18O to VPDB internally before comparing it to your data - you do not need to convert anything yourself for CDA matching. This conversion is specific to the CDA comparison step; see [below](#the-d18o-reference-scale-vsmow-vs-vpdb) for what this means elsewhere in the model.

### Step 2: Define tolerance values (optional)

Tolerances define what counts as a "match" between model and measured data. Set them in the GUI (CDA Settings section) or in a script:
- `tolerance_d13C`, `tolerance_d18O`, `tolerance_d44Ca`, `tolerance_DCP`
- `tolerance_MgCa`, `tolerance_SrCa`, `tolerance_BaCa`, `tolerance_UCa`

Leave any blank to use its default tolerance (see `cavecalc/data/defaults.py`).

### Step 3: Define model inputs

Set your model inputs as usual (see [Usage](#usage) and [Model Inputs](#model-inputs)).

### Optional: output directory

Outputs save by default to `./cavecalc_output/`. Override with:
```python
'out_dir': './my_custom_output/'
```
or set it directly in the GUI.

CDA output is stored inside the chosen output directory, in a `CDA_Results/` subfolder containing four `.csv` files (see [Output](#output)).

### Running models with CDA

```shell
cd CaveCalcV2.0/API_models/
python run_CDA.py
```
Or, via the GUI, click **Run CaveCalc With CDA!**.

Progress is reported in the terminal/command prompt. On first use in a given output directory, you'll see something like:
```
CDA was initialised for the first time in the output directory. Created new 'Path/to/Output_Directory/CDA_Results/All_outputs.csv
```

Provided the output directory is left unchanged, running further batches appends to the existing CDA results rather than overwriting them.

## Aragonite Precipitation

Simulate **aragonite** as the speleothem precipitate via the GUI or a Python script.

### In the GUI

1. Navigate to the **Aragonite/Calcite Mode** section.
2. Use the `precipitate_mineralogy` drop-down.
3. Select `Aragonite`.

CaveCalc automatically switches to the matching thermodynamic database (`aragonite.dat`) - no manual database editing required.

### In a Python script

```python
'precipitate_mineralogy': 'Aragonite'
```

Note that several model output keys (and some proxy behaviours, below) differ between Calcite and Aragonite runs, since each mineral has its own set of database partition coefficients and fractionation factors.

## Partition Coefficient Overrides

By default, CaveCalc draws every partition coefficient and fractionation factor (Mg/Ca, Sr/Ca, Ba/Ca, U/Ca, d44Ca) straight from the active thermodynamic database (`calcite.dat` or `aragonite.dat`). CaveCalcV2.0 lets you override any of these directly from your settings, without touching the database files - useful if you have site-specific partitioning constraints (e.g. from your own cave monitoring or calibration study) that differ from the generic database values.

These settings are **mineralogy-agnostic**: set `D_MgCa`, say, and it is applied to whichever mineral `precipitate_mineralogy` is currently set to (resolved at run time against the matching named expression in that mineral's database). You do not need separate settings per mineralogy.

| Setting | What it overrides | Units / form | Default |
|---|---|---|---|
| `D_MgCa` | Mg/Ca partition coefficient | Linear D (dimensionless, > 0) | `None` (database default) |
| `D_SrCa` | Sr/Ca partition coefficient | Linear D (dimensionless, > 0) | `None` (database default) |
| `D_BaCa` | Ba/Ca partition coefficient | Linear D (dimensionless, > 0) | `None` (database default) |
| `D_UCa` | U/Ca partition coefficient | Linear D (dimensionless, > 0) | `None` (database default) |
| `D_44Ca` | Ca isotope fractionation factor | **1000 x ln(alpha)**, per mil (may be negative) | `None` (database default) |

A setting left as `None` uses the database default and behaves exactly as CaveCalc always has.

**Important - D_44Ca units.** Unlike the other four, `D_44Ca` must be supplied directly as **1000 ln(alpha)** (the same convention the database itself uses), not as a linear partition coefficient. 

**Example (API script):**
```python
settings = {
    ...
    'precipitate_mineralogy': 'Calcite',
    'D_MgCa': 0.02,        # override the database Mg/Ca partition coefficient
    'D_44Ca': -0.85,       # override the Ca isotope fractionation factor (1000*ln(alpha))
}
```

**A note on physically implausible values.** Supplying a wildly unrealistic partition coefficient (e.g. `D_MgCa = 1.5`, well above typical Mg exclusion from calcite/aragonite) can push PHREEQC into severe convergence difficulty, since the solid-solution chemistry becomes thermodynamically extreme. If a run with an override fails to converge, check the value against literature-plausible partitioning for that element/mineral before assuming it's a code issue.

**GUI location.** These settings live in their own highlighted **Partition Coefficient Overrides** section, alongside Aragonite/Calcite Mode.

## The d18O Reference Scale: VSMOW vs VPDB

This trips people up, so it's worth stating plainly:

- **`atm_d18O` (Rainfall d18O), `bedrock_d18O`, `cave_d18O`** - all model d18O *inputs* must be given on the **VSMOW** scale, matching the database's built-in oxygen isotope standard.
- **`d18O_Calcite` / `d18O_Aragonite` (model output)** - natively on the **VSMOW** scale, inherited directly from that same standard.
- **Measured speleothem d18O data** is conventionally reported on the **VPDB** scale.

If you're plotting or comparing model d18O output directly (outside of CDA - e.g. via `analyse.py`), remember it is VSMOW and will carry an offset of roughly 30 permil relative to VPDB-reported measured values. Convert with:
```
VPDB = 0.970001 * VSMOW - 29.99
```
The CDA module applies this conversion internally and automatically when matching model output to your measured data (see [Carbonate Data Analyser](#carbonate-data-analyser)), so no manual conversion is needed there. The GUI's rainfall d18O field includes a **"Preview as VPDB"** button that shows the VPDB-equivalent of your entered value for reference only - it does not alter the field, which must remain on the VSMOW scale for the model to run correctly.

d13C and d44Ca don't have an analogous dual-scale issue in CaveCalc: d13C is reported on VPDB throughout, and d44Ca follows whichever standard your bedrock/soil inputs use (commonly SRM 915a) - just keep your measured data and your bedrock/soil d44Ca inputs on the same standard.

## Output

Every CaveCalcV2.0 run (with or without CDA) generates three files in the output directory:

1. **`settings.pkl`** - a pickle of all input settings for the run.
2. **`results.pkl`** - a pickle of all model results.
3. **`settings_results.csv`** - a consolidated, human-readable CSV of both. Model output is recorded at each stage of speleothem chemistry per model (soil-water equilibration, bedrock dissolution, CO2 degassing, and carbonate precipitation), so each output key holds an array of values across those steps.

A full reference of output keys and their meaning is intended for `manual.pdf`, Table 4; note that the exact set of output keys differs slightly depending on whether `precipitate_mineralogy` is Calcite or Aragonite.

If CDA was run, a `CDA_Results/` subfolder is created in the output directory, containing:

1. **`Matches.csv`** - inputs, outputs and residuals for every run that matched the measured data within tolerance.
2. **`All_outputs.csv`** - inputs, outputs and residuals for every CDA run, matched or not.
3. **`Tolerances.csv`** - the tolerance intervals used for each proxy.
4. **`Input_Ranges.csv`** - the range of model inputs explored across the CDA batch.

## Plotting

CaveCalcV2.0's built-in plotting lives in `analyse.py`. Generate plots after running models, or re-plot from archived output.

**Line plots of model output:**
```python
import cavecalc.analyse as cca

out_dir = 'path/to/output/'  # path to archived output data

e = cca.Evaluate()
e = e.load_data(out_dir)
e1 = e.filter_by_index(0, n=True)  # filter out the first model step

# d13C_Calcite vs f_ca, one coloured line per soil_pCO2 value
e1.plot_models(x_key='f_ca', y_key='d13C_Calcite', label_with='soil_pCO2')
```
`x_key`/`y_key` can be any model output key; `label_with` can be any model input key. The set of available output keys is given in `manual.pdf`, Table 3/4, and differs slightly between Calcite and Aragonite runs.

**Point/scatter plots:**
```python
import cavecalc.analyse as cca

out_dir = 'path/to/output/'

e = cca.Evaluate()
e = e.load_data(out_dir)

# f_ca vs d13C_Calcite at the final (cave-air-equilibrated) step
e.plot_points(x_key='f_ca', y_key='d13C_Calcite', point_index=-1, label_with='soil_pCO2')
```

**CDA plots:** three plots (CO2 processes, flow-path controls, model-data comparison) are generated automatically after a CDA run, and can also be regenerated manually from archived CDA output:
```python
import cavecalc.analyse as cca

e = cca.CDAPlotter()

user_filepath = 'path/to/data.csv'          # measured data used in the CDA run
out_dir = 'path/to/out_dir/CDA_Results/'    # archived CDA_Results directory

plot = e.plot_CDA(user_filepath, out_dir)
```
The CDA plotting routine doesn't plot every input variable - only a representative selection. The full set of inputs/outputs for every matched run is always available in `Matches.csv`.

## Citing this work

If you use CaveCalcV2.0, please cite: *(citation details to be added on publication)*.

## Contributing, questions, and issues

Suggestions, improvements, questions or comments are welcome - please open an issue, start a discussion, or [get in touch](mailto:samuel.hollowood@earth.ox.ac.uk).

## License

This project is licensed under the MIT license.

## References and Acknowledgements

### Scientific references

- Owen, R., Day, C.C. and Hu, C.-Y. (2018). CaveCalc: A new model for speleothem chemistry and isotopes. *Computers & Geosciences*, 119, 115-122. (original CaveCalc model)

### Software dependencies

This repository uses the following open-source libraries:

- **scipy** (v1.13.1) - Scientific computing tools
- **numpy** (v1.26.4) - Fundamental package for numerical computing
- **matplotlib** (v3.8.4) - Plotting and visualisation library
- **inflection** (v0.5.1) - String transformation utilities
- **phreeqpy** (v0.6.0) - Python interface for PHREEQC geochemical modelling
- **seaborn** (v0.13.2) - Statistical data visualisation based on matplotlib
- **pandas** (v2.2.3) - Data structures and data analysis tools
- **pywin32** (v305.1) - Windows extensions for Python

**matplotlib dependencies:** contourpy (v1.2.0), cycler (v0.11.0), fonttools (v4.51.0), kiwisolver (v1.4.4), packaging (v23.2), pillow (v10.4.0), pyparsing (v3.0.9), python-dateutil (v2.9.0.post0)

**pandas dependencies:** pytz (v2024.1), tzdata (v2023.3)

**Other dependencies:** six (v1.16.0) - Python 2/3 compatibility utilities

We thank the developers of these libraries for making this work possible.

Samuel J. Hollowood is funded by a UKRI NERC DTP Award (NE/S007474/1) and gratefully acknowledges their support.

