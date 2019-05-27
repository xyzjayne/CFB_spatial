import numpy as np

# skims
data_path = r"../CTPS_Data_ModelOutputs_2040/"
drive_skim_PK_file = data_path + 'AM/SOV_skim.omx'
drive_skim_OP_file = data_path + 'MD/SOV_skim.omx'
DAT_B_skim_PK_file = data_path + 'AM/A_DAT_for_Boat_tr_skim.omx'
DAT_B_skim_OP_file = data_path + 'MD/A_DAT_for_Boat_tr_skim.omx'
DAT_CR_skim_PK_file = data_path + 'AM/A_DAT_for_CommRail_tr_skim.omx'
DAT_CR_skim_OP_file = data_path + 'MD/A_DAT_for_CommRail_tr_skim.omx'
DAT_RT_skim_PK_file = data_path + 'AM/A_DAT_for_Rapid_Transit_tr_skim.omx'
DAT_RT_skim_OP_file = data_path + 'MD/A_DAT_for_Rapid_Transit_tr_skim.omx'
DAT_LB_skim_PK_file = data_path + 'AM/A_DAT_for_LocalBus_tr_skim.omx'
DAT_LB_skim_OP_file = data_path + 'MD/A_DAT_for_LocalBus_tr_skim.omx'
WAT_skim_PK_file = data_path + 'AM/WAT_for_All_tr_skim.omx'
WAT_skim_OP_file = data_path + 'MD/WAT_for_All_tr_skim.omx'
bike_skim_file = data_path + "2040_Bike_Skim.omx"
walk_skim_file = data_path + "2040_Walk_Skim.omx"

skim_list = ['drive_skim_PK',
'drive_skim_OP',
'DAT_B_skim_PK',
'DAT_B_skim_OP',
'DAT_CR_skim_PK',
'DAT_CR_skim_OP',
'DAT_RT_skim_PK',
'DAT_RT_skim_OP',
'DAT_LB_skim_PK',
'DAT_LB_skim_OP',
'WAT_skim_PK',
'WAT_skim_OP',
'bike_skim',
'walk_skim']

# pre-MC trip table
pre_MC_trip_file = misc_path + 'Aggregated Matrix_2040NB/pre_MC_trip_6_purposes.omx'

# land use

taz_path = r"../LandUse/"
misc_path = r"../Other/"
taz_file = misc_path + "SW_TAZ_2010.csv"
land_use_file = taz_path + "Land_Use_2040.csv"
taz_parking_file = taz_path + "Land_Use_Parking_Costs.csv"
taz_zonal_file = taz_path + "TAZ_zonal_2040.csv"

# model purpose
purpose = 'HBSc1'

# model parameter
param_file = misc_path + "param_calib_0716.xlsx"

# drive mode average occupancy
AO_dict = {'HBW':{'DA':1,'SR2':2,'SR3+':3.5,'SM_RA':1,'SM_SH':2},
	'HBO':{'DA':1,'SR2':2,'SM_RA':1,'SM_SH':2},
	'NHB':{'DA':1,'SR2':2,'SM_RA':1,'SM_SH':2},
	'HBSc1':{'DA':1,'SR2':2,'SM_RA':1,'SM_SH':2},
	'HBSc2':{'DA':1,'SR2':2,'SM_RA':1,'SM_SH':2},
	'HBSc3':{'DA':1,'SR2':2,'SM_RA':1,'SM_SH':2}
	}

# cost per mile
cost_per_mile = 0.184

# smart mobility factors
SM_calib_param_file = misc_path + "param_calib_SM.xlsx"
SM_calib_param_mngpol_file = misc_path + "param_calib_SM_mngpol.xlsx"
SM_SH_IVTT_factor = 1.3
SM_SH_OVTT_factor = 1.3
SM_SH_cost_factor = 1.3

SM_RA_OVTT_table = 5 * np.ones((2730,2730))

SM_distance_coef = 1.35
SM_time_coef = 0.21
SM_base_fare = 2.1 + 1.85 # base + booking

SM_SH_AO = 2 # average occupancy of shared smart mobility ride
SM_VMT_overhead = 1.5


# output path
out_path = r'../output//'

#%% Switches for Scenarios
scenario_switches = dict.fromkeys(["clean_vehicle" , "growth_shift" , "transit_improvements" , "active_transportation_improvements" , "TDM" , "CAV" , "smart_mobility" , "congestion_charge"])
scenario_switches['clean_vehicle'] = False
scenario_switches['growth_shift'] = False
scenario_switches['transit_improvements'] = False
scenario_switches['active_transportation_improvements'] = False
scenario_switches['TDM'] = False
scenario_switches['CAV'] = False
# scenario_switches['CAV_management_policy'] = False
scenario_switches['smart_mobility'] = False
# scenario_switches['smart_mobility_management_policy'] = False
scenario_switches['congestion_charge'] = False










