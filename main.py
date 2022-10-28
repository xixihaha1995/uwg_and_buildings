from uwg import UWG, _0_parent as parent

parent.init_saving_data()

epw_path = "resources/Mondouzil_tdb_td_rh_P_2004.epw" # available in resources directory.
param_path = "resources/initialize_Capitoul.uwg"  # available in resources directory.
model = UWG.from_param_file(param_path, epw_path=epw_path)

model.generate()
model.simulate()
model.write_epw()

data_name_lst = ['debugging_canyon']
start_time = '2004-06-01 00:00:00'
case_name = 'CAPITOUL_UWG_2004_06_01'
time_interval_sec = 300
vcwg_ep_saving_path = 'UWG_Intermediate_Results'

for data_name in data_name_lst:
    parent.save_data_to_csv(parent.saving_data, data_name,case_name,
                                        start_time, time_interval_sec, vcwg_ep_saving_path)