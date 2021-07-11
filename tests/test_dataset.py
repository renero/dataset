from unittest import TestCase

import numpy as np
import pandas as pd

from dataset.dataset import Dataset


class TestDataset(TestCase):
    df1 = pd.DataFrame(
        data={'col1': [1, 2, 3, 2, 2, 2, 1, 3, 2, 1],
              'col2': ['a', 'a', 'b', 'a', 'b', 'a', 'a', 'a', 'b', 'c'],
              'col3': ['1', '1', '1', '0', '0', '1', '1', '0', '1', '0']
              })

    def setUp(self):
        self.ds = Dataset.from_dataframe(self.df1)

    def test_numbers_type_conversion(self):
        self.assertIs(self.ds.features.col1.dtype, np.dtype('float64'))
        self.ds.to_int('col1')
        self.assertEqual(self.ds.features['col1'].dtype, 'int')
        self.ds.to_float('col1')
        self.assertEqual(self.ds.features['col1'].dtype, 'float')

    def test_empty_to_float(self):
        # Check that conversion works with all numerical columns when no
        # column is specified
        self.ds.to_int('col1')
        self.ds.to_float()
        self.assertEqual(self.ds.features['col1'].dtype, 'float')

    def tests_to_float(self):
        self.assertEqual(self.ds.numerical_features, ['col1'])

    def test_set_target(self):
        self.ds.set_target('col3')
        self.assertEqual(self.ds.names(), ['col1', 'col2'])
        self.assertEqual(self.ds.target.name, 'col3')

    def test_unset_target(self):
        self.ds.set_target('col3')
        self.ds.unset_target()
        self.assertEqual(self.ds.names(), ['col1', 'col2', 'col3'])
        self.assertIsNone(self.ds.target)

    def test_select(self):
        self.assertEqual(list(self.ds.select('numerical')), ['col1'])

    def test_set_target(self):
        self.ds.set_target('col3')
        self.assertNotIn('col3', self.ds.features)
        self.assertEqual(self.ds.target.name, 'col3')

    def test_update(self):
        self.assertEqual(self.ds.meta['features'], list(self.df1))
        self.ds.set_target('col3')
        self.assertEqual(self.ds.meta['target'], 'col3')
        self.assertEqual(list(self.ds.numerical), ['col1'])
        self.assertIs(self.ds.features, self.ds.features)
        self.assertEqual(list(self.ds.categorical), ['col2'])

    def test_bin(self):
        self.ds.discretize('col1', [(0, 2), (2, 4)])
        self.ds.to_numerical('col1')
        self.assertListEqual(list(self.ds.features['col1'].values),
                             [1, 1, 2, 1, 1, 1, 1, 2, 1, 1])

    def test_samples_matching(self):
        try:
            self.ds.samples_matching(3)
        except AttributeError as e:
            self.assertIsInstance(e, AttributeError)

        self.assertListEqual(self.ds.samples_matching('c', 'col2'), [9])
        self.assertListEqual(self.ds.samples_matching(3, 'col1'), [2, 7])
        self.ds.set_target('col3')
        self.assertListEqual(self.ds.samples_matching('0'), [3, 4, 7, 9])
        self.ds.unset_target()
        self.assertListEqual(self.ds.samples_matching('0', 'col3'),
                             [3, 4, 7, 9])

    def test_IG(self):
        df = pd.DataFrame({
            'sex': ['f', 'm', 'm', 'm', 'm', 'f', 'm', 'f', 'm', 'm'],
            'pulse': ['100', '25', '100', '25', '50', '75', '100', '75', '75',
                      '100']})
        self.ds = Dataset.from_dataframe(df)
        self.ds.set_target('sex')
        self.assertAlmostEqual(self.ds._IG('pulse'), 0.2812908992306927)

    def test_drop_na(self):
        df = pd.DataFrame({'age': [5, 6, np.nan],
                           'born': [None,
                                    pd.Timestamp('1939-05-27'),
                                    pd.Timestamp('1940-04-25')],
                           'name': ['Alfred', 'Batman', ''],
                           'toy': [None, 'Batmobile', 'Joker']})
        self.ds = Dataset.from_dataframe(df)
        self.ds.drop_na()
        self.assertEqual(self.ds.features.shape[0], 1)
        self.assertEqual(self.ds.features.shape[1], 4)
        self.assertEqual(self.ds.features.iloc[0]['age'], 6.0)
        self.assertEqual(self.ds.features.iloc[0]['born'],
                         pd.Timestamp('1939-05-27'))
        self.assertEqual(self.ds.features.iloc[0]['name'], 'Batman')

        self.ds = Dataset.from_dataframe(df)
        self.ds.set_target('toy')
        self.ds.drop_na()
        self.assertEqual(self.ds.features.shape[0], 1)
        self.assertEqual(self.ds.features.shape[1], 3)
        self.assertEqual(self.ds.features.iloc[0]['age'], 6.0)
        self.assertEqual(self.ds.features.iloc[0]['born'],
                         pd.Timestamp('1939-05-27'))
        self.assertEqual(self.ds.features.iloc[0]['name'], 'Batman')
        self.assertEqual(self.ds.target.shape[0], 1)
        self.assertEqual(self.ds.target[0], 'Batmobile')

    def test_incomplete_features(self):
        df1 = pd.DataFrame(
            data={'col1': [1, 2, np.nan, 2],
                  'col2': ['a', 'a', 'b', 'a'],
                  'col3': ['1', '1', '1', np.nan]
                  })
        ds = Dataset.from_dataframe(df1)
        self.assertEqual(set(ds.incomplete_features), set(['col1', 'col3']))
