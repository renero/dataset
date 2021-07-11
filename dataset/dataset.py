"""
This is the package dataset.
"""
import math
import warnings
from copy import copy
from math import log2

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from scipy.cluster import hierarchy
from scipy.special import boxcox1p
from scipy.stats import skew, boxcox_normmax
from sklearn.model_selection import train_test_split
from sklearn.neighbors import LocalOutlierFactor
# noinspection PyUnresolvedReferences
from sklearn.preprocessing import MinMaxScaler, StandardScaler, PowerTransformer
from sklearn.preprocessing import scale
from sklearn_pandas import DataFrameMapper
from skrebate import ReliefF

from dataset.correlations import cramers_v
from dataset.split import Split

warnings.simplefilter(action='ignore')


#
# Correlation ideas taken from:
# https://towardsdatascience.com/the-search-for-categorical-correlation-a1cf7f1888c9
#


class Dataset:
    """
    This class allows a simpler representation of the dataset used
    to build a model in class. It allows to load a remote CSV by
    providing an URL to the initialization method of the object, and
    work on the most common tasks related to data preparation and
    feature engineering.::

        my_data = Dataset(URL)

        my_data = Dataset.from_dataframe(my_dataframe)

    """

    all = None
    meta = None
    # data = None
    target = None
    features = None
    numerical = None
    categorical = None

    meta_tags = ['all', 'numerical', 'categorical', 'complete',
                 'numerical_na', 'categorical_na', 'features', 'target']
    categorical_dtypes = ['bool', 'object', 'string', 'category']

    __num_plots_per_row = 4

    def __init__(self, data_location=None, data_frame=None, *args, **kwargs):
        """
        Wrapper over the method read_csv from pandas, so you can user variadic
        arguments, as if you were using the actual read_csv

        :param data_location: path or url to the file
        :param data_frame: in case this method is called from the class method
            this parameter is passing the actual dataframe to read data from
        :param args: variadic unnamed arguments to pass to read_csv
        :param kwargs: variadic named arguments to pass to read_csv
        """
        if data_location is not None:
            self.features = pd.read_csv(data_location, *args, **kwargs)
        else:
            if data_frame is not None:
                self.features = copy(data_frame)
            else:
                raise RuntimeError(
                    "No data location, nor DataFrame passed to constructor")
        # When data is read with no headers, column names can be 'int', so
        # I need to convert them to strings.
        if isinstance(list(self.features)[0], str) is False:
            colnames = ['x{}'.format(col) for col in list(self.features)]
            self.features.columns = colnames
        self.to_float()
        self.__update()

    @classmethod
    def from_dataframe(cls, df):
        return cls(data_location=None, data_frame=df)

    def set_target(self, target_name):
        """
        Set the target variable for this dataset. This will create a new
        property of the object called 'target' that will contain the
        target column of the dataset, and that column will be removed
        from the list of features.

        :param target_name: The name of the column we want to be set as the
            target variable for this dataset.

        Example::

            my_data.set_target('SalePrice')

        """
        assert target_name in list(self.features), "Target name NOT recognized"

        self.target = self.features.loc[:, target_name].copy()
        self.features.drop(target_name, axis=1, inplace=True)
        self.__update()
        return self

    def unset_target(self):
        """
        Undo the `set_target()` operation. The feature `target_name` returns
        to the DataFrame with the rest of the features.

        Example::

            my_data.unset_target()

        """
        assert self.target is not None, "Target feature NOT set, yet..."

        self.features[self.target.name] = self.target.values
        self.target = None
        self.__update()
        return self

    def __update(self):
        """
        Builds meta-information about the dataset, considering the
        features that are categorical, numerical or does/doesn't contain NA's.
        """
        meta = dict()

        # Update META-information
        if self.target is not None:
            meta['all'] = list(self.features) + [self.target.name]
            self.all = pd.concat([self.features, self.target], axis=1)
        else:
            meta['all'] = list(self.features)
            self.all = self.features

        # Build the subsets per data ype (list of names)
        descr = pd.DataFrame({'dtype': self.features.dtypes,
                              'NAs': self.features.isna().sum()})
        meta['description'] = descr

        numerical = self.features.select_dtypes(include=['number'])
        numerical_features = list(numerical)
        categorical = self.features.select_dtypes(exclude=['number'])
        categorical_features = list(categorical)
        numerical_features_na = numerical.columns[
            numerical.isna().any()].tolist()
        categorical_features_na = categorical.columns[
            categorical.isna().any()].tolist()
        complete_features = self.all.columns[
            ~self.all.isna().any()].tolist()

        meta['features'] = list(self.features)
        meta['target'] = self.target.name if self.target is not None else None
        meta['categorical'] = categorical_features
        meta['categorical_na'] = categorical_features_na
        meta['numerical'] = numerical_features
        meta['numerical_na'] = numerical_features_na
        meta['complete'] = complete_features
        self.meta = meta

        # Update macro access properties
        self.numerical = self.select('numerical')
        self.categorical = self.select('categorical')
        # self.data = self.features
        return self

    def outliers(self, n_neighbors=20):
        """
        Find outliers, using LOF criteria, from the numerical features.
        Returns a list of indices where outliers are present

        :param n_neighbors: Number of neighbors to use by default for
            kneighbors queries. If n_neighbors is larger than the number
            of samples provided, all samples will be used.

        # TODO Implement a simple set of methods to select from in order to
               detect outliers.
        """
        X = self.select('numerical')
        lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination='auto')
        y_pred = lof.fit_predict(X)
        outliers = np.where(y_pred == -1)
        return outliers[0]

    def scale(self,
              features_of_type='numerical',
              method='StandardScaler',
              return_series=False):
        """
        Scales numerical features in the dataset, unless the parameter 'what'
        specifies any other subset selection primitive. The method to be used
        is the sckikit learn StandardScaler.

        Examples::

            # scale all my numerical features
            my_data.scale()

        :param features_of_type: Subset selection primitive
        :param method: 'StandardScaler', 'MinMaxScaler'
        :return: the subset scaled.
        """
        assert features_of_type in self.meta_tags, \
            "No features of the type specified"
        assert method == 'StandardScaler' or method == 'MinMaxScaler', \
            "Method can only be \'standard\' or \'minmax\'"

        subset = self.select(features_of_type)
        scaler = globals()[method]
        mapper = DataFrameMapper([(subset.columns, scaler())])
        scaled_features = mapper.fit_transform(subset.copy())
        self.features[self.names(features_of_type)] = pd.DataFrame(
            scaled_features,
            index=subset.index,
            columns=subset.columns)
        self.__update()
        if return_series is True:
            return self.features[self.names(features_of_type)]
        else:
            return self

    def fix_skewness(self, feature_names=None, return_series=False):
        """
        Ensures that the numerical features in the dataset,
        fit into a normal distribution by applying the Yeo-Johnson transform.
        If not already scaled, they're scaled as part of the process.

        :param feature_names:    Features to be fixed. If not specified, all
                                 numerical features are examined.
        :param return_series:    Return the normalized series

        :return:                 The subset fitted to normal distribution,
                                 or None
        """
        if feature_names is None:
            if len(self.numerical_features) == 0:
                raise ValueError('No numerical features to fix.')
            feature_names = self.numerical_features
        elif not isinstance(feature_names, list):
            feature_names = [feature_names]

        yj = PowerTransformer(method='yeo-johnson')
        normed_features = yj.fit_transform(self.features[feature_names])
        self.features[feature_names] = normed_features
        self.__update()

        if return_series is True:
            return normed_features

    def skewed_features(self, threshold=0.75, fix=False, return_series=True):
        """
        Returns the list of numerical features that present skewness. This
        method optionally can fix detected skewness whose ABS is greater
        than the threshold passed, using BoxCox method.

        :param threshold: The limit over which considering that the
            ``skew()`` return value is considered a skewed feature.
        :param fix: (Default: False) Boolean indicating whether or not
            fixing the skewed features. If True, those with values above the
            threshold will be fixed using BoxCox.
        :param return_series: (Default: True) Boolean indicating whether
            returning the features (pandas DataFrame) that present skewness.
        :return: A pandas Series with the features and their skewness
        """
        df = self.numerical
        feature_skew = df.apply(
            lambda x: skew(x)).sort_values(ascending=False)

        if fix is True:
            high_skew = feature_skew[np.abs(feature_skew) > threshold]
            skew_index = high_skew.index
            for feature in skew_index:
                self.features[feature] = boxcox1p(
                    df[feature], boxcox_normmax(df[feature] + 1))
        if return_series is True:
            return feature_skew

    def correlated(self, threshold=0.9):
        """
        Return the features that are highly correlated to with other
        variables, either numerical or categorical, based on the threshold. For
        numerical variables Spearman correlation is used, for categorical
        cramers_v.

        :param threshold: correlation limit above which features are
            considered highly correlated.
        :return: the list of features that are highly correlated, and
            should be safe to remove.
        """
        corr_categoricals = self.categorical_correlated(threshold)
        corr_numericals = self.numerical_correlated(threshold)

        return corr_categoricals + corr_numericals

    @staticmethod
    def __top_correlations(df, correlations, threshold):
        def redundant_pairs(dataf):
            """
            Get diagonal and lower triangular pairs of correlation matrix
            """
            pairs_to_drop = set()
            cols = dataf.columns
            for i in range(0, dataf.shape[1]):
                for j in range(0, i + 1):
                    pairs_to_drop.add((cols[i], cols[j]))
            return pairs_to_drop

        labels_to_drop = redundant_pairs(df)
        correlations = correlations.drop(labels=labels_to_drop).sort_values(
            ascending=False)
        tuples = [(correlations.index[i][0], correlations.index[i][1],
                   correlations[i]) for i in range(correlations.shape[0]) \
                  if correlations[i] > threshold]
        return tuples

    def numerical_correlated(self, threshold=0.9):
        """
        Build a correlation matrix between all the features in data set

        :param threshold: Threshold beyond which considering high correlation.
            Default is 0.9
        :return: The list of columns that are highly correlated and could be
            drop out from dataset.
        """
        correlations = self.numerical.corr(method='spearman').abs().unstack()
        return Dataset.__top_correlations(self.numerical, correlations,
                                          threshold)

    def categorical_correlated(self, threshold=0.9):
        """
        Generates a correlation matrix for the categorical variables in dataset
        Calculates Cramer's V statistic for categorical-categorical association.
        Uses correction from Bergsma and Wicher, Journal of the Korean
        Statistical Society 42 (2013): 323-328. This is a symmetric
        coefficient: V(x,y) = V(y,x)
        Original function taken from:
            https://stackoverflow.com/a/46498792/5863503
        Wikipedia:
            http://en.wikipedia.org/wiki/Cram%C3%A9r%27s_V

        :param threshold: Limit from which correlations is considered high.
        :return: The list of categorical variables with HIGH correlation and
            the correlation matrix
        """
        columns = self.meta['categorical']
        corr = pd.DataFrame(index=columns, columns=columns)
        for i in range(0, len(columns)):
            for j in range(i, len(columns)):
                if i == j:
                    corr[columns[i]][columns[j]] = 1.0
                else:
                    cell = cramers_v(self.features[columns[i]],
                                     self.features[columns[j]])
                    corr[columns[i]][columns[j]] = cell
                    corr[columns[j]][columns[i]] = cell
        corr.fillna(value=np.nan, inplace=True)
        correlations = corr.abs().unstack()
        return Dataset.__top_correlations(self.categorical, correlations,
                                          threshold)

    def under_represented_features(self, threshold=0.98):
        """
        Returns the list of categorical features with unrepresented categories
        or a clear unbalance between the values that can take.

        :param threshold: The upper limit of the most represented category
            of the feature.
        :return: the list of features that with unrepresented categories.
        """
        under_rep = []
        for column in self.meta['categorical']:
            counts = self.features[column].value_counts()
            majority_freq = counts.iloc[0]
            if (majority_freq / len(self.features)) > threshold:
                under_rep.append(column)
        return under_rep

    def information_gain(self):
        """
        Computes the information gain between each categorical and target
        variable.

        Examples::

            my_data.information_gain()
            Name   : 0.18
            Speed  : 0.00
            Type 1 : 0.04
            Type 2 : 0.03

        Returns:
            A dictionary with the IG value for each categorical feature name
        """
        self.drop_na()
        ig = {}
        for f in self.categorical_features:
            ig[f] = self._IG(f)
        return ig

    def _IG(self, vble_name):
        """
        Computes the Information Gain between a variable –whose name is passed,
        and the target variable.

        Args:
            vble_name: A string with the name of the categorical vble.

        Returns:
            The IG

        """
        assert self.target is not None, "Target must be set before calling IG"
        assert vble_name in self.categorical_features, \
            "Variable must be categorical to compute IG"

        def entropy(distribution):
            def H(p):
                return 0. if p == 0. else p * log2(p)

            return -sum([H(distribution[i]) for i in range(len(distribution))])

        target_num_unique_values = self.target.nunique()
        target_unique_values = self.target.unique()
        target_value_counts = self.target.value_counts()
        target_num_samples = sum([target_value_counts[target_unique_values[i]]
                                  for i in range(target_num_unique_values)])
        target_distribution = [
            target_value_counts[target_unique_values[i]] / target_num_samples \
            for i in range(target_num_unique_values)]

        target_entropy = entropy(target_distribution)

        vble = self.features[vble_name]
        vble_num_unique_values = vble.nunique()
        vble_unique_values = vble.unique()
        vble_value_counts = vble.value_counts()
        vble_num_samples = sum(
            [vble_value_counts[vble_unique_values[i]] for i in
             range(vble_num_unique_values)])

        vble_distribution = [
            vble_value_counts[vble_unique_values[i]] / vble_num_samples \
            for i in range(vble_num_unique_values)]

        vble_distribution = dict(zip(vble_unique_values, vble_distribution))

        xt = pd.crosstab(vble, self.target)

        cond_entropy = []
        for i in range(xt.shape[0]):
            row_distribution = [xt.iloc[i, j] / xt.iloc[i].sum() for j in
                                range(xt.shape[1])]
            cond_entropy.append(entropy(row_distribution))
        vble_entropy = dict(zip(xt.index, cond_entropy))
        vble_cond_entropy = sum([vble_distribution[v] * vble_entropy[v] for v in
                                 vble_unique_values])
        IG = target_entropy - vble_cond_entropy

        return IG

    def stepwise_selection(self,
                           initial_list=None,
                           threshold_in=0.01,
                           threshold_out=0.05,
                           verbose=False):
        """
        Perform a forward/backward feature selection based on p-value from
        statsmodels.api.OLS
        Your features must be all numerical, so be sure to onehot_encode them
        before calling this method.
        Always set threshold_in < threshold_out to avoid infinite looping.
        All features involved must be numerical and types must be float.
        Target variable must also be float. You can convert it back to a
        categorical type after calling this method.

        :parameter initial_list: list of features to start with (column names
            of X)
        :parameter threshold_in: include a feature if its
            p-value < threshold_in
        :parameter threshold_out: exclude a feature if its
            p-value > threshold_out
        :parameter verbose: whether to print the sequence of inclusions and
            exclusions
        :return: List of selected features

        Example::

            my_data.stepwise_selection()

        See <https://en.wikipedia.org/wiki/Stepwise_regression>
        for the details

        Taken from: <https://datascience.stackexchange.com/a/24823>
        """
        if initial_list is None:
            initial_list = []
        if len(self.names('categorical')) != 0:
            print('Considering only numerical features')
        # assert self.target.dtype.name == 'float64'

        included = list(initial_list)
        while True:
            changed = False
            # forward step
            excluded = list(set(self.numerical.columns) - set(included))
            new_pval = pd.Series(index=excluded)
            for new_column in excluded:
                model = sm.OLS(self.target, sm.add_constant(
                    pd.DataFrame(
                        self.numerical[included + [new_column]]))).fit()
                new_pval[new_column] = model.pvalues[new_column]
            best_pval = new_pval.min()
            if best_pval < threshold_in:
                best_feature = new_pval.idxmin()
                included.append(best_feature)
                changed = True
                if verbose:
                    print('Add  {:30} with p-value {:.6}'.format(best_feature,
                                                                 best_pval))
            # backward step
            model = sm.OLS(self.target, sm.add_constant(
                pd.DataFrame(self.numerical[included]))).fit()
            # use all coefs except intercept
            pvalues = model.pvalues.iloc[1:]
            worst_pval = pvalues.max()  # null if p-values is empty
            if worst_pval > threshold_out:
                changed = True
                worst_feature = pvalues.argmax()
                included.remove(worst_feature)
                if verbose:
                    print('Drop {:30} with p-value {:.6}'.format(worst_feature,
                                                                 worst_pval))
            if not changed:
                break
        return included

    def features_importance(self,
                            num_features=None,
                            num_neighbors=None,
                            abs_imp=False):
        """
        Computes NUMERICAL features importance, using the ReliefF algorithm as
        implemented in the `rebate` library.

        Args:
            num_features:   The nr of features we want to display
            num_neighbors:  The nr of neighbors to consider when computing the
                            features importance
            abs_imp:        if True, importance is displayed taking the ABS()

        Returns:
            A sorted dictionary with the feature names and their importance.

        """
        if num_features is None:
            num_features = len(self.numerical_features)
        if num_neighbors is None:
            num_neighbors = 20
        assert num_features <= len(self.numerical_features), \
            "Larger nr of features ({}) than available ({})".format(
                num_features, len(self.numerical_features))
        assert self.target is not None, \
            "Target feature must be specified before computing importance"
        assert num_neighbors <= self.features.shape[0], \
            "Larger nr of neighbours than samples ({})".format(
                self.features.shape[0])

        my_features = self.numerical.values  # the array inside the dataframe
        my_labels = self.target.values.ravel()  # the target as a 1D array.

        fs = ReliefF(n_features_to_select=num_features,
                     n_neighbors=num_neighbors)
        fs.fit_transform(my_features, my_labels)

        if abs_imp is True:
            importances = abs(fs.feature_importances_[:num_features])
        else:
            importances = fs.feature_importances_[:num_features]
        indices = np.argsort(importances)[:num_features]

        return dict([(self.numerical_features[i], importances[i]) for
                     i in indices])

    #
    # Methods are related to data manipulation of the pandas dataframe.
    #

    def select(self, what):
        """
        Returns a subset of the columns of the dataset.
        `what` specifies what subset of features to return
        If it is a list, it returns those feature names in the list,
        And if it is a keywork from: 'all', 'categorical', 'categorical_na',
        'numerical', 'numerical_na', 'complete', 'features', 'target',
        then the list of features is extracted from the metainformation
        of the dataset.

        :param what: Possible values are

            * all: (Default) Include very feature, including the target
            * numerical: Only numerical features
            * categorical: Only categorical features
            * complete: Only features without NA
            * numerical_na: Numerical features with NA
            * categorical_na: Categorical features with NA
            * features: Only features, NOT the target variable.
            * target: Only the target variable.

        :return: Reference to the columns specified.
        """
        if isinstance(what, list):
            # return self.features.loc[:, what]
            return self.features[what]
        else:
            assert what in self.meta_tags
            if what == 'all':
                return self.all[self.meta[what]]
            else:
                return self.features[self.meta[what]]

    def samples_matching(self, value=None, feature=None):
        """
        Return the a list with the indexes of those samples matching a given
        criteria. The match can be set on target variable, or any other
        column name.

        Args:
            value:
            feature:

        Returns:
            A list with the index values of those samples matching.

        Examples::

            my_data.samples_matching('red')

        returns the indices of those samples whose `target` matches the
        value `red`.

            my_data.samples_matching(75, 'column_3')

        returns the indices of those samples whose feature `column_3`
        values 75.

        """
        if feature is None:
            sample_indices = self.all.index[
                self.all[self.target.name] == value].to_list()
        else:
            assert feature in self.names(), \
                "Feature ({}) is not present in dataset".format(feature)
            assert feature is not None and value is not None, \
                "A feature name and a value must be provided"
            sample_indices = self.all.index[
                self.all[feature] == value].to_list()

        return sample_indices

    def names(self, what='all'):
        """
        Returns a the names of the columns of the dataset for which the arg
        `what` is specified.
        If it is a list, it returns those feature names in the list,
        And if it is a keywork from: 'all', 'categorical', 'categorical_na',
        'numerical', 'numerical_na', 'complete', then the list of
        features is extracted from the metainformation of the dataset.

        :param what: Possible values are

            * all: (Default) Include very feature, including the target
            * numerical: Only numerical features
            * categorical: Only categorical features
            * complete: Only features without NA
            * numerical_na: Numerical features with NA
            * categorical_na: Categorical features with NA
            * features: Only features, NOT the target variable.
            * target: Only the target variable.
        """
        assert what in self.meta_tags
        return self.meta[what]

    def discretize(self, column, bins, category_names=None):
        """
        Makes a feature, which is normally numerical, categorical by binning its
        contents into the specified buckets.

        Args:
            column: The name of the feature to be binned
            bins: the list of bins as an array of values of the form

                [(15, 20), (20, 25), (25, 30), (30, 35), (35, 40)]

            category_names: An array with names or values we want for our new
                            categories. If None a simple array with ordinal
                            number of the category is used. In the
                            example above, it should be an array from 1 .. 5.

        Returns: The dataset modified

        Example::

            # Variable "x3" contains the number of sons of a person as an
            # integer ranging between values 0 and 10. We want to convert
            # that numerical value into a categorical one with a list
            # of (say) 4 possible values, for the number of sons within
            # given ranges:

            my_data.discretize('x3',
                    [(0, 2), (2, 4), (4, 6), (6, 8)], [1, 2, 3, 4])

        """
        assert column in self.numerical_features, \
            'Feature {} is not numerical, in order to be discretized'.format(
                column)

        bins_tuples = pd.IntervalIndex.from_tuples(bins)
        x = pd.cut(self.features[column].to_list(), bins_tuples)
        if category_names is None:
            x.categories = [i + 1 for i in range(len(bins))]
        else:
            assert len(category_names) == len(bins), \
                "Num of categories passed does not matched number of bins."
            x.categories = category_names
        self.features[column] = x
        self.to_categorical(column)
        self.__update()
        return self

    def onehot_encode(self, feature_names=None):
        """
        Encodes the categorical features in the dataset, with OneHotEncode

        :parameter feature_names: column or list of columns to be one-hot
            encoded.
            The only restriction is that the target variable cannot be
            specifiedin the list of columns and therefore, cannot be
            onehot encoded.
            Default = all categorical features in dataset.
        :return: self

        Example::

            # Encodes a single column named 'my_column_name'
            my_data.onehot_encode('my_column_name')

            # Encodes 'col1' and 'col2'
            my_data.onehot_encode(['col1', 'col2'])

            # Encodes all categorical features in the dataset
            my_data.onehot_encode(my_data.names('categorical'))

        or::

            my_data.onehot_encode()

        """
        if feature_names is None:
            to_encode = list(self.categorical)
        else:
            if isinstance(feature_names, list) is not True:
                to_encode = [feature_names]
            else:
                to_encode = feature_names

        new_df = self.features[
            self.features.columns.difference(to_encode)].copy()
        for column_to_convert in to_encode:
            new_df = pd.concat(
                [new_df,
                 pd.get_dummies(
                     self.features[column_to_convert],
                     prefix=column_to_convert,
                     dtype=float)
                 ],
                axis=1)
        self.features = new_df.copy()
        self.__update()
        return self

    def add_columns(self, new_features):
        """
        Add a Series as a new column to the dataset.

        :param new_features: A pandas Series object or a DataFrame with the
                             data to be added to the Dataset. It must contain
                             a valid name not present in the Dataset already.

        Examples::

            my_data.add_column(my_series)
            my_data.add_column(pandas.Series().values)
            my_data.add_column(my_dataframe)
        """
        if isinstance(new_features, pd.Series):
            if new_features.name is not None:
                if new_features.name in self.names('features'):
                    raise ValueError(
                        'There is already a feature called {}'.format(
                            new_features.name))
                self.features[new_features.name] = new_features.values
            else:
                self.features[
                    'xf{}'.format(self.num_features + 1)] = new_features.values
        elif isinstance(new_features, pd.DataFrame):
            self.features = pd.concat([self.features, new_features], axis=1)
        else:
            raise ValueError(
                'Only pandas Series or DataFrames can be passed to this method')

        self.__update()
        return self

    def drop_columns(self, columns_list):
        """
        Drop one or a list of columns from the dataset.

        :param columns_list: An array-type expression with the names of the
            columns to be removed from the Dataset. In case a single string
            is passed, it will be considered the name of a sinle columns to
            be dropped.

        Examples::

            my_data.drop_columns('column_name')
            my_data.drop_columns(['column1', 'column2', 'column3'])
        """
        if isinstance(columns_list, list) is not True:
            columns_list = [columns_list]
        for column in columns_list:
            if column in self.names('features'):
                self.features.drop(column, axis=1, inplace=True)
        self.__update()
        return self

    def keep_columns(self, to_keep):
        """
        Keep only one or a list of columns from the dataset.

        :param to_keep: A string or array-like expression indicating the
            columns to be kept in the Dataset. The columns not in the list
            of names passed are dropped.

        Example::

            my_data.keep_columns('column_name')
            my_data.keep_columns(['column1', 'column2', 'column3'])
        """
        if isinstance(to_keep, list) is not True:
            to_keep = [to_keep]
        to_drop = list(set(list(self.features)) - set(to_keep))
        self.drop_columns(to_drop)
        return self

    def aggregate(self,
                  col_list,
                  new_column,
                  operation='sum',
                  drop_columns=True):
        """
        Perform an arithmetic operation on the given columns, and places the
        result on a new column, removing the original ones.

        :param col_list: the list of columns over which the operation is done
        :param new_column: the name of the new column to be generated from the
            operation
        :param drop_columns: whether remove the columns used to perfrom the
            aggregation
        :param operation: the operation to be done over the column values for
            each row. Examples: 'sum', 'diff', 'max', etc. By default, the
            operation is the sum of the values.
        :return: The Dataset object

        Example:

        If we want to sum the values of column1 and column2 into a
        new column called 'column3', we use::

            my_data.aggregate(['column1', 'column2'], 'column3', 'sum')

        As a result, ``my_data`` will remove ``column1`` and ``column2``,
        and the operation will be the sum of the values, as it is the default
        operation.
        """
        assert operation in dir(type(self.features))
        for col_name in col_list:
            assert col_name in list(self.features)
        self.features[new_column] = getattr(
            self.features[col_list],
            operation)(axis=1)
        if drop_columns is True:
            self.drop_columns(col_list)
        else:
            self.__update()
        return self

    def drop_samples(self, index_list):
        """
        Remove the list of samples from the dataset.

        :param index_list: The list of indices in the DataFrame to be removed
            from the features and the target DataFrames.
        :return: self
        """
        self.features = self.features.drop(self.features.index[index_list])
        if self.target is not None:
            self.target = self.target.drop(self.target.index[index_list])
        self.features.reset_index(inplace=True, drop=True)
        self.target.reset_index(inplace=True, drop=True)
        self.__update()
        return self

    def nas(self):
        """
        Returns the list of features that present NA entries

        :return: the list of feature names presenting NA
        """
        return self.names('numerical_na') + self.names('categorical_na')

    def replace_na(self, column, value):
        """
        Replace any NA occurrence from the column or list of columns passed
        by the value passed as second argument.

        :param column: Column name or list of column names from which to
            replace NAs with the value passes in the second argument
        :param value: value to be used as replacement
        :return: the object.
        """
        if isinstance(column, list) is True:
            for col in column:
                self.features[col].fillna(value, inplace=True)
        else:
            self.features[column].fillna(value, inplace=True)
        self.__update()
        return self

    def drop_na(self):
        """
        Drop samples with NAs from the features. If any value is infinite
        or -infinite, it is converted to NA, and removed also.

        Examples::

            my_data.drop_na()

        :return: object
        """
        self.features.dropna(inplace=True)
        if self.target is not None:
            self.target = self.target[
                self.target.index.isin(self.features.index)]
            self.target = self.target.reset_index(drop=True)
        self.features = self.features.reset_index(drop=True)
        self.__update()
        return self

    def split(self,
              seed=1024,
              test_size=0.2,
              validation_split=False):
        """
        From an Dataset, produce splits (with or without validation) for
        training and test. The objects of type ``Split`` will only contain
        properties with the names ``train`` or ``test`` to reference the
        different splits.

        :param seed: The seed to be used to generate the random split.
        :param test_size: The test size as a percentage of the base dataset.
        :param validation_split: Boolean indicating whether it is also needed
            to generate a third split for validation purposes, same size
            as the test_size.
        :return: The X and y objects that contain the splits.

        Example::

            # Generate the splits (80-20)
            X, y = my_data.split()

            # Create an instance of the model, and use the training set to
            # fit it, and the test set to score it.
            model = LinearRegression()
            model.fit(X.train, y.train)
            model.score(X.test, y.test)

        """
        assert self.target is not None, \
            "The target variable must be specified before calling this method"

        x = pd.DataFrame(self.features, columns=self.names('features'))
        y = pd.DataFrame(self.target)

        x_train, x_test, y_train, y_test = train_test_split(
            x, y,
            test_size=test_size, random_state=seed)

        if validation_split is True:
            x_train, x_val, y_train, y_val = train_test_split(
                x_train, y_train,
                test_size=test_size, random_state=seed)
            x_splits = [x_train, x_test, x_val]
            y_splits = [y_train, y_test, y_val]
        else:
            x_splits = [x_train, x_test]
            y_splits = [y_train, y_test]

        return Split(x_splits), Split(y_splits)

    def to_numerical(self, to_convert):
        """
        Convert the specified column or columns to numbers

        :param to_convert: column name or list of column names to be converted
        :return: object

        TODO: It must be possible to perform label encoding if specified.
              For example, I might want to convert a target variable with
              strings valued "Yes" and "No" to type "category" or to type
              "int" with values 1 and 0.

        """
        if isinstance(to_convert, list) is not True:
            to_convert = [to_convert]

        for column_name in to_convert:
            if column_name in list(self.features.columns):
                self.features[column_name] = pd.to_numeric(
                    self.features[column_name])
            else:
                self.target = pd.to_numeric(self.target)

        self.__update()
        return self

    def to_float(self, to_convert=None):
        """
        Convert a column or list of columns to float values. The columns must
        be numerical.

        Args:
            to_convert: the column name or list of column names that we want
                        to convert. If this argument is empty, then every
                        numerical feature in the dataset is converted.

        Returns: The dataset

        Example::

            my_data.to_float(my_data.numerical_features)

            # which is equivalent to::
            my_data.to_float()

            # We can also specify a single or multiple features::
            my_data.to_float('feature_15')
            my_data.to_float(['feature_15', 'feature_21'])
        """
        to_convert = self.__assert_list_of_numericals(to_convert)
        for column_name in to_convert:
            self.features[column_name] = pd.to_numeric(
                self.features[column_name]).astype(float)

        return self.__update()

    def to_int(self, to_convert=None):
        """
        Convert a column or list of columns to integer values.
        The columns must be numerical

        Args:
            to_convert: the column name or list of column names that we want
                        to convert. If none specified, all numerical columns
                        are converted to int type.

        Returns: The dataset

        Example::

            my_data.to_int(my_data.numerical_features)

            # which is equivalent to::
            my_data.to_int()

            # We can also specify a single or multiple features::
            my_data.to_int('feature_15')
            my_data.to_int(['feature_15', 'feature_21'])
        """
        to_convert = self.__assert_list_of_numericals(to_convert)

        # Bulk conversion..
        self.features[to_convert] = self.features[to_convert].astype(int)
        return self.__update()

    def to_categorical(self, to_convert):
        """
        Convert the specified column or columns to categories

        :param to_convert: column or column list to be converted
        :return: object
        """
        if isinstance(to_convert, list) is not True:
            to_convert = [to_convert]

        for column_name in to_convert:
            if column_name in list(self.features):
                self.features[column_name] = self.features[column_name].apply(
                    str)
            else:
                self.target = self.target.apply(str)

        self.__update()
        return self

    def merge_categories(self, column, old_values, new_value):
        """
        Merge a subset of categories present in one of the columns into a
        new single category. This is normally done when this list of categs
        is not enough representative.

        :param column: The column with the categories to be merged
        :param old_values: The list of categories to be merged
        :param new_value: The resulting new category after the merge.
        :return: self.

        Example::

            my_data.merge_categories(column='color',
                                     old_values=['grey', 'black'],
                                     new_value='dark')
        """
        assert column in self.categorical, "Column must be categorical"
        assert isinstance(old_values, list), \
            "Old values must be a list of values to be merged"
        assert len(old_values) > 1, \
            "List of values must contains more than 1 value"
        assert new_value is not None, "New value cannot be None"

        self.features[column] = self.features[column].apply(
            lambda x: new_value if x in old_values else x).astype('object')
        self.__update()
        return self

    def merge_values(self, column, old_values, new_value):
        """
        Same method as 'merge_categories' but for numerical values.
        Merge a subset of values present in one of the columns into a
        new single category. This is normally done when this list of values
        is not enough representative.

        :param column: The column with the values to be merged
        :param old_values: The list of values to be merged
        :param new_value: The resulting new value after the merge.
        :return: self.

        Example::

            my_data.merge_values(column='years',
                                     old_values=['2001', '2002'],
                                     new_value='2000')
        """
        assert column in self.numerical, "Column must be numerical"
        assert isinstance(old_values, list), \
            "Old values must be a list of values to be merged"
        assert len(old_values) > 1, \
            "List of values must contains more than 1 value"
        assert new_value is not None, "New value cannot be None"

        self.features[column] = self.features[column].apply(
            lambda x: new_value if x in old_values else x).astype('float64')
        self.__update()
        return self

    #
    # Description methods, printing out summaries for dataset or features.
    #

    def describe_dataset(self):
        """
        Printout the metadata information collected when calling the
        metainfo() method.

        :return: nothing
        """
        if self.meta is None:
            self.__update()

        print('{} Features. {} Samples'.format(
            len(self.meta['features']), self.features.shape[0]))
        print('Available types:', self.meta['description']['dtype'].unique())
        print('  · {} categorical features'.format(
            len(self.meta['categorical'])))
        print('  · {} numerical features'.format(
            len(self.meta['numerical'])))
        print('  · {} categorical features with NAs'.format(
            len(self.meta['categorical_na'])))
        print('  · {} numerical features with NAs'.format(
            len(self.meta['numerical_na'])))
        print('  · {} Complete features'.format(
            len(self.meta['complete'])))
        print('--')
        if self.target is not None:
            print('Target: {} ({})'.format(
                self.meta['target'], self.target.dtype.name))
            if self.target.dtype.name == 'object':
                self.__describe_categorical(self.target)
            else:
                self.__describe_numerical(self.target)
        else:
            print('Target: Not set')
        return

    def describe(self, feature_name=None, inline=False):
        """
        Wrapper.
        Calls the proper feature description method, depending on whether the
        feature is numerical or categorical. If no arguments are passed, the
        description of the entire dataset is provided.

        :param feature_name: The feature to be described. Default value is
            None, which implies that **all** features are described.
        :param inline: whether the output is multiple lines or inline. This
            is used when describing from ``summary()`` function or from
            a console or cell.
        :return: The string, only when inline=True, that contains the
            description.

        TODO: Implement a limit of characters for each line that is printed
              out in the screen, so that when reaching that limit '...' is
              printed.
        """
        if feature_name is None:
            return self.describe_dataset()

        # It could happen that target has not yet been defined.
        target_name = None if self.target is None else self.target.name

        # If feature specified, ensure that it is contained somewhere
        assert feature_name in (list(self.features) + [target_name])

        if feature_name == target_name:
            feature = self.target
        else:
            feature = self.features[feature_name]
        if feature.dtype.name in self.categorical_dtypes:
            return self.__describe_categorical(feature, inline)
        else:
            return self.__describe_numerical(feature, inline)

    def summary(self, what='all'):
        """
        Printout a summary of each feature.

        :param what: Possible values are

            * all: (Default) Include very feature, including the target
            * numerical: Only numerical features
            * categorical: Only categorical features
            * complete: Only features without NA
            * numerical_na: Numerical features with NA
            * categorical_na: Categorical features with NA
            * features: Only features, NOT the target variable.
            * target: Only the target variable.

        :return: N/A
        """
        assert what in self.meta_tags

        max_width = 25
        max_len_in_list = np.max([len(s) for s in list(self.select(what))]) + 2
        if max_len_in_list > max_width:
            max_width = max_len_in_list
        else:
            max_width = max_len_in_list
        formatting = '{{:<{}s}}: {{:<10s}} {{}}'.format(max_width)
        print('Features Summary ({}):'.format(what))
        for feature_name in list(self.select(what)):
            feature_formatted = '\'' + feature_name + '\''
            print(formatting.format(
                feature_formatted, self.select(what)[feature_name].dtype.name,
                self.describe(feature_name, inline=True)))
        return

    def table(self, what='all', max_width=80):
        """
        Print a tabulated version of the list of elements in a list, using
        a max_width display (default 80).

        :param what: Possible values are

            * all: (Default) Include very feature, including the target
            * numerical: Only numerical features
            * categorical: Only categorical features
            * complete: Only features without NA
            * numerical_na: Numerical features with NA
            * categorical_na: Categorical features with NA
            * features: Only features, NOT the target variable.
            * target: Only the target variable.

        :param max_width: The max_width used in the display.
        :return: None
        """
        assert what in self.meta_tags

        f_list = self.names(what)
        if len(f_list) == 0:
            return

        num_features = len(f_list)
        max_length = max([len(feature) for feature in f_list])
        max_fields = int(np.floor(max_width / (max_length + 1)))
        col_width = max_length + 1

        print('-' * ((max_fields * max_length) + (max_fields - 1)))
        for field_idx in range(int(np.ceil(num_features / max_fields))):
            from_idx = field_idx * max_fields
            to_idx = (field_idx * max_fields) + max_fields
            if to_idx > num_features:
                to_idx = num_features
            format_str = ''
            for i in range(to_idx - from_idx):
                format_str += '{{:<{:d}}}'.format(col_width)
            print(format_str.format(*f_list[from_idx:to_idx]))
        print('-' * ((max_fields * max_length) + (max_fields - 1)))
        return

    #
    # Properties
    #

    @property
    def feature_names(self):
        return list(self.features.columns)

    @property
    def numerical_features(self):
        return self.names('numerical')

    @property
    def numerical_features_na(self):
        return self.names('numerical_na')

    @property
    def categorical_features(self):
        return self.names('categorical')

    @property
    def categorical_features_na(self):
        return self.names('categorical_na')

    @property
    def incomplete_features(self):
        return self.categorical_features_na + self.numerical_features_na

    @property
    def num_features(self):
        return self.features.shape[1]

    @property
    def num_samples(self):
        return self.features.shape[0]

    #
    # Plot functions
    #

    @staticmethod
    def plot_correlation_matrix(corr_matrix):
        plt.subplots(figsize=(11, 9))
        # Generate a mask for the upper triangle
        mask = np.zeros_like(corr_matrix, dtype=np.bool)
        mask[np.triu_indices_from(mask)] = True
        cmap = sns.diverging_palette(220, 10, as_cmap=True)
        sns.heatmap(corr_matrix, mask=mask, cmap=cmap, vmax=0.75, center=0,
                    square=True, linewidths=.5, cbar_kws={"shrink": .5})
        plt.show()
        return

    def plot_density(self, feature_names=None, category=None):
        """
        Double density plot(s) between feature(s) and a reference category.

        :param feature_names: The name of a feature(s) in the dataset.
        :param category: The name of the reference category we want to
            represent the double density plot against. If None, then the
            target variable is used.
        :return: None

        Example::

            # represent multiple density plots, one per unique value of the
            # target
            my_data.plot_density(my_feature)

            # represent double density plots, one per unique value of the
            # categorical feature 'my_feature2'
            my_data.plot_density(my_feature1, my_feature2)

            # Plot double density plots for all numerical features.
            my_data.plot_density(my_data.numerical_features)

            # or
            my_data.plot_density()

        """
        if feature_names is None:
            feature_names = self.numerical_features
        if isinstance(feature_names, list):
            num_plots = int(len(feature_names))
            rows = int(num_plots / self.__num_plots_per_row)
            if num_plots % self.__num_plots_per_row != 0:
                rows += 1
            if num_plots >= self.__num_plots_per_row:
                cols = self.__num_plots_per_row
            else:
                cols = num_plots
            plots_left = num_plots
            for j in range(rows):
                plt.figure(figsize=(14, 3))
                for i in range(min(self.__num_plots_per_row, plots_left)):
                    plt.subplot(1, cols, i + 1)
                    self.__plot_double_density(
                        feature_names[i + (j * self.__num_plots_per_row)])
                    plots_left -= 1
                plt.show()
        else:
            self.__plot_double_density(feature_names, category)

    def plot_histogram(self, feature_names=None, category=None):
        """
        Double histogram plot between a feature and a reference category.

        :param feature_names: The name(s) of the feature(s) in the dataset.
        :param category: The name of the reference category we want to
            represent the double density plot against. If None, then the
            target variable is used.
        :return: None

        Example::

            # represent multiple density plots, one per unique value of the
            # target
            my_data.plot_double_hist(my_feature)

            # represent double density plots, one per unique value of the
            # categorical feature 'my_feature2'
            my_data.double_hist(my_feature1, my_feature2)

            # or
            my_data.plot_density()
        """
        if feature_names is None:
            feature_names = self.numerical_features
        if isinstance(feature_names, list):
            num_plots = int(len(feature_names))
            rows = int(num_plots / self.__num_plots_per_row)
            if num_plots % self.__num_plots_per_row != 0:
                rows += 1
            if num_plots >= self.__num_plots_per_row:
                cols = self.__num_plots_per_row
            else:
                cols = num_plots
            plots_left = num_plots
            for j in range(rows):
                plt.figure(figsize=(14, 3))
                for i in range(min(self.__num_plots_per_row, plots_left)):
                    plt.subplot(1, cols, i + 1)
                    self.__plot_double_hist(
                        feature_names[i + (j * self.__num_plots_per_row)])
                    plots_left -= 1
                plt.show()
        else:
            self.__plot_double_hist(feature_names, category)

    def plot_importance(self,
                        num_features=None,
                        num_neighbors=None,
                        abs_imp=False):
        """
        Plots the NUMERICAL features importance, using the ReliefF algorithm as
        implemented in the `rebate` library.

        Args:
            num_features:   The nr of features we want to display. Default is
                            all features.
            num_neighbors:  The nr of neighbors to consider when computing the
                            features importance. Default is 20.
            abs_imp:        if True, importance is displayed taking the ABS()
                            Default value is False.

        Returns:
            None

        """
        if num_features is None:
            num_features = len(self.numerical_features)
        if num_neighbors is None:
            num_neighbors = 20
        vbles_importance = self.features_importance(num_features,
                                                    num_neighbors,
                                                    abs_imp)
        top_features = list(vbles_importance.keys())
        importances = list(vbles_importance.values())

        plt.figure(figsize=(8, 8))
        plt.title("Numerical Features importance (ReliefF)")
        plt.barh(range(num_features), importances,
                 color="#c1d9eb",
                 xerr=np.std(importances),
                 align="center")
        plt.yticks(range(num_features), top_features)
        plt.ylim([-1, num_features])
        plt.show()

    def plot_covariance(self):
        """
        Plots the covariance matrix as explained by scikit contributor
        Andreas Mueller in Columbia lectures, ordering and grouping
        (numerical) features with higher correlation.

        Returns:
            None
        """

        if len(self.numerical_features) == 0:
            raise ValueError('No numerical features to plot.')

        X = scale(self.select('numerical'))
        cov = np.cov(X, rowvar=False)
        order = np.array(
            hierarchy.dendrogram(hierarchy.ward(cov), no_plot=True)['ivl'])
        order = order.astype(np.int)
        ordered_features = [self.numerical_features[i] for i in order]

        plt.figure(figsize=(8, 8), dpi=100)
        plt.title('Covariance Matrix for numerical features')
        plt.imshow(cov[order, :][:, order])
        plt.colorbar(shrink=0.8)
        plt.xticks(range(X.shape[1]), ordered_features)
        plt.yticks(range(X.shape[1]), ordered_features)
        plt.show()

    #
    # Private Methods
    #

    def __assert_list_of_numericals(self, to_convert):
        if to_convert is not None:
            # The list of columns is always a list, although a single
            # argument is passed.
            if isinstance(to_convert, list) is not True:
                to_convert = [to_convert]

            # Safety check
            for feature in to_convert:
                assert feature in self.numerical_features, \
                    'Feature {} is not numerical.'.format(feature)
        else:
            to_convert = self.features.select_dtypes(
                include=[np.number]).columns.tolist()

        return to_convert

    def __assert_category_values(self, category):
        assert category is not None or self.target is not None, \
            'Category cannot be None. Set target or categorical variable first'
        if self.target is not None:
            if category is None or self.target.name == category:
                categories = self.target.unique()
                category_series = self.target
            else:
                raise ValueError('Target variable not set.')
        else:
            assert category in list(self.categorical), \
                '"{}" must be a categorical feature'.format(category)
            categories = self.features[category].unique()
            category_series = self.features[category]

        return categories, category_series

    @staticmethod
    def __numerical_description(feature):
        """
        Build a dictionary with the main numerical descriptors for a feature.

        :param feature: The feature (column) to be analyzed
        :return: A dictionary with the indicators and its values.
        """
        description = dict()
        description['Min.'] = np.min(feature)
        description['1stQ'] = np.percentile(feature, 25)
        description['Med.'] = np.median(feature)
        description['Mean'] = np.mean(feature)
        description['3rdQ'] = np.percentile(feature, 75)
        description['Max.'] = np.max(feature)
        return description

    @staticmethod
    def __describe_categorical(feature, inline=False):
        """
        Describe a categorical column by printing num classes and proportion
        metrics.

        Args:
            feature: The categorical feature to be described.
            inline: Print out without newlines.
        """
        num_categories = feature.nunique()
        cat_names = feature.unique()
        cat_counts = feature.value_counts().values
        cat_proportion = [count / cat_counts.sum()
                          for count in cat_counts]
        if inline is False:
            print('\'', feature.name, '\' (', feature.dtype.name, ')', sep='')
            print('  {} categories'.format(num_categories))
            for cat in range(len(cat_proportion)):
                print('  · \'{}\': {} ({:.04})'.format(
                    cat_names[cat], cat_counts[cat], cat_proportion[cat]))
        else:
            if num_categories <= 4:
                max_categories = num_categories
                trail = ''
            else:
                max_categories = 4
                trail = '...'
            header = '{:d} categs. '.format(num_categories)
            body = '\'{}\'({:d}, {:.4f}) ' * max_categories
            values = [(cat_names[cat], cat_counts[cat], cat_proportion[cat])
                      for cat in range(max_categories)]
            values_flattened = list(sum(values, ()))
            body_formatted = body.format(*values_flattened)
            return header + body_formatted + trail

    @staticmethod
    def __describe_numerical(feature, inline=False):
        """
        Describe a numerical column by printing min, max, med, mean, 1Q, 3Q

        :param feature: The numerical feature to be described.
        :param inline: Default False. Controls whether the description is
            generated in a single line (compact) or paragraph mode.
        :return: nothing
        """
        description = Dataset.__numerical_description(feature)
        if inline is False:
            print('\'', feature.name, '\'', sep='')
            for k, v in description.items():
                print('  · {:<4s}: {:.04f}'.format(k, v))
            return
        else:
            body = ('{}({:<.4}) ' * len(description))[:-1]
            values = [(k, str(description[k])) for k in description]
            values_flattened = list(sum(values, ()))
            body_formatted = body.format(*values_flattened)
            return body_formatted

    def __plot_double_density(self, feature, category=None):
        """
        Plots a double density plot with the feature specified
        """
        # Get the list of categories
        categories, category_series = self.__assert_category_values(category)

        assert feature in self.numerical, '"Feature" must be numerical.'
        # plot a density for each value of the category
        for value in categories:
            sns.distplot(self.features[feature][category_series == value],
                         hist=False, kde=True,
                         kde_kws={'shade': True},
                         label=str(value))

    def __plot_double_hist(self, feature, category=None):
        """
        Plots a double histogram for feature name passed.
        """
        # Get the list of categories
        categories, category_series = self.__assert_category_values(category)

        assert feature in self.numerical, '"Feature" must be numerical.'
        # plot a density for each value of the category
        for value in categories:
            sns.distplot(self.features[feature][category_series == value],
                         hist=True, kde=False,
                         kde_kws={'shade': True},
                         label=str(value))
        plt.legend(loc='best')
