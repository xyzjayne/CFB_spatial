# coding: utf-8
import numpy as np
import pandas as pd
import openmatrix as omx
import matplotlib.pyplot as plt
import os, glob
import warnings
import tables
import config
import time
from IPython.display import display
from openpyxl import load_workbook
from mc_util import *
from mc_table_container import table_container
warnings.simplefilter('ignore', tables.NaturalNameWarning)

class Mode_Choice(object):
	'''Mode choice object that computes mode probabilities given inputs.'''
	def __init__(self,config, run_now = False, all_purposes = False):
		
		self.config = config
		self.cost_per_mile = config.cost_per_mile
		self.purpose = config.purpose
		self.param_file = config.param_file
		self.table_container = table_container(self)
		self.peak_veh = ['0_PK','1_PK','0_OP','1_OP'] # vehicle ownership + peak: market segments used in trip tables
	
		self.drive_modes = ['DA','SR2','SR3+','SR2+']
		self.DAT_modes = ['DAT_CR','DAT_RT','DAT_LB','DAT_B']
		self.WAT_modes = ['WAT','WAT_CR','WAT_RT','WAT_LB','WAT_B']
		self.active_modes = ['Walk','Bike']
		self.smart_mobility_modes = ['SM_RA','SM_SH']
		self.start_time = time.time()
		
		if run_now == True:
			self.load_input()
			self.run_model(all_purposes)
		
	def run_model(self, all_purposes = False):
		if all_purposes:
			print('Running for all purposes...')
			for purpose in ['HBW','HBO','NHB', 'HBSc1','HBSc2','HBSc3']:
				print(f'Mode choice for {purpose} started.')
				self.run_for_purpose(purpose)
				write_mode_share_to_excel(self,purpose)
		else:
			print(f'Mode choice for {self.purpose} started.')
			self.run_for_purpose(purpose = None)
	
	def run_for_purpose(self, purpose = None):
		if purpose == None:
			purpose = self.purpose
		self.read_param(purpose)
		self.calculate_trips_by_mode()
		self.table_container.store_table(purpose)
	
	def load_input(self):
		self.read_taz_data()
		self.read_skims()
		self.read_trip_table()
		self.generate_zonal_var()
	
	def read_taz_data(self):
		taz = pd.read_csv(self.config.taz_file)
		land_use = pd.read_csv(self.config.land_use_file)
		self.taz_lu = taz.merge(land_use,on='ID')
		self.taz_parking = pd.read_csv(self.config.taz_parking_file).fillna(0)
		self.taz_zonal = pd.read_csv(self.config.taz_zonal_file).sort_values('TAZ_ID')
		print(f'✓ TAZ / land use / parking / zonal variables read. Time elapsed: {time.time()-self.start_time:.2f} seconds')

	def read_skims(self):
		self.skim_list = []
		for skim_fn in self.config.skim_list:
			exec('self.' + skim_fn +
				 ' = store_omx_as_dict(self.config.'
				 +skim_fn+ '_file)')	
			self.skim_list.append(skim_fn)
		
		print(f'✓ skims read. Time elapsed: {time.time()-self.start_time:.2f} seconds')
		
		self.skim_PK_dict = {'drive':self.drive_skim_PK,'DAT_B':self.DAT_B_skim_PK,'DAT_CR':self.DAT_CR_skim_PK,'DAT_RT':self.DAT_RT_skim_PK,'DAT_LB':self.DAT_LB_skim_PK,'WAT':self.WAT_skim_PK,'Walk':self.walk_skim,'Bike':self.bike_skim,'SM_RA':self.drive_skim_PK,'SM_SH':self.drive_skim_PK}
		
		self.skim_OP_dict = {'drive':self.drive_skim_OP,'DAT_B':self.DAT_B_skim_OP,'DAT_CR':self.DAT_CR_skim_OP,'DAT_RT':self.DAT_RT_skim_OP,'DAT_LB':self.DAT_LB_skim_OP,'WAT':self.WAT_skim_OP,'Walk':self.walk_skim,'Bike':self.bike_skim,'SM_RA':self.drive_skim_OP,'SM_SH':self.drive_skim_OP}
		
	def read_trip_table(self):
		self.pre_MC_trip_table = store_omx_as_dict(self.config.pre_MC_trip_file)
		print(f'✓ trip table read. Time elapsed: {time.time()-self.start_time:.2f} seconds')
		
	def generate_zonal_var(self):
	# this generates parking, PEV, pop density, emp density, hh size, vpw, wacc, wegr tables.
		self.parking = expand_attr(self.taz_parking['Daily Parking Cost'])/2
		self.AccPEV = expand_prod(self.taz_zonal['Acc_PEV'].fillna(0.001))
		self.EgrPEV = expand_attr(self.taz_zonal['Egr_PEV'].fillna(0.001))
		self.PopD = np.sqrt(expand_prod( self.taz_zonal['Tot_Pop']/self.taz_zonal['Area'] ) )
		self.EmpD = np.sqrt(expand_attr( self.taz_zonal['Tot_Emp']/self.taz_zonal['Area'] ) )
		self.HHSize = expand_prod((self.taz_zonal['HH_Pop']/self.taz_zonal['HH']).fillna(0))
		self.VPW = expand_prod( self.taz_zonal['VehiclesPerWorker'].fillna(
		self.taz_zonal['VehiclesPerWorker'].mean()))
		self.wacc_PK = expand_prod( self.taz_zonal['AM_wacc_fact'])
		self.wacc_OP = expand_prod( self.taz_zonal['MD_wacc_fact'])
		self.wegr_PK = expand_attr( self.taz_zonal['AM_wacc_fact'])
		self.wegr_OP = expand_attr( self.taz_zonal['MD_wacc_fact'])
		self.Hwy_Prod_Term = expand_prod( self.taz_zonal['Hwy Prod Term Time']) 
		print(f'✓ zonal variable tables generated. Time elapsed: {time.time()-self.start_time:.2f} seconds')
		
	def read_param(self, purpose = None):

		if purpose:
			param = pd.read_excel(self.param_file,sheet_name = purpose).fillna(0)
		else:	
			purpose = self.config.purpose
			param = pd.read_excel(self.param_file,sheet_name=self.config.purpose).fillna(0) 
		
		trip_tables = [purpose+ i for i in ['_PK_0Auto','_PK_wAuto','_OP_0Auto','_OP_wAuto']]

		self.trip_tables_dict = dict(zip(self.peak_veh,trip_tables))
		
		coef_col = ['mode','nest','nest_coefficient'] +list(param.filter(regex='ASC'))
		self.coef_table = param[coef_col]
		self.var_list = param.columns.drop(coef_col)
		self.param = param
		self.AO_dict = self.config.AO_dict[purpose]
		print(f'✓ Parameter table for {purpose} generated. Time elapsed: {time.time()-self.start_time:.2f} seconds')
		
	def var_by_mode(self,pv,var,mode):
		drive_modes = self.drive_modes
		DAT_modes = self.DAT_modes
		WAT_modes = self.WAT_modes
		active_modes = self.active_modes
		smart_mobility_modes = self.smart_mobility_modes
		
		table = np.zeros((2730,2730))
		
		peak = pv[2:]
		if peak == 'PK':
			skim_dict = self.skim_PK_dict
		elif peak == 'OP':
			skim_dict = self.skim_OP_dict
		else:
			print('peak input incorrect!')

		if var == 'IVTT':
			if mode in drive_modes:
				skim = skim_dict['drive']
				table = skim['CongTime']
			elif mode in DAT_modes:
				skim = skim_dict[mode]
				table = skim['Total_IVTT']
				table[np.where(table==0)]=+1e4 # 0 in DAT skims indicates no path found
			elif mode in WAT_modes:
				skim = skim_dict['WAT']
				table = skim['Total_IVTT']
				table[np.where(table==0)]=+1e4 # 0 in DAT skims indicates no path found
			elif mode in active_modes:
				pass
			elif mode in smart_mobility_modes:
				skim = skim_dict['drive']
				if mode == 'SM_RA':
					table = skim['CongTime']
				elif mode == 'SM_SH':
					table = skim['CongTime'] * self.config.SM_SH_IVTT_factor
			else: print(mode,var,'not found in var_by_mode module')
			
		elif var == 'OVTT':
			if mode in drive_modes:
				skim = skim_dict['drive']
				table = skim['TerminalTimes']
			elif mode in DAT_modes: 
				skim = skim_dict[mode] 
				table = skim['Total_OVTT'] + self.Hwy_Prod_Term # add Hwy Prod Term Time
			elif mode in WAT_modes:
				skim = skim_dict['WAT']
				table = skim['Total_OVTT']
			elif mode in active_modes: # walk time, bike time from skims.
				skim = skim_dict[mode]
				table = skim[mode+'Time'][:2730,:2730]
			elif mode in smart_mobility_modes:
				skim = skim_dict['drive']
				if mode == 'SM_RA':
					table = self.config.SM_RA_OVTT_table
				elif mode == 'SM_SH':
					table = self.config.SM_RA_OVTT_table * self.config.SM_SH_OVTT_factor
				#table = skim['TerminalTimes']				
			else: print(mode,var,'not found in var_by_mode module')

		elif var == 'Cost':
			if mode in drive_modes:
				skim = skim_dict['drive']
				toll = skim['Auto_Toll (Skim)'] 
				toll[np.where(abs(toll)>1e6)] = 0 # eliminate same-zone large value issues
				
				length = skim['Length (Skim)']
				AO = self.AO_dict[mode]
				
				table = (toll/AO + length * self.cost_per_mile)

			elif mode in DAT_modes: 
				skim = skim_dict[mode]
				table = skim['Total_Cost']
			elif mode in WAT_modes:
				skim = skim_dict['WAT']
				table = skim['Total_Cost']
			elif mode in active_modes:
				pass
			elif mode in smart_mobility_modes:
				skim = skim_dict['drive']
				toll = skim['Auto_Toll (Skim)']
				toll[np.where(abs(toll)>1e6)] = 0 # eliminate same-zone large value issues
				
				length = skim['Length (Skim)']
				time = skim['CongTime']
				
				total_cost = self.config.SM_base_fare + self.config.SM_distance_coef * length + self.config.SM_time_coef * time + toll
				
				if mode == 'SM_RA':
					table = total_cost
				elif mode == 'SM_SH':
					table = total_cost / self.config.SM_SH_cost_factor
			
			else: print(mode,var,'not found in var_by_mode module')    
		
		elif var == 'Parking': 
			if mode in drive_modes:
				table = self.parking
			elif mode in DAT_modes + WAT_modes + active_modes + smart_mobility_modes:
				pass
			else: print(mode,var,'not found in var_by_mode module')
		
		elif var == 'length':
			if mode in active_modes:
				skim = skim_dict[mode]
				table = skim['Length (Skim)'][:2730,:2730]
			elif mode in drive_modes + DAT_modes + WAT_modes + smart_mobility_modes:
				pass
			else: print(mode,var,'not found in var_by_mode module')
		
		elif var == 'Sqrlength':
			if mode in active_modes:
				skim = skim_dict[mode]
				table = np.sqrt(skim['Length (Skim)'][:2730,:2730])
			elif mode in drive_modes + DAT_modes + WAT_modes + smart_mobility_modes:
				pass
			else: print(mode,var,'not found in var_by_mode module')        
		
		elif var == 'AccPEV':
			if mode in active_modes + WAT_modes:
				table = self.AccPEV
			elif mode in drive_modes + DAT_modes + smart_mobility_modes:
				pass
			else: print(mode,var,'not found in var_by_mode module')    
					
		elif var == 'EgrPEV':
			if mode in active_modes + WAT_modes + DAT_modes:
				table = self.EgrPEV
			elif mode in drive_modes + smart_mobility_modes:
				pass
			else: print(mode,var,'not found in var_by_mode module')           
				
		elif var == 'PopD': # sqrt population density production TAZ
			if mode in active_modes + WAT_modes:
				table = self.PopD
			elif mode in drive_modes + DAT_modes + smart_mobility_modes:
				pass
			else: print(mode,var,'not found in var_by_mode module')  

		elif var == 'EmpD': # sqrt employment density attraction TAZ
			if mode in active_modes + DAT_modes:
				table = self.EmpD
			elif mode in drive_modes + WAT_modes + smart_mobility_modes:
				pass
			else: print(mode,var,'not found in var_by_mode module')  
			
		elif var == 'HHSize':
			if mode in drive_modes:
				table = self.HHSize
			elif mode in active_modes + DAT_modes + WAT_modes + smart_mobility_modes:
				pass
			else: print(mode,var,'not found in var_by_mode module')  
		
		elif var == 'VPW':
			if mode in drive_modes:
				table = self.VPW
			elif mode in active_modes + DAT_modes + WAT_modes + smart_mobility_modes:
				pass
			else: print(mode,var,'not found in var_by_mode module')  
			
		elif var == 'wacc_fact':
			if mode in WAT_modes:
				table = self.wacc_PK * (peak == 'PK') + self.wacc_OP * (peak == 'OP')
			elif mode in drive_modes + active_modes + DAT_modes + smart_mobility_modes:
				pass
			else: print(mode,var, 'not found in var_by_mode module')
			
		elif var == 'wegr_fact':
			if mode in WAT_modes + DAT_modes:
				table = self.wegr_PK * (peak == 'PK') + self.wegr_OP * (peak == 'OP')
			elif mode in drive_modes + active_modes + smart_mobility_modes:
				pass
			else: print(mode,var, 'not found in var_by_mode module')
		
		else:
			print(mode, var, 'not implemented in var_by_mode module')
		
		# dimension check
		if table.shape!=(2730,2730):
			try: table = table[:2730,:2730]
			except: raise
		
		return table			
	
	def mode_probability_tables(self,pv,modes):
		var_values = {}
		for mode in modes:
			var_values[mode]={}
			for var in self.var_list:
				var_values[mode][var] = self.var_by_mode(pv,var,mode)

		# compute utility for each mode.
		mode_utils = {}
		for mode in modes: 
			util = np.zeros((2730,2730))
			util += self.param[self.param['mode']==mode]['ASC_'+pv].values
			for var in self.var_list:
				# coefficient values
				coeff = self.param[self.param['mode']==mode][var].values
				util += coeff * var_values[mode][var]
			mode_utils[mode] = np.exp(util)
			
		# compute logsums
		nests = self.param[self.param['mode'].isin(modes)].nest.unique()
		nest_logsums= dict(zip(nests,[np.zeros((2730,2730))]*len(nests)))
		
		for mode in modes:
			nest = dict(zip(self.param['mode'],self.param['nest']))[mode]
			nest_logsum = nest_logsums[nest]
			nest_logsums[nest] = nest_logsum + mode_utils[mode]
		
		zero_logsum = {}

		for nest in nests:
			zero_logsum[nest] = (nest_logsums[nest]==0) # apply the mask later in probability calculation
			(nest_logsums[nest])[~zero_logsum[nest]] = np.log((nest_logsums[nest])[~zero_logsum[nest]]) # if nest logsum is not zero, calculate log.
		
		# from logsums to mode probability
		nest_thetas = dict(zip(self.param['nest'],self.param['nest_coefficient']))
		mode_probs = {}
		
		all_nest_sum = np.zeros((2730,2730))
		# if a nest has entries with zero logsum, it will be excluded.
		for nest in nests:
			all_nest_sum[~zero_logsum[nest]] += np.exp(nest_thetas[nest] * nest_logsums[nest][~zero_logsum[nest]])
		
		for mode in modes:
			mode_probs[mode]={}
			
			nest = dict(zip(self.param['mode'],self.param['nest']))[mode]
			theta = nest_thetas[nest]
			modes_in_nest = self.param[self.param['nest']==nest]['mode']

			prob_nest = np.zeros((2730,2730))
			prob_nest[~zero_logsum[nest]] = np.exp(theta * nest_logsums[nest][~zero_logsum[nest]]) / all_nest_sum[~zero_logsum[nest]]
			
			prob_mode_in_nest = np.zeros((2730,2730))
			prob_mode_in_nest[~zero_logsum[nest]] = (mode_utils[mode][~zero_logsum[nest]] / 
			np.exp((nest_logsums[nest]))[~zero_logsum[nest]])
				
			prob = prob_nest * prob_mode_in_nest
			mode_probs[mode] = prob
		
		return mode_probs, nest_logsums, mode_utils

	def calculate_trips_by_mode(self):
		modes = self.param['mode']

		self._0_PK, self._1_PK, self._0_OP, self._1_OP = ({},{},{},{})
		
		self.trips_by_mode = dict(zip(self.peak_veh, [self._0_PK, self._1_PK, self._0_OP, self._1_OP]))
		
		for pv in self.peak_veh:
			mode_probs = self.mode_probability_tables(pv,modes)[0]
			print(f'✓ Trips for {pv} calculated. Time elapsed: {time.time()-self.start_time:.2f} seconds')
			for mode in modes:
				trip_table = self.pre_MC_trip_table[self.trip_tables_dict[pv]][:2730,:2730]
				trips_MC = trip_table * mode_probs[mode]
				self.trips_by_mode[pv][mode] = trips_MC
				