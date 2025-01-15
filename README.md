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

We present a proof-of-concept workflow for probabilistic earthquake ground motion prediction that accounts for inconsistencies between existing seismic velocity models. The approach is based on the probabilistic merging of overlapping seismic velocity models using scalable Gaussian Process (GP) regression. We fit a GP to two synthetic 1-D velocity profiles simultaneously, demonstrating that the predictive uncertainty accounts for the differences between them. We then draw samples of velocity models from the predictive distribution and simulate the acoustic wave equation using each sample as input. This results in a distribution of possible peak ground displacement (PGD) scenarios, reflecting the degree of knowledge of seismic velocities in the region.
