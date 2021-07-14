# -*- coding: utf-8 -*-
# Copyright (C) 2021 Jesus Renero
# Licence: MIT
import codecs
import os.path

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

with open('README.md', encoding="utf-8") as f:
    long_description = f.read()


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def get_version():
    for line in read("dataset/__init__.py").splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


def setup_package():
    setup(
        name='dataset',
        version=get_version(),
        description='A library to start managing data in ML projects, \
        for educational purposes.',
        packages=find_packages(),
        url='https://github.com/renero/dataset',
        license='MIT',
        author='J.Renero',
        install_requires=['matplotlib', 'numpy', 'pandas', 'scikit_learn',
                          'scipy', 'seaborn', 'sklearn_pandas', 'skrebate',
                          'statsmodels', 'nbsphinx'],
        author_email='jrenero@faculty.ie.edu'
    )


if __name__ == '__main__':
    setup_package()
