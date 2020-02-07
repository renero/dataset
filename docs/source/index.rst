.. pyDataset documentation master file, created by
   sphinx-quickstart on Wed Feb  5 19:49:08 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pyDataset
====================

J. Renero

.. image:: https://travis-ci.org/renero/dataset.svg?branch=master
    :target: https://travis-ci.org/renero/dataset

.. image:: https://readthedocs.org/projects/pydataset/badge/?version=latest
    :target: https://pydataset.readthedocs.io/en/latest/?badge=latest

.. image:: https://img.shields.io/github/v/tag/renero/dataset
    :target: https://img.shields.io/github/v/tag/renero/dataset

Dataset is for educational purposes, mainly. It tries to help those
approaching Data Science in Python for the first time, who must deal with
common (and time consuming) data preparation tasks.

This package tries, through a very simple approach, to collect all the common
tasks that are normally done over pandas DataFrames, like:

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
- compute information gain,
- plot some useful charts

Install
-------

To install this package, simply `pip` from this git repo:

.. code-block:: bash

  $ pip install git+https://github.com/renero/dataset

Data Tutorial / Guide
---------------------

.. toctree::
   :maxdepth: 1
   :caption: A Comprehensive tutorial with examples:

   example

The API Documentation
---------------------

If you are looking for information on a specific function, or method,
this part of the documentation is for you.

.. toctree::
   :maxdepth: 3
   :caption: pyDataset API documentation

   dataset

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
