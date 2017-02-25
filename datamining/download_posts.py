# -*- coding: utf-8 -*-
"""
Created on Sat Nov  5 08:15:36 2016

@author: amollgaard
"""

from ..lib import newsmine as nm
import time
import requests
import platform
import os
import pickle
import numpy as np

################### Authorize ###################################
print 'Access token wil expire 06/03/2017 14:56 Copenhagen'
app_id = '176850349063593'
app_secret = '7f16661417c8ae95e34a02c60f10f3bc'
access_token = 'EAACg2C47ZCakBAMEuSj1egXe1YVaUaT1Qe9ZBj80b5GDuigeDeRYlqZCmCcUVHPiK0EUM8xFQuoRZA4Y8su4Q3k2q79X7y8ZBQZB0AfxMNCVm1m3BNn2P5cb87HM572ZCSk3GlztOp1U5bDZA6AMuVVt'
#graph = facebook.GraphAPI(access_token,version='2.7')

########### Variables #############################

graph_url = "https://graph.facebook.com/v2.8/"

if platform.node() == 'Asparagus':
    data_directory = '/home/amollgaard/Data/FacebookMining/posts'
if platform.node() == 'kaoslx07.biocmplx.nbi.dk':
    data_directory = '/home.lx07/cmplx/amoellga/Data/FacebookMining/posts'
if platform.node() == 'UbuntuServer1':
    data_directory = '/home/asparagus/Data/FacebookMining/posts'

pages = nm.pages
post_fields = ['id','created_time','description','from{id,name,fan_count,link,website,location{city,latitude,longitude}}','link','message','shares','reactions.limit(0).summary(1)','comments.limit(0).summary(1)']
post_limit = 100
page_limit = 10

############## Misc ##############################

#https://graph.facebook.com/me/feed?message="Hello, World."&amp;access_token={your-access-token}
#posts = graph.get_object('ditbt/posts?limit=50&fields=message,shares,reactions.limit(3).summary(1){fields=id,type},comments.limit(3).summary(1){message}')
#posts = graph.get_object('posts?ids=ditbt,ekstrabladet&limit=50&fields=id,created_time,description,from,link,message,shares,reactions.limit(0).summary(1),comments.limit(0).summary(1)')
#https://graph.facebook.com/v2.6/posts?ids=aftonbladet,expressen,ditbt,ekstrabladet,metroxpress,tv2nyhederne,MetroUK&limit=100&fields=id,created_time,description,from,link,message,shares,reactions.limit(0).summary(1),comments.limit(0).summary(1)&access_token=EAACg2C47ZCakBAOguFnp2nvM7t2RqCu2PnaobPpt1lwDTZAeGtWTqUKnKrnvWzAjGhN9asZAAASWvDvDi3eJCV8pHGfbposb4oFT5kK492aLx22PQXcB7PbW6ZCCOXeHiRVRwCD5FKn5gSxBa0XT


def extend_token(access_token):
    
    graph = facebook.GraphAPI(access_token)
    extended_token = graph.extend_access_token(app_id, app_secret)
    
    return extended_token
    

class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)
    

########### Get posts #############################################

def get_posts(pages=pages,fields=post_fields,post_limit=post_limit):
    
    url_tail = 'posts?ids=' + ','.join(pages) + '&limit=' + str(post_limit) + '&fields=' + ','.join(fields)    
    url = graph_url + url_tail + '&access_token=' + access_token
#    r = requests.get(url,timeout=15) #v2.8 limit on batch requests is 50. For v2.7 it is 25.
    r = requests.post(url+'&method=GET',timeout=15) #post requests with a GET method is adviced by the API documentation, when making large calls
    posts_dic = r.json()
#    posts_dic = graph.get_object(url_tail) #graph.get_object only works up to 14 pages.
    
    timestamp = time.time()
    for page in posts_dic:
        posts_dic[page]['timestamp'] = int(timestamp)
    
    return posts_dic


def get_posts_divide(pages=pages,fields=post_fields,post_limit=post_limit,page_limit=page_limit):
    
    posts_dic = {}
    pages_subsets = [pages[i:i+page_limit] for i in xrange(0, len(pages), page_limit)]
    
    for pages_subset in pages_subsets:
        n = 0
        while True:
            n += 1
            try:
                posts_dic_subset = get_posts(pages_subset,fields,post_limit)
                if pages_subset[0] in posts_dic_subset:
                    posts_dic.update( posts_dic_subset )
                    break
            except:
                print 'Exception', n
                if n > 3:
                    break
        
    return posts_dic


def save_post(post,timestamp,page):
    
    filename = '%s_ID=%s.p' %(post['created_time'][:-5].replace('-','').replace(':',''),post['id'])
                    
    #If the post file exists
    if os.path.isfile(filename): 
        post_dic = pickle.load( open(filename,'rb') )
        try:
            post_dic['comments'] = np.append(post_dic['comments'], post['comments']['summary']['total_count'])
        except:
            post_dic['comments'] = np.append(post_dic['comments'], 0)
        try:
            post_dic['reactions'] = np.append(post_dic['reactions'], post['reactions']['summary']['total_count'])
        except:
            post_dic['reactions'] = np.append(post_dic['reactions'], 0)
        try:
            post_dic['shares'] = np.append(post_dic['shares'], post['shares']['count'])
        except:
            post_dic['shares'] = np.append(post_dic['shares'], 0)
        post_dic['timestamps'] = np.append(post_dic['timestamps'], timestamp )
    
    #If the post file does not exist
    else: 
        post_dic = post
        try:
            time_string = post['created_time']
            timestamp_created = int( nm.time_to_epoch(time_string,"%Y-%m-%dT%H:%M:%S+0000",'UTC') )
            post_dic['created_time'] = {'time_string':time_string, 'timestamp':timestamp_created}
        except:
            post_dic['created_time'] = {'time_string':False, 'timestamp':False}
        try:
            post_dic['comments'] = np.array([ post['comments']['summary']['total_count'] ])
        except:
            post_dic['comments'] = np.array([ 0 ])
        try:
            post_dic['reactions'] = np.array([ post['reactions']['summary']['total_count'] ])
        except:
            post_dic['reactions'] = np.array([ 0 ])
        try:
            post_dic['shares'] = np.array([ post['shares']['count'] ])
        except:
            post_dic['shares'] = np.array([ 0 ])
        post_dic['timestamps'] = np.array([ timestamp ])
    
    #Save post_dic to file
    pickle.dump(post_dic, open(filename, 'wb') )
    
    
def save_posts(posts_dic):
    
    with cd(data_directory):
        
        #Construct directories for potentially new pages in posts_dic
        posts_pages = posts_dic.keys()
        old_pages = next(os.walk('.'))[1]
        new_pages = set(posts_pages) - set(old_pages)
        for page in new_pages:
            os.mkdir(page)
        
        #Iterate the pages in posts_dic
        for page in posts_pages:
            with cd(page):
                posts = posts_dic[page]['data']
                
                #Iterate posts of page: build files for new posts and add to files for old posts
                for post in posts:
                    save_post(post,posts_dic[page]['timestamp'],page)
                    
                        
################ Main #############################
                        
def update(pages=pages,fields=post_fields,post_limit=post_limit,page_limit=page_limit):
    
    posts_dic = get_posts_divide(pages,fields,post_limit,page_limit)
    save_posts(posts_dic)
    
    #Save update performance in the file "update_stats.p"
    timestamp = int(time.time())
    success_pages = posts_dic.keys()
    update_stats = pickle.load(open('update_stats.p','rb'))
    for page in pages:
        if page not in update_stats:
            update_stats[page] = {'timestamp':[], 'success':[]}
        update_stats[page]['timestamp'] = timestamp
        if page in success_pages:
            update_stats[page]['success'] = 1
        else:
            update_stats[page]['success'] = 0
    pickle.dump(update_stats,open('update_stats.p','wb'))
    
    #Print failed pages
    failed_pages = set(pages) - set(success_pages)
    if len(failed_pages) > 0:
        print 'Failed page updates:'
        for page in failed_pages:
            print '   %s'%page
    else:
        print 'Update complete'


def update_continuously(pages=pages,fields=post_fields,post_limit=post_limit,page_limit=page_limit,update_interval_minimum=30):
    
    last_update_time = 0
    while True:
        loop_initiation_time = time.time()
        time_passed = loop_initiation_time  - last_update_time
        time_sleep = update_interval_minimum - time_passed
        print '\nTime passed: %d \nSleeping in seconds: %d\n'%(time_passed,max(0,time_sleep))
        if time_sleep > 0:
            time.sleep(time_sleep)
        last_update_time = time.time()
        update(pages,fields,post_limit,page_limit)

        