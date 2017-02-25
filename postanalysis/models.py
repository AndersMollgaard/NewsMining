# -*- coding: utf-8 -*-
"""
Created on Tue Jan 10 09:28:26 2017

@author: amollgaard
"""

import numpy as np
from ..lib import newsmine as nm

########### Model X #########################

class Model1():
    
    def __init__(self, response_time, response_function):
        self.response_time = response_time
        self.response_function = response_function
    
    def fit(self, t, x, fan_count):
        self.x = x
        self.response_fraction = np.interp(t[-1:], self.response_time, self.response_function)[0]
        self.x_final = self.x[-1] / self.response_fraction
        self.infectiousness = self.x_final / fan_count
    
    def predict_final(self):
        return self.x_final, self.infectiousness
    
    def predict(self,t_predict):
        response_fraction_predict = np.interp(t_predict, self.response_time, self.response_function)
        x_predict = response_fraction_predict * self.x_final
        return x_predict


############# Seismic type models ##########################

class SeismicSimple():
    
    def __init__(self, response_time, response_function,followers_avg):
        self.response_time = response_time
        self.response_function = response_function
        self.followers_avg = followers_avg
    
    
    def fit(self, t, x, fan_count, shares):
        t_halfway = np.concatenate((t[:1], nm.halfway(t)))
        response_input = t[-1] - t_halfway
        response_array = np.interp(response_input, self.response_time, self.response_function)
        shares_new = nm.diffx(shares)
        degree_new = self.followers_avg * shares_new
        degree_new = np.concatenate((np.array([fan_count]), degree_new))
        self.degree_sum = fan_count + self.followers_avg * shares[-1]
        self.degree_sum_effective = np.dot(degree_new, response_array)
        self.infectiousness = x[-1] / self.degree_sum_effective
        self.x_last = x[-1]
    
    def predict_final(self):
        infection_avg = self.followers_avg * self.infectiousness
        if infection_avg > 1:
            return np.inf, self.infectiousness
        else:
            degree_potential = self.degree_sum - self.degree_sum_effective
            x_predict = self.x_last + self.infectiousness * degree_potential / (1. - infection_avg)
            return x_predict, self.infectiousness