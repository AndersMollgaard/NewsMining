# -*- coding: utf-8 -*-
"""
Created on Thu Nov 17 11:06:44 2016

@author: amollgaard
"""

from ..lib import newsmine as nm
from ..postanalysis import models
import numpy as np
import cPickle as pickle
from matplotlib import pyplot as plt
from sklearn.metrics import r2_score
from scipy.stats import spearmanr

    
############## Plotting ##########################################

def plot_signals(signals,normalization=36000,bins=100):
    '''Plots each signal along with an average signal.
    
    Args:
        signals: list of tuples (time,sig_vals)
        normalization: False or integer denoting the time of the sig_val used 
        for normalization
    '''
    
    time = np.linspace(0, 2*normalization, bins)
    signal_matrix = np.zeros((len(signals), bins))
    
    # Plot each signal along with average statistics
    plt.figure(figsize=(15,12))
    for ii,(t,x) in enumerate(signals):
        if normalization:
            norm = np.interp(normalization,t,x)
            x = x / norm
        signal_matrix[ii,:] = np.interp(time,t,x)
        plt.plot(t,x)
    signal_mean = np.mean(signal_matrix,axis=0)
    signal_spread = np.std(signal_matrix,axis=0)
    plt.plot(time,signal_mean,color='k',linewidth=5)
    plt.fill_between(time, 
                     signal_mean - signal_spread, 
                     signal_mean + signal_spread,
                     color='k',
                     alpha=0.2,
                     zorder=10)
    if normalization:
        plt.xlim(0,normalization * 2)
        plt.ylim(0,2)
    
    return time, signal_mean, signal_spread


############### Helper functions #######################################

def signal_offsetting(post):
    '''Returns dictionary with "t" (time since creation array), along with an
    array for each excitation.
    '''
    t = post['timestamps'] - post['created_time']['timestamp']
    reactions = post['reactions'][:]
    comments = post['comments'][:]
    shares = post['shares'][:]
    if t[0] == 0:
        reactions[0] = 0
        comments[0] = 0
        shares[0] = 0
    else:
        t = np.concatenate((np.array([0]), t))
        reactions = np.concatenate((np.array([0]), reactions))
        comments = np.concatenate((np.array([0]), comments))
        shares = np.concatenate((np.array([0]), shares))
    d = { 't': t, 'reactions': reactions, 'comments': comments, 'shares': shares}
    return d
        

def signal_average(signal_tuples,time_interpolated=np.arange(0,216000,60.)):
    '''Interpolate signals and return average and spread of signals.
    
    Args:
        signal_tuples: list of tuples (time, sig_vals)
    '''
    signal_matrix = np.zeros((len(signal_tuples),len(time_interpolated)))
    for ii,signal_tuple in enumerate(signal_tuples):
        signal_interpolated = np.interp(time_interpolated,
                                        signal_tuple[0],
                                        signal_tuple[1],
                                        right=np.nan)
        signal_matrix[ii,:] = signal_interpolated
    signal_mean = np.nanmean(signal_matrix,axis=0)
    signal_spread = np.nanstd(signal_matrix,axis=0)
    Nsignals = signal_matrix.shape[0]
    return  time_interpolated, signal_mean, signal_spread, Nsignals
    
    
############## Response function ##################################
    
def calc_response_function():
    '''Calculate a response function based on posts specified in code. The
    response function should represent an average response function in cases,
    where no spreading is present.
    '''
    
    # Define filters
    filters = nm.filter_2days
    
    # Construct signal_tuples
    signal_tuples = [ (post['timestamps']-post['created_time']['timestamp'],post['reactions']) \
                      for page,path,post in nm.pagesposts_iter(['bbcnews'],filters=filters) \
                      if 100 < post['shares'][-1] < 1000 ]
    
    # Normalize ccording to end interpolation value
    time_interpolated = np.arange(0, 172800, 60.)
    signal_tuples = [ (t, x / float(np.interp([172800],t,x)[0])) for t,x in signal_tuples ]
    
    # Response function
    t,x,xe,n = signal_average(signal_tuples,time_interpolated)
    
    # Save
    with open('/home/amollgaard/Dropbox/Projekter/FacebookMining/objects/response_function.p','wb') as f:
        pickle.dump((t,x,xe),f)
    
    return t,x,xe
    
    
################ Model testing ######################################

# Define model parameters
while True:
    try:
        model1_params = {'response_time': response_time1, 'response_function': response_function1}
        SeismicSimple_params = {'response_time': response_time1, 
                                'response_function': response_function1, 
                                'followers_avg': 300}
        break
    except:
        response_time1, response_function1, reponse_error1 = nm.load_response_function()


def model_predict_final(fit_params,model):
    '''Return prediction of final excitation strength based on fit parameters and model.
    
    Args:
        fit_params: dictionary
        model: model instance
    '''
    
    model.fit(**fit_params)
    finalX = model.predict_final()
    return finalX
    

def model_testing(posts,
                  t_input_max=600,
                  excitation='reactions',
                  Model=models.Model1,
                  params=model1_params):
    '''Test a model class with given parameters on a sample of posts.'''
    
    # Predicted and target value lists
    infectiousness = []
    predictions = []
    targets = []
    
    # Iterate posts an predict for each using Model
    model = Model(**params)
    for post in posts:
        
        # Get input variables
        fan_count = post['from']['fan_count']
        d = signal_offsetting(post)
        t = d['t']
        x = d[excitation]
        index_max = t.searchsorted(t_input_max)
        
        # Get fit parameters 
        if Model == models.Model1:
            fit_params = {'t': t[:index_max], 
                          'x': x[:index_max], 
                          'fan_count': fan_count}
        if Model == models.SeismicSimple:
            fit_params = {'t': t[:index_max], 
                          'x': x[:index_max], 
                          'fan_count': fan_count,
                          'shares': d['shares'][:index_max]}
        
        #Prediction and target
        prediction, infect = model_predict_final(fit_params, model)
        infectiousness.append(infect)
        predictions.append(prediction)
        targets.append(x[-1])
    
    # Evaluate predictions
    infectiousness = np.array(infectiousness)
    predictions = np.array(predictions)
    targets = np.array(targets)
    indices_not_inf = np.logical_not(np.isinf(predictions))
    R2 = r2_score(targets[indices_not_inf], predictions[indices_not_inf])
    print 'R2, target-predict:', R2
    rank_corr = spearmanr(targets,infectiousness)
    print 'Spearman rank coeff, target-infect:', rank_corr[0]
    
    # Scatterplot of target-prediction pairs
    plt.figure(figsize=(12,12))
    plt.plot([0,max(targets)], [0,max(targets)], linewidth=2, color='k', zorder=-1)
    plt.scatter(targets,predictions)
    
    return targets,predictions





