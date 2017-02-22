# -*- coding: utf-8 -*-
"""
Created on Tue Jan  3 10:21:46 2017

@author: amollgaard
"""

import os
import time

#########################################################################

def cleanup(directory='/home/asparagus/Data/FacebookMining/posts',delta_old=172800):
    
    print '\nRemoving files that are older than %d seconds'%delta_old 
    now = time.time()
    
    removed = []
    for root, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            path = '%s/%s'%(root,filename)
            time_modified = os.path.getmtime(path)
            modification_age = now - time_modified
            print '\n# Path: %s/%s'%(root,filename)
            print '# Modification age: %d'%modification_age
            if modification_age > delta_old:
                print '# Removing'
                os.remove(path)
                removed.append(path)
    
    print '\nRemoved %d files\n'%len(removed)


if __name__ == '__main__':
    cleanup()