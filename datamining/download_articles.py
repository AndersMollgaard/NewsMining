# -*- coding: utf-8 -*-
"""
Created on Thu Jan  5 08:53:49 2017

@author: amollgaard
"""

import pickle
from newspaper import Article, Config
from ..lib import newsmine as nm
import os
import testmining

############ Variables ##########################################

url1 = 'http://www.b.dk/nationalt/stormraadet-giver-haab-for-ramte-danskere\
        -saadan-faar-du-erstatning'
articles_path = '/home/amollgaard/Data/FacebookMining/articles'

############ Helping functions ###################################

def get_article_downloads():
    with open('/home/amollgaard/Data/FacebookMining/article_downloads.p','rb') as f:
        article_downloads = pickle.load(f)
    return article_downloads


def update_article_downloads(status,page,filename,article_downloads):
    if page not in article_downloads['download_success']:
        article_downloads['download_success'][page] = []
        article_downloads['download_failure'][page] = []
    article_downloads[status][page].append(filename)


def save_article_downloads(article_downloads):
    with open('/home/amollgaard/Data/FacebookMining/article_downloads.p','wb') as f:
        pickle.dump(article_downloads,f)

############# Download #####################################

def download_article(url=url1):
    
    config = Config()
    config.memoize_articles = False
    config.fetch_images = False
    article = Article(url=url,config=config)
    article.download()
    try:
        article.parse()
        article_dic = {'url' : url, 'authors' : article.authors,
                   'title' : article.title, 'text' : article.text}
    except:
        article_dic = {}
    
    return article, article_dic
    

def save_article(article_dic,page,filename,article_downloads):
    
    # Create folder if it does not exist
    article_folder = '%s/%s'%(articles_path,page)
    if not os.path.exists(article_folder):
        os.makedirs(article_folder)
    
    # Save article_dic using pickle
    path = '%s/%s'%(article_folder,filename)
    with open(path,'wb') as f:
        pickle.dump(article_dic,f)
    
    # Add the filename to article_downloads
    update_article_downloads('download_success',page,filename,article_downloads)


def save_articles(pages=testmining.pages):
    
    article_downloads = get_article_downloads()
    skip_dic = article_downloads['download_success']
    for page,path,post in nm.pagesposts_iter(pages,filters={},skip_dic=skip_dic):
        filename = path.split('/')[-1]
        if 'link' in post:
            url = post['link']
            print '\nAttempting to download: %s'%url
            article,article_dic = download_article(url)
            if article_dic:
                print 'Success'
                save_article(article_dic,page,filename,article_downloads)
            else:
                print 'Failure'
                update_article_downloads('download_failure',page,filename,article_downloads)
        else:
            print '\nMissing link for file: %s'%filename
            update_article_downloads('download_failure',page,filename,article_downloads)
    save_article_downloads(article_downloads)
    
    
    
    
    
    