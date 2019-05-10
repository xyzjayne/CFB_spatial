# coding: utf-8
import numpy as np
import pandas as pd
import openmatrix as omx
import mode_choice
import mc_util
from shutil import copyfile
import config
import copy
import re
import os
from mc_table_container import table_container
from config import data_path, taz_path, misc_path


scenario_space = {
'Clean Vehicles': 'Reduce driving cost (by default $0.05 / mile)',
'Land Use': 'Shift a certain amount of population growth to growth-intensive TAZs (by default 50%).',
'Transit Improvements': 'Decrease transit travel time by 30% for TAZs impacted by Go Boston transit improvement projects.',
'Active Transportation': 'Decrease bike trip time and distance for neighborhoods impacted by Go Boston bike improvement projects; improve citywide Pedestrian Environment Variables by 10%.',
'CAV':'10% of car-owning households convert to zero-car households, reduced travel time, driving cost and parking cost.',
'Smart Mobility':'Use model parameters calibrated against target Smart Mobility shares, convert car-owning households based on TNC usage data.',
'Congestion Charge':'$5 toll charge for auto trips entering central Boston.',
'TDM': 'Reduce home-based work transit fare for trips entering central Boston by $1; reduce the number of HBW trips in these areas by 0.35%.'
}

switches = config.scenario_switches

def implement_scenarios(mc_obj):
	if sum(list(switches.values())) == 0: # no scenario is turned on
		print('No scenario is enabled. Check config.')
	else:
		if switches['clean_vehicle']:
			print(f'"Clean Vehicle" enabled: {scenario_space["Clean Vehicles"]}')
			decrease_driving_cost(mc_obj)

		if switches['growth_shift']:
			print(f'"Land Use" enabled: {scenario_space["Land Use"]}')
			land_use_growth_shift(mc_obj)
			
		if switches['transit_improvements']:
			print(f'"Transit Improvements" enabled: {scenario_space["Transit Improvements"]}')
			transit_modify_skim(mc_obj)
			
		if switches['active_transportation_improvements']:
			print(f'"Active Transportation" enabled: {scenario_space["Active Transportation"]}')
			active_transportation_modify_skim(mc_obj)
			active_transportation_decrease_PEV(mc_obj)
			
		if switches['congestion_charge']:
			print(f'"Congestion Charge" enabled: {scenario_space["Congestion Charge"]}')
			congestion_charge(mc_obj)
			
		if switches['smart_mobility']:
			print(f'"Smart Mobility" enabled: {scenario_space["Smart Mobility"]}')
			smart_mobility_shift_HH(mc_obj)
			if switches['smart_mobility_management_policy']:
				mc_obj.param_file = config.SM_calib_param_mngpol_file
			else:
				mc_obj.param_file = config.SM_calib_param_file
		
		if switches['CAV'] == False and switches['TDM'] == False:
			mc_obj.run_model(all_purposes = True)
			print('Scenario run is finished. You may now call methods in mc_util to produce output summaries.')
		
		elif switches['TDM'] == True and switches['CAV'] == False:
			print(f'"TDM" enabled: {scenario_space["TDM"]}')
			mc_obj.run_model(all_purposes = True)
			TDM_run(mc_obj)
			print('TDM run is finished. You may now call methods in mc_util to produce output summaries.')										
		
		elif switches['CAV'] == True and switches['TDM'] == False:
			print(f'"CAV" enabled: {scenario_space["CAV"]}')
			param_out, trip_table_conventional, trip_table_CAV = CAV_input_generator(mc_obj)
			mc_obj.param_file = param_out
			mc1 = mode_choice.Mode_Choice(config, run_now = False)
			mc2 = mode_choice.Mode_Choice(config, run_now = False)
			# mc1 = copy.deepcopy(mc_obj) gives "cannot pickle" error
			# mc2 = copy.deepcopy(mc_obj)
			
			mc1.load_input()
			mc2.load_input()
			
			mc1.pre_MC_trip_table = trip_table_conventional
			mc2.pre_MC_trip_table = trip_table_CAV
			mc2.param_file = param_out
            
			print('Running CAV scenario for families with no vehicle or no access to CAV...')
			mc1.run_model(all_purposes = True)
			print('Running CAV scenario for families with access to CAV...')
			mc2.run_model(all_purposes = True)
			
			# combine post mode choice trip tables
			combined_table = table_container(mc_obj)
			for purpose in ['HBW','HBO','NHB', 'HBSc1','HBSc2','HBSc3']:
				for peak in ['PK','OP']:
					for veh_own in ['0','1']:
						for mode in mc_obj.table_container.get_table(purpose)[f'{veh_own}_{peak}']:
							combined_table.get_table(purpose)[f'{veh_own}_{peak}'][mode] = mc1.table_container.get_table(purpose)[f'{veh_own}_{peak}'][mode] + mc2.table_container.get_table(purpose)[f'{veh_own}_{peak}'][mode]
			
			mc_obj.table_container = combined_table
			print('Scenario run is finished. You may now call methods to mc_util to produce output summaries.')
			
		elif switches['CAV'] and switches['TDM']:
			print(f'"TDM" enabled: {scenario_space["TDM"]}')
			print(f'"CAV" enabled: {scenario_space["CAV"]}')
			
			param_out, trip_table_conventional, trip_table_CAV = CAV_input_generator(mc_obj)
			mc_obj.param_file = param_out
			mc1 = mode_choice.Mode_Choice(config, run_all = False)
			mc2 = mode_choice.Mode_Choice(config, run_all = False)
			# mc1 = copy.deepcopy(mc_obj)
			# mc2 = copy.deepcopy(mc_obj)
			
			mc1.load_input()
			mc2.load_input()
			
			mc1.pre_MC_trip_table = trip_table_conventional
			mc2.pre_MC_trip_table = trip_table_CAV
			mc2.param_file = param_out
			
			print('Running CAV scenario for families with no vehicle or no access to CAV...')
			mc1.run_model(all_purposes = True)
			print('Running CAV scenario for families with access to CAV...')
			mc2.run_model(all_purposes = True)
			
            # TDM run on both mode choice objects
			TDM_modify_skim_trip_table(mc1)
			TDM_run(mc1)
			TDM_modify_skim_trip_table(mc2)
			TDM_run(mc2)
                        
            
			# combine post mode choice trip tables
			combined_table = table_container(mc_obj)
			for purpose in ['HBW','HBO','NHB', 'HBSc1','HBSc2','HBSc3']:
				for peak in ['PK','OP']:
					for veh_own in ['0','1']:
						for mode in mc_obj.table_container.get_table(purpose)[f'{veh_own}_{peak}']:
							combined_table[purpose][f'{veh_own}_{peak}'][mode] = mc1.table_container.get_table(purpose)[f'{veh_own}_{peak}'][mode] + mc2.table_container.get_table(purpose)[f'{veh_own}_{peak}'][mode]
			
			mc_obj.table_container = combined_table		
			
			print('TDM run is finished. You may now call methods in mc_util to produce output summaries.')			
			
		
		
			
def show_scenarios():
	for sc in scenario_space:
		print(sc+':')
		print(scenario_space[sc])
		print('\n')

def decrease_driving_cost(mc_obj, amount = 0.05):
	mc_obj.cost_per_mile -= amount

def land_use_growth_shift(mc_obj, factor = 0.5):
	modified_2040 = misc_path + "2040_growth_shift_trip_tables.omx"
	if os.path.isfile(modified_2040):
		mc_obj.pre_MC_trip_table = mc_util.store_omx_as_dict(modified_2040)
	else:
		pre_MC_trip_file_2016 = misc_path + "pre_MC_trip_6_purposes.omx"
		pre_MC_trip_file_2040 = misc_path + "pre_MC_trip_6_purposes.omx"
		
		dense_taz = pd.read_csv(misc_path + "Densified_TAZs.csv").sort_values('ID_FOR_CS')[['ID_FOR_CS']]
		dense_taz['dense'] = 1
		all_taz = pd.read_csv(mc_obj.config.taz_file)
		dense_taz_list = all_taz[['ID_FOR_CS']].merge(dense_taz,on = 'ID_FOR_CS',how = 'left').fillna(0).astype(bool)[:2730]

		with omx.open_file(pre_MC_trip_file_2016) as f1 , omx.open_file(pre_MC_trip_file_2040) as f2, omx.open_file(modified_2040,'w') as fout:
			for name in f1.list_matrices():
				tt_2016 = np.array(f1[name])[:2730,:2730]
				tt_2040 = np.array(f2[name])[:2730,:2730]
				diff = tt_2040 - tt_2016
				prod_sum_2016 = tt_2016.sum(axis = 1)
				prod_sum_2040 = tt_2040.sum(axis = 1)
				prod_sum_diff = diff.sum(axis = 1)
				sum_to_transfer = prod_sum_diff[~dense_taz_list['dense'].values].sum() * factor
				prod_sum_diff[~dense_taz_list['dense'].values] = prod_sum_diff[~dense_taz_list['dense'].values] * (1-factor)
				prod_sum_diff[dense_taz_list['dense'].values] = (prod_sum_diff[dense_taz_list['dense'].values] 
			+ sum_to_transfer * prod_sum_2040[dense_taz_list['dense'].values] / prod_sum_2040[dense_taz_list['dense'].values].sum())
				# distribute prod_sum to each attraction zone
				tt_new = pd.DataFrame(tt_2040).divide(pd.Series(prod_sum_2040), axis = 0).fillna(0).multiply(prod_sum_2016 + prod_sum_diff,axis = 0).values
				fout[name] = tt_new

		mc_obj.pre_MC_trip_table = mc_util.store_omx_as_dict(fout)
	
def transit_time_reduction(skim, idx_list, time_saving_list, factor = 0.3):
	for i in range(len(idx_list)):
		skim[tuple(idx_list[i])] -= min(time_saving_list[i],skim[tuple(idx_list[i])] * factor)
	return skim
	
def transit_modify_skim(mc_obj, TAZ_savings_file = misc_path + 'transit_TAZ_and_time_savings.csv',factor = 0.3):
	TAZ_savings = pd.read_csv(TAZ_savings_file)
	ivtt_idx_list = ( TAZ_savings[TAZ_savings['IVTT difference']!=0][['TAZ_0_skim','TAZ_1_skim']].values.tolist()
+  TAZ_savings[TAZ_savings['IVTT difference']!=0][['TAZ_1_skim','TAZ_0_skim']].values.tolist())

	ivtt_list = TAZ_savings[TAZ_savings['IVTT difference']!=0]['IVTT difference'].values.tolist() * 2

	ovtt_idx_list = ( TAZ_savings[TAZ_savings['OVTT difference']!=0][['TAZ_0_skim','TAZ_1_skim']].values.tolist()
+  TAZ_savings[TAZ_savings['OVTT difference']!=0][['TAZ_1_skim','TAZ_0_skim']].values.tolist())

	ovtt_list = TAZ_savings[TAZ_savings['OVTT difference']!=0]['OVTT difference'].values.tolist() * 2
	
	mc_obj.DAT_B_skim_PK['Total_IVTT'] = transit_time_reduction(mc_obj.DAT_B_skim_PK['Total_IVTT'], ivtt_idx_list, ivtt_list,factor)
	mc_obj.DAT_B_skim_OP['Total_IVTT'] = transit_time_reduction(mc_obj.DAT_B_skim_OP['Total_IVTT'], ivtt_idx_list, ivtt_list,factor)
	mc_obj.DAT_CR_skim_PK['Total_IVTT'] = transit_time_reduction(mc_obj.DAT_CR_skim_PK['Total_IVTT'], ivtt_idx_list, ivtt_list,factor) 
	mc_obj.DAT_CR_skim_OP['Total_IVTT'] = transit_time_reduction(mc_obj.DAT_CR_skim_OP['Total_IVTT'], ivtt_idx_list, ivtt_list,factor)
	mc_obj.DAT_RT_skim_PK['Total_IVTT'] = transit_time_reduction(mc_obj.DAT_RT_skim_PK['Total_IVTT'], ivtt_idx_list, ivtt_list,factor)
	mc_obj.DAT_RT_skim_OP['Total_IVTT'] = transit_time_reduction(mc_obj.DAT_RT_skim_OP['Total_IVTT'], ivtt_idx_list, ivtt_list,factor)
	mc_obj.DAT_LB_skim_PK['Total_IVTT'] = transit_time_reduction(mc_obj.DAT_LB_skim_PK['Total_IVTT'], ivtt_idx_list, ivtt_list,factor)
	mc_obj.DAT_LB_skim_OP['Total_IVTT'] = transit_time_reduction(mc_obj.DAT_LB_skim_OP['Total_IVTT'], ivtt_idx_list, ivtt_list,factor)
	mc_obj.WAT_skim_PK['Total_IVTT'] = transit_time_reduction(mc_obj.WAT_skim_PK['Total_IVTT'], ivtt_idx_list, ivtt_list,factor)
	mc_obj.WAT_skim_OP['Total_IVTT'] = transit_time_reduction(mc_obj.WAT_skim_PK['Total_IVTT'], ivtt_idx_list, ivtt_list,factor)
	
	mc_obj.DAT_B_skim_PK['Total_OVTT'] = transit_time_reduction(mc_obj.DAT_B_skim_PK['Total_OVTT'], ovtt_idx_list, ovtt_list,factor)
	mc_obj.DAT_B_skim_OP['Total_OVTT'] = transit_time_reduction(mc_obj.DAT_B_skim_OP['Total_OVTT'], ovtt_idx_list, ovtt_list,factor)
	mc_obj.DAT_CR_skim_PK['Total_OVTT'] = transit_time_reduction(mc_obj.DAT_CR_skim_PK['Total_OVTT'], ovtt_idx_list, ovtt_list,factor) 
	mc_obj.DAT_CR_skim_OP['Total_OVTT'] = transit_time_reduction(mc_obj.DAT_CR_skim_OP['Total_OVTT'], ovtt_idx_list, ovtt_list,factor)
	mc_obj.DAT_RT_skim_PK['Total_OVTT'] = transit_time_reduction(mc_obj.DAT_RT_skim_PK['Total_OVTT'], ovtt_idx_list, ovtt_list,factor)
	mc_obj.DAT_RT_skim_OP['Total_OVTT'] = transit_time_reduction(mc_obj.DAT_RT_skim_OP['Total_OVTT'], ovtt_idx_list, ovtt_list,factor)
	mc_obj.DAT_LB_skim_PK['Total_OVTT'] = transit_time_reduction(mc_obj.DAT_LB_skim_PK['Total_OVTT'], ovtt_idx_list, ovtt_list,factor)
	mc_obj.DAT_LB_skim_OP['Total_OVTT'] = transit_time_reduction(mc_obj.DAT_LB_skim_OP['Total_OVTT'], ovtt_idx_list, ovtt_list,factor)
	mc_obj.WAT_skim_PK['Total_OVTT'] = transit_time_reduction(mc_obj.WAT_skim_PK['Total_OVTT'], ovtt_idx_list, ovtt_list,factor)
	mc_obj.WAT_skim_OP['Total_OVTT'] = transit_time_reduction(mc_obj.WAT_skim_PK['Total_OVTT'], ovtt_idx_list, ovtt_list,factor)

def bike_time_distance_reduction(time_skim, dist_skim, idx_list, factor_list):
	for i in range(len(idx_list)):
		time_skim[tuple(idx_list[i])] -= time_skim[tuple(idx_list[i])]*factor_list[i]
		dist_skim[tuple(idx_list[i])] -= dist_skim[tuple(idx_list[i])]*factor_list[i]
	return time_skim, dist_skim
	
def active_transportation_modify_skim(mc_obj, bike_improvement_TAZ_file = misc_path + 'bike_trip_factors.csv'):
	TAZ_pair_df = pd.read_csv(bike_improvement_TAZ_file)
	idx_list = TAZ_pair_df[['TAZ_0_skim','TAZ_1_skim']].values.tolist()
	factor_list = TAZ_pair_df['factor_avg'].values.tolist()

	mc_obj.bike_skim['BikeTime'], mc_obj.bike_skim['Length (Skim)'] = bike_time_distance_reduction(mc_obj.bike_skim['BikeTime'], mc_obj.bike_skim['Length (Skim)'],idx_list, factor_list)
	
	mc_obj.bike_skim['OneMileorLess'] = 1*(mc_obj.bike_skim['Length (Skim)']<=1)
	
	
def active_transportation_decrease_PEV(mc_obj, factor = 0.9):
    mc_obj.AccPEV[0:447,0:447] *= factor
    mc_obj.EgrPEV[0:447,0:447] *= factor


def congestion_charge(mc_obj,amount = 5):
	cong_zones = mc_obj.taz_lu[mc_obj.taz_lu['BOSTON_NB'].isin(['Downtown','North End','West End','South Boston Waterfront','Chinatown','Bay Village','Back Bay'])]['ID'].values
	
	cong_charge_table = np.zeros((2730,2730))
	cong_charge_table[np.ix_(np.where(np.logical_not(mc_obj.taz_lu['ID'].iloc[:2730].isin(cong_zones).values))[0],
      np.where(mc_obj.taz_lu['ID'].iloc[:2730].isin(cong_zones).values)[0])] = amount
	
	mc_obj.drive_skim_PK['Auto_Toll (Skim)'] += cong_charge_table
	mc_obj.drive_skim_OP['Auto_Toll (Skim)'] += cong_charge_table
	
def TDM_modify_skim_trip_table(mc_obj, fare_reduction = 1, trip_reduction = 0.0035):
	# Run after the main process has finished
	tdm_zones = mc_obj.taz_lu[mc_obj.taz_lu['BOSTON_NB'].isin(['Downtown','North End','West End','South Boston Waterfront','Chinatown','Bay Village','Back Bay'])]['ID'].values
	# reduce transit fare for HBW trips ending in Downtown equivalent neighborhoods
	mc_obj.DAT_B_skim_PK['Total_Cost'][:,np.where(mc_obj.taz_lu['ID'].iloc[:2730].isin(tdm_zones).values)[0]] -= np.minimum(1,mc_obj.DAT_B_skim_PK['Total_Cost'][:,np.where(mc_obj.taz_lu['ID'].iloc[:2730].isin(tdm_zones).values)[0]])
	mc_obj.DAT_CR_skim_PK['Total_Cost'][:,np.where(mc_obj.taz_lu['ID'].iloc[:2730].isin(tdm_zones).values)[0]] -= np.minimum(1,mc_obj.DAT_CR_skim_PK['Total_Cost'][:,np.where(mc_obj.taz_lu['ID'].iloc[:2730].isin(tdm_zones).values)[0]])
	mc_obj.DAT_RT_skim_PK['Total_Cost'][:,np.where(mc_obj.taz_lu['ID'].iloc[:2730].isin(tdm_zones).values)[0]] -= np.minimum(1,mc_obj.DAT_RT_skim_PK['Total_Cost'][:,np.where(mc_obj.taz_lu['ID'].iloc[:2730].isin(tdm_zones).values)[0]])
	mc_obj.DAT_LB_skim_PK['Total_Cost'][:,np.where(mc_obj.taz_lu['ID'].iloc[:2730].isin(tdm_zones).values)[0]] -= np.minimum(1,mc_obj.DAT_LB_skim_PK['Total_Cost'][:,np.where(mc_obj.taz_lu['ID'].iloc[:2730].isin(tdm_zones).values)[0]])
	mc_obj.WAT_skim_PK['Total_Cost'][:,np.where(mc_obj.taz_lu['ID'].iloc[:2730].isin(tdm_zones).values)[0]] -= np.minimum(1,mc_obj.WAT_skim_PK['Total_Cost'][:,np.where(mc_obj.taz_lu['ID'].iloc[:2730].isin(tdm_zones).values)[0]])
	
	# reduce HBW trips going to these neighborhoods by 0.35%
	mc_obj.pre_MC_trip_table['HBW_PK_0Auto'][:,np.where(mc_obj.taz_lu['ID'].iloc[:2730].isin(tdm_zones).values)[0]] *= 1-trip_reduction
	mc_obj.pre_MC_trip_table['HBW_PK_wAuto'][:,np.where(mc_obj.taz_lu['ID'].iloc[:2730].isin(tdm_zones).values)[0]] *= 1-trip_reduction

def TDM_run(mc_obj):
	print('Rerunning HBW for TDM policy scenario...')
	mc_obj.run_for_purpose('HBW')
	print('HBW trips rerun with TDM policy scenario.')
	
	
def CAV_input_generator(mc_obj, cost_reduction = 0.50, parking_reduction = 0.75, travel_time_reduction = 0.50, HH_shift = 0.1):
	# create param for CAV households, alternative baseline and mangement policies
	if switches['smart_mobility'] == True:
		if switches['smart_mobility_management_policy']:
			param_file = mc_obj.config.SM_calib_param_file
		else:
			param_file = mc_obj.config.SM_calib_param_mngpol_file
		param_out = misc_path + "CAV_param_SM_on.xlsx"
		#param_mngpol_out = r"X:\Proj\2018\180021 - ISE_GHGMitAnly\001\Data\CTPS_Data\Mode Choice Related\CAV_mngpol_param_SM_on.xlsx"
	else:
		param_file = mc_obj.config.param_file
		param_out = misc_path + "CAV_param_SM_off.xlsx"
		#param_mngpol_out = r"X:\Proj\2018\180021 - ISE_GHGMitAnly\001\Data\CTPS_Data\Mode Choice Related\CAV_mngpol_param_SM_off.xlsx"
	
	writer1 = pd.ExcelWriter(param_out,engine = 'openpyxl')
	for purpose in ['HBW','HBO','NHB', 'HBSc1','HBSc2','HBSc3']:
	# TODO: what's the CAV management policy?
		param = pd.read_excel(param_file, sheet_name = purpose,index_col = 0)
		try:
			param.loc['DA','Cost'] *= (1 - cost_reduction)
			param.loc['DA','Parking'] *= (1 - parking_reduction)
			param.loc['DA','IVTT'] *= (1 - travel_time_reduction)
		except:
			pass
		param.to_excel(writer1, sheet_name = purpose)
	writer1.save()
	
	# create two sets of trip tables: one with all 0-veh HHs and 90% of the 1+ veh HHs, the other with 10% of the 1+ veh HHs
	trip_table_conventional = copy.deepcopy(mc_obj.pre_MC_trip_table)
	trip_table_CAV = copy.deepcopy(mc_obj.pre_MC_trip_table)
    
	hh_0_veh = list(filter(re.compile('.*_0Auto').match, list(trip_table_conventional.keys())))
	hh_1_veh = list(filter(re.compile('.*_wAuto').match, list(trip_table_conventional.keys())))
	for segment in hh_1_veh:
		trip_table_conventional[segment] *= (1-HH_shift)
		trip_table_CAV[segment] *= HH_shift
	
	for segment in hh_0_veh:
		trip_table_CAV[segment] *= 0
    
	return param_out, trip_table_conventional, trip_table_CAV
	
def smart_mobility_shift_HH(mc_obj):
	# check if mc_obj has a calibrated smart mobility parameter file
	
	if hasattr(mc_obj.config, 'SM_calib_param_file') == False and hasattr(mc_obj.config, 'SM_calib_param_mngpol_file')== False:
		print('Smart mobility parameter file is not provided in config.')
		
	else:
		# modify trip tables of mc_obj
		TNC_data = pd.read_csv(misc_path + 'trips_veh_ownership.csv')[['TOWN','amount_to_shift','origin_trips_HH0','origin_trips_HH1']]
		taz = pd.read_csv(mc_obj.config.taz_file)
		for item in TNC_data.itertuples():
			town = item.TOWN
			
			if len(taz.query('TOWN == "town"+",MA"')) == 0:
				print(f'{town} not found in taz')
			
			hh0_old_total = item.origin_trips_HH0
			hh0_new_total = item.origin_trips_HH0 + item.amount_to_shift
			hh1_old_total = item.origin_trips_HH1
			hh1_new_total = item.origin_trips_HH1 - item.amount_to_shift
			
			hh_0_veh = list(filter(re.compile('.*_0Auto').match, list(mc_obj.pre_MC_trip_table.keys())))
			hh_1_veh = list(filter(re.compile('.*_wAuto').match, list(mc_obj.pre_MC_trip_table.keys())))
			
			for segment in hh_0_veh:
				mc_obj.pre_MC_trip_table[i][:2730,:2730][taz['TOWN']==town+',MA',:] *= hh0_new_total / hh0_old_total
			
			for segment in hh_1_veh:
				mc_obj.pre_MC_trip_table[i][:2730,:2730][taz['TOWN'] == town+',MA',:] *= hh1_new_total / hh1_old_total

				
