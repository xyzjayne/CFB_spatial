import numpy as np
import pandas as pd


class table_container(object):
	'''
	Defines an object that contains post-mode choice trip tables.
	'''
	def __init__(self, mc_obj):
		self.purpose_calculated = {purpose: False for purpose in ['HBW','HBO','NHB', 'HBSc1','HBSc2','HBSc3']}
		self.model = mc_obj
		self.container = dict.fromkeys(['HBW','HBO','NHB', 'HBSc1','HBSc2','HBSc3'])
		for purpose in self.container:
			self.container[purpose] = {'0_PK':{},'1_PK':{},'0_OP':{},'1_OP':{}}
		self.modes = set()
		
	def store_table(self,purpose):
		self.container[purpose] = self.model.trips_by_mode
		self.modes = self.modes | set(self.model.param['mode'])
		self.purpose_calculated[purpose] = True
	
	def get_table(self,purpose):
		if purpose in self.container.keys() and self.purpose_calculated[purpose] == True:
			return self.container[purpose]
		else:
			return None
	
	def aggregate_by_mode_segment(self, mode, pv):
		trip_sum = np.zeros((2730,2730))
		for purpose in ['HBW','HBO', 'NHB', 'HBSc1', 'HBSc2', 'HBSc3']:
			try:
				trip_sum += self.container[purpose][pv][mode]
			except: pass
			
		return trip_sum

