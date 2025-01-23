# CaveCalcV2.0: A software tool for forward modelling speleothem chemistry.
version 1 (https://github.com/Rob-Owen/cavecalc)

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Samhollowood/CaveCalcV2.0/main)
![GitHub License](https://img.shields.io/github/license/Samhollowood/CaveCalcV2.0)
![GitHub Release](https://img.shields.io/github/v/release/Samhollowood/CaveCalcV2.0)

## Table of Contents
- [Introduction](#introduction)
- [Installation](#installation)
- [Usage](#usage)
- [Post-processing](#post-processing)
- [Citing this work](#citing-this-work)
- [Contributing, questions, and issues](#contributing-questions-and-issues)
- [License](#license)
- [References and Acknowledgements](#references-and-acknowledgements)


## Introduction
This repository is the official implementation of [_CaveCalcV2.0: A software tool for forward modelling speleothem chemistry._](), in preperation for submission into [Computers & Geosciences](https://www.sciencedirect.com/journal/computers-and-geosciences).

We present a newly updated CaveCalcV2.0 forward modelling tool for simulating speleothem chemistry with new examples, and installation processes.

Updates include:
(1) The new Carbonate Data Analyser (CDA) mode
(2) Speleothem aragonite precipitation
(3) U/Ca as a proxy 

This repository provides the source code (`cavecalc/`), examples (`examples/`), API model run examples (`API_models/`), and scripts for opening the Graphical User Interface (/scripts)

## Installation
There is a full installation guide in the manual () if users need guidance on installing python, and manually configuring the COM server in PHREEQC (Windows Only).

NOTE: A key difference to installation on CaveCalcV2.0 to CaveCalc is that the installation script automatically configures and compiles the system-specific .dll/.so file for interaction with the IPhreeqc COM server for Windows and Linux users

Here, I provide steps on how to install cavecalc from github:

**This code has been tested using Python 3.10.12. CaveCalc cannot run on Python2.7. Please use a version of Python3 (recomended >3.5).**

Clone the repository:
```shell
git clone https://github.com/Samhollowood/CaveCalcV2.0.git
```

Go to directory:
```shell
cd CaveCalcV2.0
```

If you would like to install into anaconda (optional):
```shell
conda activate base
```

Run:
```shell
python setup.py install
```

Verify installation by running example:
```shell
cd examples/
```
```shell
python example1.py
```


Open the GUI by:
```shell
cd CaveCalcV2.0/scripts
```
```shell
python cc_input_gui.py
```



## Usage
Examples of running single models, multiple models, and models with the CDA initialised are provided in the manual (). Users can run models via the run_models.py in `API_models/` or the CDA in run_CDA.py also in 
`API_models/`. The python scripts have inputs set as the default, change them as you please.


## Citing this work
If you use CaveCalcV2.0 please site .....

## Contributing, questions, and issues
If you have any suggestions, improvements, questions, or comments - please create an issue, submit a pull request, or [get in touch](mailto:samuel.hollowood@earth.ox.ac.uk).

## License
This project is licensed under the MIT license

## References and Acknowledgements

This repository uses the following open-source software libraries:






Samuel J. Hollowood is funded by a UKRI NERC DTP Award (NE/S007474/1) and gratefully acknowledges their support.

