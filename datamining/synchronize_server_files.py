# -*- coding: utf-8 -*-
"""
Created on Mon Jan  2 11:39:19 2017

@author: amollgaard
"""

import subprocess
import time
import paramiko

####################################################

#cmd = ['rsync', '-azvv', '-e', 'ssh', '/home/amollgaard/Pictures/', \
#    'asparagus@178.62.206.144:/home/asparagus/testfolder']
#cmd = ['rsync', '-azvv', '-e', 'ssh', \
#    'asparagus@178.62.206.144:/home/asparagus/testfolder/', \
#    '/home/amollgaard/testfolder']

def rsync_posts():
    
    cmd = ['rsync', '-azvv', '-e', 'ssh', \
        'asparagus@178.62.206.144:/home/asparagus/Data/FacebookMining/posts/', \
        '/home/amollgaard/Data/FacebookMining/posts']
    
    before = time.time()
    p1 = subprocess.Popen(cmd).wait()
    after = time.time()
    
    print 'Process exit status: %s'%p1
    print 'Seconds spent: %d'%(after - before)
    
    return p1


def cleanup_posts():
    
    # Lines for possible later use
#    rsa_private_key_path = '/home/amollgaard/.ssh/id_rsa'
#    rsa_public_key_path = '/home/amollgaard/.ssh/id_rsa.pub'
#    known_hosts_path = '/home/amollgaard/.ssh/known_hosts'
#    private_key = paramiko.RSAKey.from_private_key_file(rsa_private_key_path)
#    client.load_system_host_keys()
#    client.load_host_keys(known_hosts_path)
#    client.get_host_keys().add('178.62.206.144', 'ssh-rsa', private_key)
    
    cmd = 'python /home/asparagus/Projects/FacebookMining/post_cleanup.py'
    
    paramiko.util.log_to_file('ssh.log')
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('178.62.206.144', username='asparagus')
    stdin, stdout, stderr = client.exec_command(cmd)
    for line in stdout:
        print('... ' + line.strip('\n'))
    client.close()
    


def rsync_cleanup_posts():
    
    for i in range(1,4):
        print '# Attempt %d of 3'%i
        p_rsync = rsync_posts()
        if p_rsync == 0:
            print 'Succesful synchronization'
            cleanup_posts()
            break
        else:
            print 'Failed synchronization'
        