# -*- coding: utf-8 -*-
import os
import sys


sys.path.insert(0, os.path.abspath('../'))
sys.path.append('/Users/renero/Documents/SideProjects/dataset/dataset')

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode', 'sphinx.ext.napoleon', 'm2r']

napoleon_google_docstring = True
napoleon_use_param = True
napoleon_use_ivar = True

source_suffix = '.rst'
master_doc = 'index'
project = u'Dataset'
copyright = u'J. Renero'
exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'sphinx_rtd_theme'
autoclass_content = "both"

autodoc_default_options = {
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': 'update, target, numerical, numbers_to_float, \
    meta_tags, meta, features, describe_numerical, describe_categorical,\
    data, categorical_dtypes, all, categorical'
}
