#################################################################
######  Copyright: Regents of the University of Minnesota  ######
#################################################################

VERSION='2.2.5'

# Here I wrap the core dataset clustering function with functions
# that send specific datasets to it and define specific output
# locations for the cluster files.
import os,sys
import numpy as np
import pandas as pd
import gzip
import cPickle

import cluster_dataset as clus
from cg_common_functions import get_verbosity, get_sample_table, get_barcode_table, parse_yaml


def get_lane_data_path(config_params, lane_id):

    output_folder = config_params['output_folder']
    return os.path.join(output_folder, 'intermediate', lane_id)

def get_lane_interactions_path(config_params, lane_id):

    output_folder = config_params['output_folder']
    return os.path.join(output_folder, 'interactions', lane_id)

def get_detection_limits(config_params):

    sample_detection_limit = float(config_params['sample_detection_limit'])
    control_detection_limit = float(config_params['control_detection_limit'])

    return sample_detection_limit, control_detection_limit

def get_dumped_count_matrix_filename(config_params, lane_id):

    lane_folder = get_lane_data_path(config_params, lane_id)
    return os.path.join(lane_folder, '{}_barseq_matrix.dump.gz'.format(lane_id))

def load_dumped_count_matrix(config_params, lane_id):

    filename = get_dumped_count_matrix_filename(config_params, lane_id)
    f = gzip.open(filename, 'rb')
    barcodes, conditions, matrix = cPickle.load(f)
    dataset = [np.array(barcodes), np.array(conditions), matrix]
    f.close()

    return dataset

def get_clustered_count_matrix_filename(config_params, lane_id):

    lane_folder = get_lane_data_path(config_params, lane_id)
    return os.path.join(lane_folder, '{}_barseq_matrix'.format(lane_id))

def get_dumped_zscore_matrix_filename(config_params, lane_id):

    lane_interactions_path = get_lane_interactions_path(config_params, lane_id)
    return os.path.join(lane_interactions_path, '{}_scaled_dev.dump.gz'.format(lane_id))
    
def load_dumped_zscore_matrix(config_params, lane_id):

    filename = get_dumped_zscore_matrix_filename(config_params, lane_id)
    f = gzip.open(filename, 'rb')
    barcodes, conditions, matrix = cPickle.load(f)
    dataset = [np.array(barcodes), np.array(conditions), matrix]
    f.close()

    return dataset

def get_clustered_zscore_matrix_filename(config_params, lane_id):

    lane_interactions_path = get_lane_interactions_path(config_params, lane_id)
    return os.path.join(lane_interactions_path, '{}_scaled_dev'.format(lane_id))

def customize_strains(strains, barcode_table, fmt_string, verbosity = 1):

    barcode_table = barcode_table.set_index('Strain_ID', drop = False)
    barcode_table_cols = barcode_table.columns.values
    
    cols_with_commas = [',' in x for x in barcode_table_cols]
    if np.any(cols_with_commas):
        num_with_commas = np.sum(cols_with_commas)
        raise ColumnError('{} barcode table column names contain commas,\nwhich must be addressed before visualizing'.format(num_with_commas))

    custom_columns = fmt_string.split(',')
    assert all([x in barcode_table.columns for x in custom_columns]), "Not all of the specified columns are in the provided barcode table ({})".format(';'.join(list(set(custom_columns) - set(barcode_table.columns))))
    custom_barcode_table = barcode_table[custom_columns]
    #strain_keys = [tuple(strain) for strain in strains]
    strain_keys = strains[:]
    
    custom_strains = []
    for strain in strain_keys:
        # print strain
        assert strain in custom_barcode_table.index, "Strain {} in the dataset not found in the barcode table. Make sure you have specified the correct barcode table!".format(strain)
        custom_strain = custom_barcode_table.ix[strain].values
        custom_strain_strings = [str(x) for x in custom_strain]
        custom_strain_final = '_'.join(custom_strain_strings)
        if verbosity >= 3:
            #print strain
            #print custom_barcode_table.ix[strain]
            print custom_strain
            #print custom_strain_strings
            print custom_strain_final
        custom_strains.append(custom_strain_final)

    return np.array(custom_strains)

def customize_conditions(conditions, sample_table, fmt_string, verbosity = 1):

    sample_table = sample_table.set_index(['screen_name', 'expt_id'], drop = False)
    sample_table_cols = sample_table.columns.values
    
    cols_with_commas = [',' in x for x in sample_table_cols]
    if np.any(cols_with_commas):
        num_with_commas = np.sum(cols_with_commas)
        raise ColumnError('{} sample table column names contain commas,\nwhich must be addressed before visualizing'.format(num_with_commas))

    custom_columns = fmt_string.split(',')
    assert all([x in sample_table.columns for x in custom_columns]), "Not all of the specified columns are in the provided sample table"
    custom_sample_table = sample_table[custom_columns]
    condition_keys = [tuple(cond) for cond in conditions]
    
    custom_conditions = []
    for cond in condition_keys:
        assert cond in custom_sample_table.index, "Condition {} in the dataset not found in the sample table. Make sure you have specified the correct sample table!".format(cond)
        custom_cond = custom_sample_table.ix[cond].values
        custom_cond_strings = [str(x) for x in custom_cond]
        custom_cond_final = '_'.join(custom_cond_strings)
        if verbosity >= 3:
            #print cond
            #print custom_sample_table.ix[cond]
            print custom_cond
            #print custom_cond_strings
            print custom_cond_final
        custom_conditions.append(custom_cond_final)

    return np.array(custom_conditions)


# Define an error class to handle when the sample table columns
# have commas
class ColumnError(Exception):
    '''
    Raise when a table's columns contain commas
    and the code is trying to reference those
    columns to customize row/column names in
    the clustering output.
    '''

# In the future, these functions will take in inputs to customize
# the output (the CDT labels)
# In the future, these functions will take in inputs to customize
# the output (the CDT labels)
def cluster_count_matrix(config_file, lane_id, strain_fmt_string, cond_fmt_string):

    config_params = parse_yaml(config_file)

    sample_detection_limit, control_detection_limit = get_detection_limits(config_params)

    # If the file does not exist, then do not attempt to cluster it!
    try:
        genes, conditions, matrix = load_dumped_count_matrix(config_params, lane_id)
    except IOError:
        print "could not find '{}' count matrix".format(lane_id)
        return None

    thresholded_matrix = matrix
    
    thresholded_matrix[thresholded_matrix < sample_detection_limit] = sample_detection_limit
    logged_matrix = np.log2(thresholded_matrix)

    # Customize the strain and condition names for interpretable visualization!
    custom_genes = customize_strains(genes, config_params, strain_fmt_string, verbosity = get_verbosity(config_params))
    custom_conditions = customize_conditions(conditions, config_params, cond_fmt_string, verbosity = get_verbosity(config_params))

    dataset = [custom_genes, custom_conditions, logged_matrix]

    f = get_clustered_count_matrix_filename(config_params, lane_id)
    record, rows_tree, cols_tree = clus.cluster(dataset, file_base = f)

    record.save(f, rows_tree, cols_tree)


def cluster_zscore_matrix(config_file, lane_id, strain_fmt_string, cond_fmt_string):

    config_params = parse_yaml(config_file)

    # If the file does not exist, then do not attempt to cluster it!
    try:
        genes, conditions, matrix = load_dumped_zscore_matrix(config_params, lane_id)
    except IOError:
        print "could not find '{}' zscore matrix".format(lane_id)
        return None
    
    # Customize the strain and condition names for interpretable visualization!
    strain_table = get_barcode_table(config_params)
    sample_table = get_sample_table(config_params)
    custom_genes = customize_strains(genes, strain_table, strain_fmt_string, verbosity = get_verbosity(config_params))
    custom_conditions = customize_conditions(conditions, sample_table, cond_fmt_string, verbosity = get_verbosity(config_params))

    dataset = [custom_genes, custom_conditions, matrix]
    
    f = get_clustered_zscore_matrix_filename(config_params, lane_id)
    record, rows_tree, cols_tree = clus.cluster(dataset, file_base = f)

    record.save(f, rows_tree, cols_tree)

    # return the filename so the cdt/atr/gtr files can be copied to a directory with all
    # of the other clustergrams and eventually tarred/gzipped for distribution!
    return f

def cluster_one_stacked_matrix(dataset, matrix_id, strain_table, sample_table, strain_fmt_string, cond_fmt_string, output_folder, new_matrix = None, verbosity = 1):

    genes, conditions, matrix = dataset

    custom_genes = customize_strains(genes, strain_table, strain_fmt_string, verbosity = verbosity)
    custom_conditions = customize_conditions(conditions, sample_table, cond_fmt_string, verbosity = verbosity)

    dataset = [custom_genes, custom_conditions, matrix]
    
    f = os.path.join(output_folder, matrix_id)
    
    record, rows_tree, cols_tree = clus.cluster(dataset, file_base = f, new_matrix = new_matrix)
    record.save(f, rows_tree, cols_tree)

    # return the filename so the cdt/atr/gtr files can be copied to a directory with all
    # of the other clustergrams and eventually tarred/gzipped for distribution!
    return f



