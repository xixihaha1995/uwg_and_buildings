import datetime
import numpy as np, pandas as pd, os, sys
import configparser, threading, time

sys.path.insert(0, 'C:\EnergyPlusV22-1-0')
from pyenergyplus.api import EnergyPlusAPI
ep_sensWaste_w_m2_per_footprint_area = 0
save_path_clean = False
def init_all(ini_file_name):
    global config, saving_data, sem0, sem1,sem2,sem3, called_ep_bool, ep_api, psychrometric, \
        input_folder, output_folder,project_path, uwg_param_path, epw_path, mediumOfficeBld_one_floor_area_m2, \
        ep_sensWaste_w_m2_per_footprint_area, uwg_time_index_in_seconds, \
        ep_floor_Text_K, ep_floor_Tint_K, ep_roof_Text_K, ep_roof_Tint_K, \
        ep_wallSun_Text_K, ep_wallSun_Tint_K, ep_wallShade_Text_K, ep_wallShade_Tint_K, \
        ep_oaTemp_C, ep_indoorTemp_C

    project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config = configparser.ConfigParser()
    input_folder = os.path.join(project_path, 'UWG_Cases_Inputs')
    config_path = os.path.join(input_folder, ini_file_name)
    config.read(config_path)

    output_folder = os.path.join(project_path, 'UWG_Cases_Outputs',ini_file_name[:-4],
                                 config['Default']['experiments_theme'])
    if not os.path.exists(input_folder):
        os.makedirs(input_folder)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    uwg_param_path = os.path.join(input_folder, config['Default']['uwg_file_name'])
    epw_path = os.path.join(input_folder, config['Default']['epwFileName'])
    sem0 = threading.Semaphore(1)
    sem1 = threading.Semaphore(0)
    sem2 = threading.Semaphore(0)
    sem3 = threading.Semaphore(0)
    called_ep_bool = False

    ep_api = EnergyPlusAPI()
    psychrometric = None

    saving_data = {}
    saving_data['debugging_canyon'] = []
    saving_data['can_Averaged_temp_k_specHum_ratio_press_pa'] = []
    saving_data['s_wall_Text_K_n_wall_Text_K'] = []
    mediumOfficeBld_one_floor_area_m2 = 4982 / 3
    uwg_time_index_in_seconds = 0

    ep_sensWaste_w_m2_per_footprint_area = 0
    ep_oaTemp_C = 7
    ep_indoorTemp_C = 20

    ep_floor_Text_K = 300
    ep_floor_Tint_K = 300
    ep_roof_Text_K = 300
    ep_roof_Tint_K = 300
    ep_wallSun_Text_K = 300
    ep_wallSun_Tint_K = 300
    ep_wallShade_Text_K = 300
    ep_wallShade_Tint_K = 300

def BEMCalc_Element(UCM, BEM,forc, it, simTime):
    global uwg_time_index_in_seconds, \
        UWG_canTemp_K, UWG_canSpecHum_Ratio, UWG_forcPres_Pa, ep_sensWaste_w_m2_per_footprint_area

    sem0.acquire()
    uwg_time_index_in_seconds = (it ) * simTime.dt
    UWG_canTemp_K = UCM.canTemp
    UWG_canSpecHum_Ratio = UCM.canHum
    UWG_forcPres_Pa = forc.pres
    BEM_building = BEM.building
    BEM_building.nFloor = max(UCM.bldHeight / float(BEM_building.floor_height), 1)
    BEM_building.GasTotal = 0
    sem1.release()


    sem3.acquire()
    BEM_building.indoor_temp = ep_indoorTemp_C + 273.15
    BEM_building.sensWaste = ep_sensWaste_w_m2_per_footprint_area
    ep_sensWaste_w_m2_per_footprint_area = 0

    BEM.mass.layerTemp[0] = ep_floor_Text_K
    # BEM.mass.Tint = ep_floor_Tint_K
    BEM.wall.layerTemp[0] = (ep_wallSun_Text_K +ep_wallShade_Text_K ) / 2
    # BEM.wallSun.Tint = ep_wallSun_Tint_K
    BEM.roof.layerTemp[0] = ep_roof_Text_K
    BEM_building.ElecTotal = 0

    WallshadeT = ep_wallShade_Text_K
    WalllitT = ep_wallSun_Text_K
    RoofT = ep_roof_Text_K
    senWaste = BEM_building.sensWaste

    data_saving_path = os.path.join(output_folder, 'saving.csv')
    global save_path_clean
    if os.path.exists(data_saving_path) and not save_path_clean:
        os.remove(data_saving_path)
        save_path_clean = True
    # start_time + accumulative_seconds
    cur_datetime = datetime.datetime.strptime(config['Default']['start_time'], '%Y-%m-%d %H:%M:%S') + \
                   datetime.timedelta(seconds=uwg_time_index_in_seconds)
    print(f'cur_datetime: {cur_datetime}, canTemp: {UWG_canTemp_K}')
    # if not exist, create the file and write the header
    if not os.path.exists(data_saving_path):
        os.makedirs(os.path.dirname(data_saving_path), exist_ok=True)
        with open(data_saving_path, 'a') as f1:
            # prepare the header string for different sensors
            header_str = 'cur_datetime,UWG_canTemp_K, senWaste, UWG_forcPres_Pa,WallshadeT, WalllitT, RoofT,'
            header_str += '\n'
            f1.write(header_str)
    # write the data
    with open(data_saving_path, 'a') as f1:
        fmt1 = "%s," * 1 % (cur_datetime) + \
               "%.3f," * 6 % (UWG_canTemp_K, senWaste, UWG_forcPres_Pa,WallshadeT, WalllitT, RoofT) + '\n'
        f1.write(fmt1)

    sem0.release()
    return BEM
