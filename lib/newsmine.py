# -*- coding: utf-8 -*-
"""
Created on Thu Nov 17 11:17:00 2016

@author: amollgaard
"""

import platform
import os
import cPickle as pickle
import numpy as np
import itertools
import datetime
import pytz

################### Variables #######################

# Check the computer name to determine directories
if platform.node() == 'Asparagus':
    post_directory = '/home/amollgaard/Data/FacebookMining/posts'
    article_directory = '/home/amollgaard/Data/FacebookMining/articles'    
if platform.node() == 'UbuntuServer1':
    post_directory = '/home/asparagus/Data/FacebookMining/posts'
    article_directory = '/home/asparagus/Data/FacebookMining/articles'

# Standard filters and variables
filter_standard = {'dt_max':120,'length':15,'passed_min':36000}
filter_2days = {'dt_max':120,'length':15,'passed_min':172800}
excitations = ('reactions','comments','shares')

# Facebook pages for download and analysis
pages_dic = { 
            'danish': 
    ['ditbt','ekstrabladet','metroxpress','tv2nyhederne','jyllandsposten','finans.dk',
    'berlingskebusiness','lokalavisen.dk','nordjyskemedier','stiftstidende','fyensdk','DRNyheder'],
            'english': 
    ['DailyMail','dailymirror','theguardian','TheIndependentOnline','bbcnews','MetroUK'],
            'swedish':
    ['aftonbladet', 'expressen'],
            'norwegian':
    ['vgnett','NRK',],
            'american':
    ['nytimes', 'washingtonpost', 'NYDailyNews', 'HuffingtonPost', 'cnn', 'ABCNews', 
    'NBCNews', 'mashable']
}
pages = [page for sublist in pages_dic.values() for page in sublist]

################## Loader functions #####################

def load_time_scaler(which='all'):
    '''Load and return time scaling, i.e. average circadian acticity.
    
    Returns:
        cbins: array with time of day
        hd: dict with keys (excitation strings) and values (circadian activity array)
    '''
    if which == 'all':
        with open('/home/amollgaard/Dropbox/Projekter/NewsMining/objects/time_scaler_all.p','rb') as f:
            cbins,hd = pickle.load(f)
        return cbins,hd
        
        
def load_response_function():
    '''Load and return response_time (array), response_function (array),
    and reponse_error (array).'''
    
    with open('/home/amollgaard/Dropbox/Projekter/NewsMining/objects/response_function.p','rb') as f:
        response_time,response_function,response_error = pickle.load(f)
    return response_time,response_function,response_error


############### Misc #####################################

def diffx(x):
    x = np.array(x)
    return x[1:] - x[:-1]
    

def halfway(bins):
    bins = np.array(bins)
    return 0.5*(bins[1:]+bins[:-1])
    

def time_to_epoch(t='2011-12-21 00:00:00',form = "%Y-%m-%d %H:%M:%S",tz='utc'):
    '''New York: EST5EDT. Copenhagen: Europe/Copenhagen.'''

    date_aware = datetime.datetime.strptime(t, form).replace(tzinfo=pytz.timezone(tz))
    pytz_object = pytz.timezone(tz)
    time_shift = int(pytz_object.normalize(date_aware).strftime('%z')[:-2])
    date_utc = datetime.datetime.strptime(t, form)
    epoch = datetime.datetime(1970,1,1)
    dt = date_utc - epoch
    seconds = dt.total_seconds() - time_shift * 3600

    return seconds
    

############ Filter function ############################

def filter_post(post,filters={}):
    '''Returns True if the post meets the filters and False if not.
    
    Filter arguments (optional):
        length: minimum length of time series
        dt_max: maximum time difference between first N=length entries in time series
        passed_min: minimum time extend of series as measured from creation time
        followers_minimum: minimum number of followers of the page creating the post
        reactions_minimum: minimum number of final reactions in series
        comments_minimum: minimum number of final comments in series
        shares_minimum: minimum number of shares in series
    '''
    
    if 'dt_max' in filters:
        dt_max = filters['dt_max']
        length = filters['length']
        passed_min = filters['passed_min']
        try:
            created = post['created_time']['timestamp']
            timestamps = post['timestamps']
            # Check time series length criteria
            if timestamps.shape[0] < length:
                return False
            # Check time interval criteria
            dt_timestamps = timestamps[1:length+1] - timestamps[:length]
            if timestamps[0] - created > dt_max or np.any(dt_timestamps > dt_max):
                return False
            # Check time extend criteria
            if timestamps[-1] - created < passed_min:
                return False
        except:
            return False
    
    if 'followers_minimum' in filters:
        followers_minimum = filters['followers_minimum']
        try:
            followers = post['from']['fan_count']
            if followers < followers_minimum:
                return False
        except:
            return False
    
    for excitations_min, excitation in (('reactions_minimum','reactions'),('comments_minimum','comments'),('shares_minimum','shares')):
        if excitations_min in filters:
            excitations_minimum = filters[excitations_min]
            try:
                excitations_final = post[excitation][-1]
                if excitations_final < excitations_minimum:
                    return False
            except:
                return False
    
    return True
    
    
############# Get files ##################################        
        
def open_post_file(name='20161227T131737_ID=228735667216_10154250297787217',page='bbcnews'\
,data_directory=post_directory):
    '''Load and return post file with given name.'''
    
    with open('%s/%s/%s.p'%(data_directory,page,name), 'rb') as f:
        post = pickle.load(f)
    
    return post


def search_for_post(ID='115634401797120_1597374340289778',data_directory=post_directory):
    '''Searches for a post ID in the data_directory and return post_object.'''
    
    for root, dirnames, filenames in os.walk(data_directory):
        for filename in filenames:
            if ID in filename:
                path = os.path.join(root, filename)
                with open(path,'rb') as f:
                    post = pickle.load(f)
                return post
    

class pageposts_iter:
    '''Iterator class of the (post- or article-) directory of a page/media. Files in 
    skip_list are ignored, and so are any files that do not pass the filter.
    
    Args:
        page: string
        timestamp_min: False or integer/float
        filters: dictionary
        skip_list: list of files
        data_directory: string specifying path to dict
    
    Returns:
        page: string
        path: string
        post: dictionary
    
    Raises:
        StopIteration, when it runs out of files that pass the criterias.
    '''
    
    def __init__(self,page,timestamp_min=False,timestamp_max=False,filters={},skip_list=[],data_directory=post_directory):
        self.page = page
        self.dir = '%s/%s/'%(data_directory,page)
        self.filters = filters
        # Ignore posts outside timeframe if timeframe stated. Create list with paths of files
        if timestamp_min:
            if type(timestamp_min) == str:
                timestamp_min = time_to_epoch(timestamp_min,"%Y%m%dT%H%M%S",'utc')
            if type(timestamp_max) == str:
                timestamp_max = time_to_epoch(timestamp_max,"%Y%m%dT%H%M%S",'utc')
            if not timestamp_max:
                timestamp_max = timestamp_min + 86400
            self.post_paths = [ os.path.join(self.dir, filename) for filename in os.listdir(self.dir) \
            if os.path.isfile(os.path.join(self.dir, filename)) and timestamp_min <= \
            time_to_epoch(filename[:15],"%Y%m%dT%H%M%S",'utc') <= timestamp_max  ]
        else:
            self.post_paths = [ os.path.join(self.dir, filename) for filename in os.listdir(self.dir) \
            if os.path.isfile(os.path.join(self.dir, filename)) ]
        # Ignore files in skip_list
        if skip_list:
            self.post_paths = [ path for path in self.post_paths if path.split('/')[-1] not in skip_list ]
        self.post_paths_iter = iter(self.post_paths)
        self.index_current = -1
        self.index_max = len(self.post_paths) - 1
    
    def __iter__(self):
        return self
    
    def next(self):
        # Introduce while loop to allow skipping of file paths that dont pass filter
        while True:
            if self.index_current == self.index_max:
                raise StopIteration
            else:
                # Iterate by increasing index and getting next post_path
                self.index_current += 1
                self.post_path = next(self.post_paths_iter)
                # Open file
                try:
                    with open(self.post_path,'rb') as f:
                        self.post = pickle.load(f)
                except:
                    print '\nPath failed: %s\n'%self.post_path
                    continue
                # Filter post
                if self.filters:
                    if not filter_post(self.post,self.filters):
                        continue
                # Finally, return variables
                return self.page,self.post_path,self.post
            

def generate_pageposts_iters(pages=False,timestamp_min=False,timestamp_max=False,filters={},\
skip_dic={},data_directory=post_directory):
    '''Construct a function with a yield method, thereby allowing the pageposts_iters
    to be chained into one iterator'''
    
    if type(pages) == bool:
        pages = [ page for page in os.listdir(data_directory) if os.path.isdir(os.path.join(data_directory,page))]
    else:
        pages = pages
    
    for page in pages:
        if skip_dic and page in skip_dic:
            skip_list = skip_dic[page]
        else:
            skip_list = []
        yield pageposts_iter(page,timestamp_min,timestamp_max,filters,skip_list,data_directory)
        

def pagesposts_iter(pages=False,timestamp_min=False,timestamp_max=False,filters=filter_standard,skip_dic={},data_directory=post_directory):
    '''Iterator class for the posts/articles belonging to specified pages. Further filtering
    of posts/articles allowed by filters.
    
    Args:
        page: string
        timestamp_min: False or integer/float
        filters: dictionary
        skip_list: list of files
        data_directory: string specifying path to dict
    
    Returns:
        page: string
        path: string
        post: dictionary
    
    Raises:
        StopIteration, when it runs out of files that pass the criterias.
    '''
    return itertools.chain.from_iterable(generate_pageposts_iters(pages,timestamp_min,timestamp_max,filters,skip_dic,data_directory))

    
    