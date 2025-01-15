# CaveCalcV2.0: A software tool for forward modelling speleothem chemistry and the evolution of isotopic and elemental systems
version 1 (https://github.com/Rob-Owen/cavecalc)

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Samhollowood/CaveCalcV2.0/HEAD?urlpath=tree)
![GitHub License](https://img.shields.io/github/license/Samhollowood/CaveCalcV2.0)
![GitHub Release](https://img.shields.io/github/v/release/Samhollowood/CaveCalcV2.0)

## Table of Contents
- [Introduction](#introduction)
- [Installation](#installation)
- [Usage](#usage)
- [Citing this work](#citing-this-work)
- [Contributing, questions, and issues](#contributing-questions-and-issues)
- [License](#license)
- [References and Acknowledgements](#references-and-acknowledgements)


## Introduction
This repository is the official implementation of [_CaveCalcV2.0: A software tool for forward modelling speleothem chemistry and the evolution of isotopic and elemental systems_](), in preperation for submission into [Computers & Geosciences](https://www.sciencedirect.com/journal/computers-and-geosciences).

We present a newly updated CaveCalcV2.0 forward modelling tool for simulating speleothem chemistry with new examples, and installation processes.

Updates include:
(1) The new Carbonate Data Analyser (CDA) mode
(2) Speleothem aragonite precipitation
(3) U/Ca as a proxy 

This repository provides the source code (/cavecalc), examples (/examples), API model run examples (/API_model), and scripts for opening the Graphical User Interface (/scripts)

## Installation
There is a full installation guide in the manual () if users need guidance on installing python, and manually configuring the COM server in PHREEQC (Windows Only).

It is important to note that in the setup.py I have automated this configuration and thus Windows usres no longer need to do this step manually. Nonetheless it is still provided if users have difficutly with the set-up.

Here, I provide steps on how to install cavecalc from github:

**This code has been tested using Python 3.10.12. CaveCalc cannot run on Python2.7. Please use a version of Python3 (recomended >3.5).**

Clone the repository:
```shell
git clone git@github.com:Samhollowood/CaveCalcV2.0.git
```

Go to directory:
```shell
cd CaveCalcV2.0
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
cd ..
```
```shell
cd scripts
```
```shell
python cc_input_gui.py
```


