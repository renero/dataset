# Dataset
(C) J. Renero

[![Build Status](https://travis-ci.org/renero/dataset.svg?branch=master)](https://travis-ci.org/renero/dataset) [![Documentation Status](https://readthedocs.org/projects/pydataset/badge/?version=latest)](https://pydataset.readthedocs.io/en/latest/?badge=latest)

This class attempts, through a very simple approach, collect all the common 
tasks that are normally done over pandas dataframes, like:

- load data
- set the target variable
- describe the health status of the dataset
- drop/keep columns or sample from simple lists
- split the dataset
- count categorical and numerical features
- fix NA's
- find correlations
- detect skewness
- scale numeric values
- detect outliers
- one hot encoding
- find under represented categorical features
- perform stepwise feature selection

## Install

To install this package, simply git clone this repo, and:

    $ cd dataset
    $ pip install -e .
    
## Examples

Check the `example.py` to see how to start using it.

## Documentation

Please, check the latest documentation at ![ReadTheDocs PyDataset Project page](https://readthedocs.org/projects/pydataset/).
