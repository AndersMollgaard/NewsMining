# -*- coding: utf-8 -*-
"""
Created on Tue Jan 10 10:05:02 2017

@author: amollgaard
"""

from NewsMining.lib import newsmine as nm
from timezonefinder import TimezoneFinder
import numpy as np
import cPickle as pickle
import tools as ts
from matplotlib import pyplot as plt
from matplotlib import cm
from analyse_posts import plot_signals

############## Circadian scale factor ######################

def get_timezones(pages=[]):
    '''Return page_info with updates timezone info.'''

    # Saved timezone information
    with open('objects/page_info.p','rb') as f:
        page_info = pickle.load(f)
    
    # Update if information missing
    miss_tz_pages = list(set(pages) - set(page_info.keys()))
    if miss_tz_pages:
        tf = TimezoneFinder()
        posts_dic = testmining.get_posts_divide(pages=miss_tz_pages,post_limit=1)
        for page in posts_dic:
            try:
                longitude = posts_dic[page]['data'][0]['from']['location']['longitude']
                latitude = posts_dic[page]['data'][0]['from']['location']['latitude']
                timezone = tf.timezone_at(lng=longitude,lat=latitude)
                page_info[page]['timezone'] = timezone
            except:
                print '{:20s} has no location information'.format(page)
                timezone = raw_input('Give timezone: ')
                page_info[page] = timezone
        with open('objects/page_info.p','wb') as f:
            pickle.dump(page_info,f)
    
    return page_info
            

def comp_time_scaler(pages=['ditbt'],filters={},Nbins=24,view=False):
    
    page_info = get_timezones(pages)
    bins = np.linspace(0,86400,Nbins+1)
    cbins = ts.halfway(bins) / 3600.
    histo_dic = { page : { excitation : np.zeros(Nbins) for excitation in nm.excitations} for page in pages }
    
    # Iterate posts and add contribution to histo_dic
    for page,path,post in nm.pagesposts_iter(pages,filters=filters):
        
        # Add post info to histo_dic
        timestamps = post['timestamps']
        timestamps_halfway = ts.halfway(timestamps)
        days,tods = ts.weekday_and_time(timestamps_halfway,page_info[page]['timezone'])
        for excitation in nm.excitations:
            signal = post[excitation]
            signal_increase = ts.diff(signal)
            histogram,bins_ = np.histogram(tods,bins,weights=signal_increase)
            histo_dic[page][excitation] += histogram
    
    # Normalize the statistics of each page
    for page in pages:
        # Remove low stats pages
        if np.sum(histo_dic[page]['reactions']) < 1000:
            print 'Removing {} due to small statistics.'.format(page)
            del histo_dic[page]
            continue
        for excitation in nm.excitations:
            histogram = histo_dic[page][excitation]
            avg = np.mean(histogram)
            histo_dic[page][excitation] = histogram / avg
    
    # View histogram for each page seperately
    if view:
        for page in histo_dic:
            ts.plotter(cbins,histo_dic[page].values(),Title=page)
            
    # Average over pages
    histo_dic = { excitation : np.mean(np.array([ histo_dic[page][excitation] for page in histo_dic ]), axis=0) for excitation in nm.excitations }
    
    return cbins,histo_dic


def expand_time(created_time,timestamps,binwidth=600):
    
    # Add timestamp at created_time (simple) and possibly also timestamps up
    # to the first timestamp in timestamps
    if binwidth == 'simple':
        timestamps_pre = np.array([created_time])
    else:
        timestamps_pre = np.arange(created_time,timestamps[0],binwidth)
    timestamps_expanded = np.concatenate((timestamps_pre,timestamps))
    
    # Calculate time passed between two consecutive measurements and find the
    # time of day
    timestamps_expanded_dt = ts.diff(timestamps_expanded)
    timestamps_expanded_halfway = ts.halfway(timestamps_expanded)
    days,tods = ts.weekday_and_time(timestamps_expanded_halfway)
    
    return timestamps_expanded,timestamps_expanded_dt,tods


################## Scale time ######################################

def scale_time(timestamps_expanded_dt,tods,cbins,time_scaler,scale_weight=1.):
    '''Scale the time intervals by the activity at the time of day'''
    scaling = np.interp(tods,cbins,time_scaler,period=86400.)
    timestamps_expanded_dt_scaled = (scale_weight * scaling + ( 1. - scale_weight )) * timestamps_expanded_dt
    time_passed = np.cumsum(timestamps_expanded_dt_scaled)
    return time_passed
    

def scaled_time_signals(pages=testmining.pages,excitation='reactions',passed_min=36000,scale_weight=1.,filters=False):

    # Set post filter and load time scaler
    if not filters:
        filters={'dt_max':120,'length':15,'passed_min':passed_min,'followers_min':1000000,'{}_minimum'.format(excitation):1000}
    cbins,histo_dic = nm.load_time_scaler()
    
    # Iterate signals and scale individual time measurements
    signals = []
    for page, post_path, post in nm.pagesposts_iter(pages,filters=filters):
        timestamps_expanded,timestamps_expanded_dt,tods = expand_time(post['created_time']['timestamp'],post['timestamps'])
        time_passed = scale_time(timestamps_expanded_dt,tods,cbins,histo_dic[excitation],scale_weight)
        signals.append((time_passed, post[excitation]))
    
    return signals
    

############## Scale signal ####################################

def scale_signal(signal,tods,cbins,signal_scaler,scale_weight=1.):
    '''Scale the signal by the inverse activity at the time of day'''
    signal_dt = np.concatenate((signal[:1], signal[1:] - signal[:-1]))
    scaling = np.interp(tods,cbins,signal_scaler,period=86400.)
    signal_dt_scaled = (scale_weight * scaling + ( 1. - scale_weight )) * signal_dt
    signal_scaled = np.concatenate((np.zeros(1), np.cumsum(signal_dt_scaled)))
    return signal_scaled
    

def scaled_signals(pages=testmining.pages,excitation='reactions',passed_min=36000,scale_weight=1.,filters=False):
    
    # Set post filters and load scaling
    if not filters:
        filters={'dt_max':120,'length':15,'passed_min':passed_min,'followers_min':1000000,'{}_minimum'.format(excitation):1000}
    cbins,histo_dic = nm.load_time_scaler()
    signal_scaler = 1. / histo_dic[excitation]
    
    # Iterate signals and scale them
    signals = []
    for page, post_path, post in nm.pagesposts_iter(pages,filters=filters):
        created_time = post['created_time']['timestamp']
        signal = post[excitation]
        timestamps_expanded,timestamps_expanded_dt,tods = expand_time(created_time,post['timestamps'],binwidth='simple')
        signal_scaled = scale_signal(signal,tods,cbins,signal_scaler,scale_weight=scale_weight)
        signals.append((timestamps_expanded-created_time, signal_scaled))
    
    return signals

############# Compare scalings ############################

def compare_scalings(pages=testmining.pages,time_scale_weights=[1.],signal_scale_weights=[1.]):
    '''Calculate the average normalized signal and its spread for different
    scalings. Finally, compare the spreads to check for lowest noise.'''
    
    # Unscaled signal statistics
    signals_unscaled = scaled_time_signals(pages,scale_weight=0)
    t_unscaled,x_unscaled,xe_unscaled = plot_signals(signals_unscaled)
    plt.close()
    
    # Scaled time statistics
    signals_scaled_time = []
    for time_scale_weight in time_scale_weights:
        signals = scaled_time_signals(pages,scale_weight=time_scale_weight)
        t,x,xe = plot_signals(signals)
        signals_scaled_time.append( (t,x,xe) )
        plt.close()
    
    #Scaled signal statistics
    signals_scaled = []
    for signal_scale_weight in signal_scale_weights:
        signals = scaled_signals(pages,scale_weight=signal_scale_weight)
        t,x,xe = plot_signals(signals)
        signals_scaled.append( (t,x,xe) )
        plt.close()
    
    #Plot the normalized signals spread for the different scalings
    plt.figure(figsize=(15,12))
    plt.plot(t_unscaled,xe_unscaled,label='unscaled',linewidth=2,color='k')
    for scale_weight,(t,x,xe) in zip(time_scale_weights,signals_scaled_time):
        plt.plot(t,xe,label='time scaled %.2f'%scale_weight,color=cm.Reds(scale_weight*0.7))
    for scale_weight,(t,x,xe) in zip(signal_scale_weights,signals_scaled):
        plt.plot(t,xe,label='signals scaled %.2f'%scale_weight,color=cm.Greens(scale_weight*0.7))
    plt.legend(fontsize=30)
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=25,pad=10,length=7,width=2)