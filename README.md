# Dataset
(C) J. Renero

[![Build Status](https://travis-ci.org/renero/dataset.svg?branch=master)](https://travis-ci.org/renero/dataset) [![Documentation Status](https://readthedocs.org/projects/pydataset/badge/?version=latest)](https://pydataset.readthedocs.io/en/latest/?badge=latest) ![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/renero/dataset)

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

To install this package, first of all, be sure you have Python 3.7, and then do the following:

    $ pip install git+http://github.com/renero/dataset
    
Or, if you prefer, clone the repository using `git clone https:/github.com/renero/dataset.git`, and then move into the just created folder to install it:

    $ git clone https:/github.com/renero/dataset.git
    $ cd dataset
    $ pip install -e .

## Examples

Check the `example.ipynb` to see how to start using it.

## Documentation

Please, check the latest documentation at [ReadTheDocs PyDataset Project page](https://pydataset.readthedocs.io/en/latest/).
