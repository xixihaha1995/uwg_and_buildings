import numpy as np, pandas as pd, os, sys
import configparser, threading, time

sys.path.insert(0, 'C:\EnergyPlusV22-1-0')
from pyenergyplus.api import EnergyPlusAPI
ep_sensWaste_w_m2_per_floor_area = 0
def init_all(case_name):
    global config, saving_data, sem0, sem1,sem2,sem3, called_ep_bool, ep_api, psychrometric, \
        input_folder, output_folder, uwg_param_path, epw_path, mediumOfficeBld_floor_area_m2, \
        ep_sensWaste_w_m2_per_floor_area, uwg_time_index_in_seconds, \
        ep_floor_Text_K, ep_floor_Tint_K, ep_roof_Text_K, ep_roof_Tint_K, \
        ep_wallSun_Text_K, ep_wallSun_Tint_K, ep_wallShade_Text_K, ep_wallShade_Tint_K, \
        ep_indoorTemp_C, ep_indoorHum_Ratio, ep_sensCoolDemand_w_m2, ep_sensHeatDemand_w_m2, ep_coolConsump_w_m2, ep_heatConsump_w_m2, \
        ep_elecTotal_w_m2_per_floor_area, ep_sensWaste_w_m2_per_floor_area, ep_oaTemp_C

    config = configparser.ConfigParser()
    # find the project path
    project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_folder = os.path.join(project_path, 'UWG_Cases_Inputs',case_name)
    output_folder = os.path.join(project_path, 'UWG_Cases_Outputs',case_name)
    if not os.path.exists(input_folder):
        os.makedirs(input_folder)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    config_path = os.path.join(input_folder, 'config.ini')
    config.read(config_path)

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

    mediumOfficeBld_floor_area_m2 = 4982
    uwg_time_index_in_seconds = 0

    ep_indoorTemp_C = 20
    ep_indoorHum_Ratio = 0.006
    ep_sensCoolDemand_w_m2 = 0
    ep_sensHeatDemand_w_m2 = 0
    ep_coolConsump_w_m2 = 0
    ep_heatConsump_w_m2 = 0
    ep_elecTotal_w_m2_per_floor_area = 0
    ep_sensWaste_w_m2_per_floor_area = 0
    ep_oaTemp_C = 7

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
        UWG_canTemp_K, UWG_canSpecHum_Ratio, UWG_forcPres_Pa, ep_sensWaste_w_m2_per_floor_area

    if not sem0.acquire(timeout= 60):
        sys.exit('BEMCalc_Element: sem0.acquire() timeout')
    # VCWG upload canyon info to Parent
    uwg_time_index_in_seconds = (it + 1) * simTime.dt

    UWG_canTemp_K = UCM.canTemp
    UWG_canSpecHum_Ratio = UCM.canHum
    UWG_forcPres_Pa = forc.pres
    saving_data['can_Averaged_temp_k_specHum_ratio_press_pa'].append([UWG_canTemp_K, UWG_canSpecHum_Ratio,
                                                                      UWG_forcPres_Pa])
    BEM_building = BEM.building
    BEM_building.nFloor = max(UCM.bldHeight / float(BEM_building.floor_height), 1)
    # print(f'VCWG: Update needed time index[accumulated seconds]: {vcwg_time_index_in_seconds}\n')
    # Notify to the downstream (EP download canyon info from Parent) to start
    sem1.release()


    # Waiting for the upstream (EP upload results to Parent) to finish
    sem3.acquire()
    # VCWG download EP results from Parent
    BEM_building.sensWaste = ep_sensWaste_w_m2_per_floor_area * BEM_building.nFloor
    # print(f'VCWG: Update needed time index[Month Day, Hour, Minute, Second]: {}\n')
    day_hour_min_sec = time.strftime("%m %d %H %M %S", time.gmtime(uwg_time_index_in_seconds))

    print(f"m d H M S:{day_hour_min_sec}, "
          f"sensWaste (Currently only HVAC Rejection):{BEM_building.sensWaste} watts/ unit footprint area")
    ep_sensWaste_w_m2_per_floor_area = 0
    BEM_building.ElecTotal = ep_elecTotal_w_m2_per_floor_area * BEM_building.nFloor
    BEM.mass.layerTemp[0] = ep_floor_Text_K
    # BEM.mass.Tint = ep_floor_Tint_K
    BEM.wall.layerTemp[0] = (ep_wallSun_Text_K +ep_wallShade_Text_K ) / 2
    # BEM.wallSun.Tint = ep_wallSun_Tint_K
    BEM.roof.layerTemp[0] = ep_roof_Text_K

    saving_data['debugging_canyon'].append([ep_wallSun_Text_K - 273.15,
                                            ep_wallShade_Text_K -273.15, ep_floor_Text_K - 273.15, ep_roof_Text_K - 273.15,
                                            BEM_building.sensWaste, ep_oaTemp_C, UWG_canTemp_K - 273.15])

    saving_data['s_wall_Text_K_n_wall_Text_K'].append([BEM.wallSun.Text, BEM.wallShade.Text])


    # if time_step_version == 2:
    #     saving_data['vcwg_wsp_mps_wdir_deg_ep_wsp_mps_wdir_deg'].append([vcwg_wsp_mps, vcwg_wdir_deg, ep_wsp_mps, ep_wdir_deg])
    # # floor mass, wallSun, wallShade, roofImp, roofVeg
    # if FractionsRoof.fimp > 0:
    #     BEM.roofImp.Text = ep_roof_Text_K
    #     BEM.roofImp.Tint = ep_roof_Tint_K
    # if FractionsRoof.fveg > 0:
    #     BEM.roofVeg.Text = ep_roof_Text_K
    #     BEM.roofVeg.Tint = ep_roof_Tint_K

    BEM_building.sensCoolDemand = ep_sensCoolDemand_w_m2
    BEM_building.sensHeatDemand = ep_sensHeatDemand_w_m2
    BEM_building.coolConsump = ep_coolConsump_w_m2
    BEM_building.heatConsump = ep_heatConsump_w_m2
    BEM_building.indoorTemp = ep_indoorTemp_C + 273.15
    BEM_building.indoorHum = ep_indoorHum_Ratio

    BEM_building.indoorRhum = 0.6
    BEM_building.sensWasteCoolHeatDehum = 0.0  # Sensible waste heat per unit building footprint area only including cool, heat, and dehum [W m-2]
    BEM_building.dehumDemand = 0.0  # Latent heat demand for dehumidification of air per unit building footprint area [W m^-2]
    BEM_building.dehumDemand = 0.5
    BEM_building.fluxSolar = 0.5
    BEM_building.fluxWindow = 0.5
    BEM_building.fluxInterior = 0.5
    BEM_building.fluxInfil = 0.5
    BEM_building.fluxVent = 0.5
    BEM_building.QWater = 0.5
    BEM_building.QGas = 0.5
    BEM_building.Qhvac = 0.5
    BEM_building.Qheat = 0.5
    BEM_building.GasTotal = 0.5
    # wall load per unit building footprint area [W m^-2]
    BEM_building.QWall = 0.5
    # other surfaces load per unit building footprint area [W m^-2]
    BEM_building.QMass = 0.5
    # window load due to temperature difference per unit building footprint area [W m^-2]
    BEM_building.QWindow = 0.5
    # ceiling load per unit building footprint area [W m^-2]
    BEM_building.QCeil = 0.5
    # infiltration load per unit building footprint area [W m^-2]
    BEM_building.QInfil = 0.5
    # ventilation load per unit building footprint area [W m^-2]
    BEM_building.QVen = 0.5
    BEM_building.QWindowSolar = 0.5
    BEM_building.elecDomesticDemand = 0.5
    BEM_building.sensWaterHeatDemand = 0.5
    BEM_building.fluxWall = 0
    BEM_building.fluxRoof = 0
    BEM_building.fluxMass = 0
    # Notify to the downstream (VCWG upload canyon info to Parent) to start
    sem0.release()

    return BEM

def add_date_index(df, start_date, time_interval_sec):
    '''
    df is [date, sensible/latent]
    '''
    date = pd.date_range(start_date, periods=len(df), freq='{}S'.format(time_interval_sec))
    date = pd.Series(pd.to_datetime(date))
    year = date[0].year
    this_year_feb_29 = pd.to_datetime(str(year) + '-02-29')
    if year % 4 == 0 and (date == this_year_feb_29).any():
        date = date.apply(lambda x: x + pd.Timedelta(days=1) if x >= pd.Timestamp(date[0].year, 2, 29) else x)
    df.index = date
    return df

def save_data_to_csv(saving_data, file_name,case_name, start_time, time_interval_sec, vcwg_ep_saving_path):
    data_arr = np.array(saving_data[file_name])
    df = pd.DataFrame(data_arr)
    if file_name == 'can_Averaged_temp_k_specHum_ratio_press_pa':
        df.columns = ['Temp_K', 'SpecHum_Ratio', 'Press_Pa']
    elif file_name == 'debugging_canyon':
    # 'debugging_canyon' includes wallSun, wallShade, floor, roof, sensWaste(W/per unit footprint area),
    # canTemp_ep, canTemp_vcwg
        df.columns = ['wallSun', 'wallShade', 'floor', 'roof', 'sensWaste', 'canTemp_ep', 'canTemp_vcwg']
    else:
        df.columns = [f'(m) {file_name}_' + str(0.5 + i) for i in range(len(df.columns))]
    df = add_date_index(df, start_time, time_interval_sec)
    # save to excel, if non-exist, create one
    if not os.path.exists(vcwg_ep_saving_path):
        os.makedirs(vcwg_ep_saving_path)
    df.to_excel(os.path.join(vcwg_ep_saving_path, f'{case_name}_{file_name}.xlsx'))
