#!/usr/bin/env python

#################################################################
######  Copyright: Regents of the University of Minnesota  ######
#################################################################

import numpy as np
import pdb

def precision_recall_curve(y_true, probas_pred):
    '''
    Calculates precision-recall pairs for different probability thresholds.
    Unlike the scikit-learn version, the returned results 1) contain the
    precision computed on all values (aka the background precision) and 2) only
    contain the first and last precision value for each recall (can reduce size
    of output from 3 GB to < 1 MB for large vectors of y_true/probas_pred).
    
    Returns results in the same format as scikit-learn precision_recall_curve.
    
    '''

    # Check if y_true is acceptable
    y_unique = np.unique(y_true)
    if np.all(y_unique == np.array([0, 1])):
        y_dict = {0: False, 1: True}
    elif np.all(y_unique == np.array([-1, 1])):
        y_dict = {-1: False, 1: True}
    elif np.all(y_unique == np.array([False, True])):
        y_dict = {False: False, True: True}
    else:
        assert False, '\nValues in y_true must be in [0, 1], [-1, 1], or [False, True]'

    # Sorts in descending order, nans go to the end
    sort_inds = np.argsort(-probas_pred)

    tp = 0.
    fp = 0.
    p_last = 0
    precision = [1]
    recall_int = [0]
    thresholds = []

    for i, idx in enumerate(sort_inds):
        if y_dict[y_true[idx]]:
            tp += 1.
        else:
            fp += 1.

        if i == 0:
            recall_int.append(tp)
            precision.append(tp / (tp + fp))
            thresholds.append(probas_pred[idx])
        elif tp > recall_int[-1]:
            # If last observed precision at previous recall was not already
            # added, add it!
            if precision[-1] != p_last:
                recall_int.append(recall_int[-1])
                precision.append(p_last)
                thresholds.append(probas_pred[sort_inds[i-1]])
            # Add current precision at current recall
            recall_int.append(tp)
            precision.append(tp / (tp + fp))
            thresholds.append(probas_pred[idx])
        elif i == len(sort_inds) - 1:
            if (tp / (tp + fp)) != precision[-1]:
                recall_int.append(tp)
                precision.append(tp / (tp + fp))
        
        p_last = tp / (tp + fp)

    return np.array(precision[::-1]), np.array(recall_int[::-1]) / tp, np.array(thresholds[::-1])

def precision_recall_curve_2(y_true, probas_pred):
    '''
    Calculates precision-recall pairs for different probability thresholds.
    Unlike the scikit-learn version, the returned results 1) contain the
    precision computed on all values (aka the background precision) and 2) only
    contain the first and last precision value for each recall (can reduce size
    of output from 3 GB to < 1 MB for large vectors of y_true/probas_pred).
    
    Returns results in the same format as scikit-learn precision_recall_curve.
    
    '''

    # Check if y_true is acceptable
    y_unique = np.unique(y_true)
    if np.all(y_unique == np.array([0, 1])):
        y_dict = {0: False, 1: True}
    elif np.all(y_unique == np.array([-1, 1])):
        y_dict = {-1: False, 1: True}
    elif np.all(y_unique == np.array([False, True])):
        y_dict = {False: False, True: True}
    else:
        assert False, '\nValues in y_true must be in [0, 1], [-1, 1], or [False, True]'

    # Sorts in descending order, nans go to the end
    sort_inds = np.argsort(-probas_pred)

    total_pos = sum(y_dict[x] for x in y_true if y_dict[x])
    tp = 0
    fp = 0
    start_prec = np.repeat(np.nan, total_pos + 1)
    end_prec = np.repeat(np.nan, total_pos + 1)
    start_prec[0] = 1
    end_prec[0] = 1
    start_thresh = np.repeat(np.nan, total_pos + 1)
    end_thresh = np.repeat(np.nan, total_pos + 1)
    start_thresh[0] = 1
    end_thresh[0] = 1

    for i, idx in enumerate(sort_inds):
        if y_dict[y_true[idx]]:
            tp += 1
            start_prec[tp] = end_prec[tp] = tp * 1.0 / (tp + fp)
            start_thresh[tp] = end_thresh[tp] = probas_pred[idx]
        else:
            fp += 1
            end_prec[tp] = tp * 1.0 / (tp + fp)
            end_thresh[tp] = probas_pred[idx]

    dup_inds = start_prec == end_prec
    final_len = (total_pos + 1) * 2 - np.sum(dup_inds)
    recall = np.repeat(np.nan, final_len)
    precision = np.repeat(np.nan, final_len)
    thresholds = np.repeat(np.nan, final_len)
    final_start_inds = np.arange(0, (total_pos + 1) * 2, 2) - np.cumsum(np.hstack([0, dup_inds[:-1]]))
    final_end_inds = np.setdiff1d(np.arange(final_len), final_start_inds)
    precision[final_start_inds] = start_prec
    precision[final_end_inds] = end_prec[np.invert(dup_inds)]
    recall[final_start_inds] = np.arange(total_pos + 1)
    recall[final_end_inds] = np.arange(total_pos + 1)[np.invert(dup_inds)]
    thresholds[final_start_inds] = start_thresh
    thresholds[final_end_inds] = end_thresh[np.invert(dup_inds)]
    pdb.set_trace()

    return precision[::-1], recall[::-1] * 1.0 / total_pos, thresholds[1:][::-1]



