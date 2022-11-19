from . import _0_parent as parent
import os, signal

get_ep_results_inited_handle = False
overwrite_ep_weather_inited_handle = False
accu_hvac_heat_rejection_J = 0
zone_floor_area_m2 = 0
ep_last_accumulated_time_index_in_seconds = 0
ep_last_call_time_seconds = 0

def api_to_csv(state):
    orig = parent.ep_api.exchange.list_available_api_data_csv(state)
    newFileByteArray = bytearray(orig)
    api_path = os.path.join(parent.input_folder,'api_data.csv')
    newFile = open(api_path, "wb")
    newFile.write(newFileByteArray)
    newFile.close()

def run_ep():
    state = parent.ep_api.state_manager.new_state()
    parent.psychrometric = parent.ep_api.functional.psychrometrics(state)
    parent.ep_api.runtime.callback_begin_zone_timestep_before_set_current_weather(state,
                                                                          overwrite_ep_weather)
    if 'mediumOffice' in parent.config['Default']['time_step_handlers']:
        parent.ep_api.runtime.callback_end_system_timestep_after_hvac_reporting(state,
                                                                                      mediumOffice_get_ep_results)

    parent.ep_api.exchange.request_variable(state, "HVAC System Total Heat Rejection Energy", "SIMHVAC")
    parent.ep_api.exchange.request_variable(state, "Site Wind Speed", "ENVIRONMENT")
    parent.ep_api.exchange.request_variable(state, "Site Wind Direction", "ENVIRONMENT")
    parent.ep_api.exchange.request_variable(state, "Site Outdoor Air Drybulb Temperature", "ENVIRONMENT")
    parent.ep_api.exchange.request_variable(state, "Site Outdoor Air Humidity Ratio", "ENVIRONMENT")


    output_path = os.path.join(parent.output_folder, 'ep_optional_outputs')
    weather_file_path = os.path.join(parent.input_folder, parent.config['Default']['epwFileName'])
    idfFilePath = os.path.join(parent.input_folder, parent.config['Default']['idfFileName'])
    sys_args = '-d', output_path, '-w', weather_file_path, idfFilePath
    parent.ep_api.runtime.run_energyplus(state, sys_args)

def overwrite_ep_weather(state):
    global overwrite_ep_weather_inited_handle, odb_actuator_handle, orh_actuator_handle,\
        oat_sensor_handle, orh_sensor_handle, \
        wsped_mps_actuator_handle, wdir_deg_actuator_handle,\
        called_vcwg_bool

    if not overwrite_ep_weather_inited_handle:
        api_to_csv(state)
        if not parent.ep_api.exchange.api_data_fully_ready(state):
            return
        overwrite_ep_weather_inited_handle = True
        odb_actuator_handle = parent.ep_api.exchange.\
            get_actuator_handle(state, "Weather Data", "Outdoor Dry Bulb", "Environment")
        orh_actuator_handle = parent.ep_api.exchange.\
            get_actuator_handle(state, "Weather Data", "Outdoor Relative Humidity", "Environment")
        oat_sensor_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                             "Site Outdoor Air Drybulb Temperature",
                                                                             "Environment")
        orh_sensor_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                             "Site Outdoor Air Humidity Ratio",
                                                                             "Environment")

        #if one of the above handles is less than 0, then the actuator is not available
        # the entire program (multithread cooperation) should be terminated here, system exit with print messagePYTHO
        if odb_actuator_handle < 0 or orh_actuator_handle < 0 or orh_sensor_handle < 0:
            print('ovewrite_ep_weather(): some handle not available')
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)

    warm_up = parent.ep_api.exchange.warmup_flag(state)
    if not warm_up:
        # Wait for the upstream (VCWG upload canyon info to Parent) to finish
        parent.sem1.acquire()
        # EP download the canyon info from Parent
        oat_temp_c = parent.ep_api.exchange.get_variable_value(state, oat_sensor_handle)
        orh_ratio = parent.ep_api.exchange.get_variable_value(state, orh_sensor_handle)
        print(f'original oat C :{oat_temp_c}, set to {parent.UWG_canTemp_K - 273.15}')
        print(f'original orh ratio :{orh_ratio}, set to {parent.UWG_canSpecHum_Ratio}')
        rh_percentage = 100*parent.psychrometric.relative_humidity_b(state, parent.UWG_canTemp_K - 273.15,
                                               parent.UWG_canSpecHum_Ratio, parent.UWG_forcPres_Pa)
        parent.ep_api.exchange.set_actuator_value(state, odb_actuator_handle, parent.UWG_canTemp_K - 273.15)
        parent.ep_api.exchange.set_actuator_value(state, orh_actuator_handle, rh_percentage)
        # Notify the downstream (EP upload EP results to Parent) to start
        parent.sem2.release()

def mediumOffice_get_ep_results(state):
    global get_ep_results_inited_handle, oat_sensor_handle, \
        hvac_heat_rejection_sensor_handle, zone_flr_area_handle, \
        zone_indor_temp_sensor_handle, zone_indor_spe_hum_sensor_handle, \
        sens_cool_demand_sensor_handle, sens_heat_demand_sensor_handle, \
        cool_consumption_sensor_handle, heat_consumption_sensor_handle, \
        flr_pre1_Text_handle, flr_pre2_Text_handle, flr_pre3_Text_handle, flr_pre4_Text_handle, \
        flr_core_Text_handle, \
        roof_Text_handle, \
        s_wall_bot_1_Text_handle, s_wall_mid_1_Text_handle, s_wall_top_1_Text_handle, \
        n_wall_bot_1_Text_handle, n_wall_mid_1_Text_handle, n_wall_top_1_Text_handle, \
        s_wall_bot_1_Solar_handle, s_wall_mid_1_Solar_handle, s_wall_top_1_Solar_handle, \
        n_wall_bot_1_Solar_handle, n_wall_mid_1_Solar_handle, n_wall_top_1_Solar_handle, \
        flr_pre1_Tint_handle, flr_pre2_Tint_handle, flr_pre3_Tint_handle, flr_pre4_Tint_handle, \
        flr_core_Tint_handle, \
        roof_Tint_handle, \
        s_wall_bot_1_Tint_handle, s_wall_mid_1_Tint_handle, s_wall_top_1_Tint_handle, \
        n_wall_bot_1_Tint_handle, n_wall_mid_1_Tint_handle, n_wall_top_1_Tint_handle

    if not get_ep_results_inited_handle:
        if not parent.ep_api.exchange.api_data_fully_ready(state):
            return
        get_ep_results_inited_handle = True
        oat_sensor_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                             "Site Outdoor Air Drybulb Temperature",
                                                                             "Environment")
        hvac_heat_rejection_sensor_handle = \
            parent.ep_api.exchange.get_variable_handle(state,
                                                             "HVAC System Total Heat Rejection Energy",
                                                             "SIMHVAC")
        zone_flr_area_handle =  parent.ep_api.exchange.get_internal_variable_handle(state, "Zone Floor Area",
                                                                          "CORE_MID")
        zone_indor_temp_sensor_handle = parent.ep_api.exchange.get_variable_handle(state, "Zone Air Temperature",
                                                                                         "CORE_MID")
        zone_indor_spe_hum_sensor_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                            "Zone Air Humidity Ratio",
                                                                                            "CORE_MID")
        sens_cool_demand_sensor_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                          "Zone Air System Sensible Cooling Rate",
                                                                                          "CORE_MID")
        sens_heat_demand_sensor_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                          "Zone Air System Sensible Heating Rate",
                                                                                          "CORE_MID")
        cool_consumption_sensor_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                          "Cooling Coil Electricity Rate",
                                                                                          "VAV_2_COOLC DXCOIL")
        heat_consumption_sensor_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                          "Heating Coil Heating Rate",
                                                                                          "CORE_MID VAV BOX REHEAT COIL")
        flr_pre1_Text_handle = parent.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature",
                                                                                "Perimeter_bot_ZN_1_Floor")
        flr_pre2_Text_handle = parent.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature",
                                                                                "Perimeter_bot_ZN_2_Floor")
        flr_pre3_Text_handle = parent.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature",
                                                                                "Perimeter_bot_ZN_3_Floor")
        flr_pre4_Text_handle = parent.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature",
                                                                                "Perimeter_bot_ZN_4_Floor")
        flr_core_Text_handle = parent.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature",
                                                                                "Core_bot_ZN_5_Floor")
        roof_Text_handle = parent.ep_api.exchange.get_variable_handle(state, "Surface Outside Face Temperature",
                                                                            "Building_Roof")
        s_wall_bot_1_Text_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                              "Surface Outside Face Temperature",
                                                                              "Perimeter_bot_ZN_1_Wall_South")
        s_wall_mid_1_Text_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                    "Surface Outside Face Temperature",
                                                                                    "Perimeter_mid_ZN_1_Wall_South")
        s_wall_top_1_Text_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                    "Surface Outside Face Temperature",
                                                                                    "Perimeter_top_ZN_1_Wall_South")
        n_wall_bot_1_Text_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                    "Surface Outside Face Temperature",
                                                                                    "Perimeter_bot_ZN_3_Wall_North")
        n_wall_mid_1_Text_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                    "Surface Outside Face Temperature",
                                                                                    "Perimeter_mid_ZN_3_Wall_North")
        n_wall_top_1_Text_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                    "Surface Outside Face Temperature",
                                                                                    "Perimeter_top_ZN_3_Wall_North")
        s_wall_bot_1_Solar_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                     "Surface Outside Face Incident Solar Radiation Rate per Area",
                                                                                     "Perimeter_bot_ZN_1_Wall_South")
        s_wall_mid_1_Solar_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                     "Surface Outside Face Incident Solar Radiation Rate per Area",
                                                                                     "Perimeter_mid_ZN_1_Wall_South")
        s_wall_top_1_Solar_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                     "Surface Outside Face Incident Solar Radiation Rate per Area",
                                                                                     "Perimeter_top_ZN_1_Wall_South")
        n_wall_bot_1_Solar_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                     "Surface Outside Face Incident Solar Radiation Rate per Area",
                                                                                     "Perimeter_bot_ZN_3_Wall_North")
        n_wall_mid_1_Solar_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                     "Surface Outside Face Incident Solar Radiation Rate per Area",
                                                                                     "Perimeter_mid_ZN_3_Wall_North")
        n_wall_top_1_Solar_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                     "Surface Outside Face Incident Solar Radiation Rate per Area",
                                                                                     "Perimeter_top_ZN_3_Wall_North")
        flr_pre1_Tint_handle = parent.ep_api.exchange.get_variable_handle(state, "Surface Inside Face Temperature",
                                                                                "Perimeter_bot_ZN_1_Floor")
        flr_pre2_Tint_handle = parent.ep_api.exchange.get_variable_handle(state, "Surface Inside Face Temperature",
                                                                                "Perimeter_bot_ZN_2_Floor")
        flr_pre3_Tint_handle = parent.ep_api.exchange.get_variable_handle(state, "Surface Inside Face Temperature",
                                                                                "Perimeter_bot_ZN_3_Floor")
        flr_pre4_Tint_handle = parent.ep_api.exchange.get_variable_handle(state, "Surface Inside Face Temperature",
                                                                                "Perimeter_bot_ZN_4_Floor")
        flr_core_Tint_handle = parent.ep_api.exchange.get_variable_handle(state, "Surface Inside Face Temperature",
                                                                                "Core_bot_ZN_5_Floor")
        roof_Tint_handle = parent.ep_api.exchange.get_variable_handle(state, "Surface Inside Face Temperature",
                                                                            "Building_Roof")
        s_wall_bot_1_Tint_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                    "Surface Inside Face Temperature",
                                                                                    "Perimeter_bot_ZN_1_Wall_South")
        s_wall_mid_1_Tint_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                    "Surface Inside Face Temperature",
                                                                                    "Perimeter_mid_ZN_1_Wall_South")
        s_wall_top_1_Tint_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                    "Surface Inside Face Temperature",
                                                                                    "Perimeter_top_ZN_1_Wall_South")
        n_wall_bot_1_Tint_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                    "Surface Inside Face Temperature",
                                                                                    "Perimeter_bot_ZN_3_Wall_North")
        n_wall_mid_1_Tint_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                    "Surface Inside Face Temperature",
                                                                                    "Perimeter_mid_ZN_3_Wall_North")
        n_wall_top_1_Tint_handle = parent.ep_api.exchange.get_variable_handle(state,
                                                                                    "Surface Inside Face Temperature",
                                                                                    "Perimeter_top_ZN_3_Wall_North")
        if (oat_sensor_handle == -1 or hvac_heat_rejection_sensor_handle == -1 or zone_flr_area_handle == -1 or
                 zone_indor_temp_sensor_handle == -1 or
                zone_indor_spe_hum_sensor_handle == -1 or
                sens_cool_demand_sensor_handle == -1 or sens_heat_demand_sensor_handle == -1 or
                cool_consumption_sensor_handle == -1 or heat_consumption_sensor_handle == -1 or
                flr_pre1_Text_handle == -1 or flr_pre2_Text_handle == -1 or flr_pre3_Text_handle == -1 or
                flr_pre4_Text_handle == -1 or flr_core_Text_handle == -1 or roof_Text_handle == -1 or
                s_wall_bot_1_Text_handle == -1 or s_wall_mid_1_Text_handle == -1 or s_wall_top_1_Text_handle == -1 or
                n_wall_bot_1_Text_handle == -1 or n_wall_mid_1_Text_handle == -1 or n_wall_top_1_Text_handle == -1 or
                s_wall_bot_1_Solar_handle == -1 or s_wall_mid_1_Solar_handle == -1 or s_wall_top_1_Solar_handle == -1 or
                n_wall_bot_1_Solar_handle == -1 or n_wall_mid_1_Solar_handle == -1 or n_wall_top_1_Solar_handle == -1 or
                flr_pre1_Tint_handle == -1 or flr_pre2_Tint_handle == -1 or flr_pre3_Tint_handle == -1 or
                flr_pre4_Tint_handle == -1 or flr_core_Tint_handle == -1 or roof_Tint_handle == -1 or
                s_wall_bot_1_Tint_handle == -1 or s_wall_mid_1_Tint_handle == -1 or s_wall_top_1_Tint_handle == -1 or
                n_wall_bot_1_Tint_handle == -1 or n_wall_mid_1_Tint_handle == -1 or n_wall_top_1_Tint_handle == -1):
            print('mediumOffice_get_ep_results(): some handle not available')
            os.getpid()
            os.kill(os.getpid(), signal.SIGTERM)

    # get EP results, upload to parent

    global ep_last_call_time_seconds, zone_floor_area_m2

    parent.sem2.acquire()
    zone_floor_area_m2 = parent.ep_api.exchange.get_internal_variable_value(state, zone_flr_area_handle)
    curr_sim_time_in_hours = parent.ep_api.exchange.current_sim_time(state)
    curr_sim_time_in_seconds = curr_sim_time_in_hours * 3600  # Should always accumulate, since system time always advances
    accumulated_time_in_seconds = curr_sim_time_in_seconds - ep_last_call_time_seconds
    ep_last_call_time_seconds = curr_sim_time_in_seconds
    hvac_heat_rejection_J = parent.ep_api.exchange.get_variable_value(state,hvac_heat_rejection_sensor_handle)
    hvac_waste_w_m2 = hvac_heat_rejection_J / accumulated_time_in_seconds / parent.mediumOfficeBld_one_floor_area_m2
    parent.ep_sensWaste_w_m2_per_footprint_area += hvac_waste_w_m2

    time_index_alignment_bool = 1 > abs(curr_sim_time_in_seconds - parent.uwg_time_index_in_seconds)

    if not time_index_alignment_bool:
        parent.sem2.release()
        return

    zone_indor_temp_value = parent.ep_api.exchange.get_variable_value(state, zone_indor_temp_sensor_handle)
    zone_indor_spe_hum_value = parent.ep_api.exchange.get_variable_value(state,
                                                                               zone_indor_spe_hum_sensor_handle)
    sens_cool_demand_w_value = parent.ep_api.exchange.get_variable_value(state,
                                                                               sens_cool_demand_sensor_handle)
    sens_cool_demand_w_m2_value = sens_cool_demand_w_value / zone_floor_area_m2
    sens_heat_demand_w_value = parent.ep_api.exchange.get_variable_value(state,
                                                                               sens_heat_demand_sensor_handle)
    sens_heat_demand_w_m2_value = sens_heat_demand_w_value / zone_floor_area_m2
    cool_consumption_w_value = parent.ep_api.exchange.get_variable_value(state,
                                                                               cool_consumption_sensor_handle)
    cool_consumption_w_m2_value = cool_consumption_w_value / zone_floor_area_m2
    heat_consumption_w_value = parent.ep_api.exchange.get_variable_value(state,
                                                                               heat_consumption_sensor_handle)
    heat_consumption_w_m2_value = heat_consumption_w_value / zone_floor_area_m2

    flr_core_Text_c = parent.ep_api.exchange.get_variable_value(state, flr_core_Text_handle)
    flr_pre1_Text_c = parent.ep_api.exchange.get_variable_value(state, flr_pre1_Text_handle)
    flr_pre2_Text_c = parent.ep_api.exchange.get_variable_value(state, flr_pre2_Text_handle)
    flr_pre3_Text_c = parent.ep_api.exchange.get_variable_value(state, flr_pre3_Text_handle)
    flr_pre4_Text_c = parent.ep_api.exchange.get_variable_value(state, flr_pre4_Text_handle)
    roof_Text_c = parent.ep_api.exchange.get_variable_value(state, roof_Text_handle)

    s_wall_bot_1_Text_c = parent.ep_api.exchange.get_variable_value(state, s_wall_bot_1_Text_handle)
    s_wall_mid_1_Text_c = parent.ep_api.exchange.get_variable_value(state, s_wall_mid_1_Text_handle)
    s_wall_top_1_Text_c = parent.ep_api.exchange.get_variable_value(state, s_wall_top_1_Text_handle)
    n_wall_bot_1_Text_c = parent.ep_api.exchange.get_variable_value(state, n_wall_bot_1_Text_handle)
    n_wall_mid_1_Text_c = parent.ep_api.exchange.get_variable_value(state, n_wall_mid_1_Text_handle)
    n_wall_top_1_Text_c = parent.ep_api.exchange.get_variable_value(state, n_wall_top_1_Text_handle)


    flr_core_Tint_c = parent.ep_api.exchange.get_variable_value(state, flr_core_Tint_handle)
    flr_pre1_Tint_c = parent.ep_api.exchange.get_variable_value(state, flr_pre1_Tint_handle)
    flr_pre2_Tint_c = parent.ep_api.exchange.get_variable_value(state, flr_pre2_Tint_handle)
    flr_pre3_Tint_c = parent.ep_api.exchange.get_variable_value(state, flr_pre3_Tint_handle)
    flr_pre4_Tint_c = parent.ep_api.exchange.get_variable_value(state, flr_pre4_Tint_handle)
    roof_Tint_c = parent.ep_api.exchange.get_variable_value(state, roof_Tint_handle)

    s_wall_bot_1_Tint_c = parent.ep_api.exchange.get_variable_value(state, s_wall_bot_1_Tint_handle)
    s_wall_mid_1_Tint_c = parent.ep_api.exchange.get_variable_value(state, s_wall_mid_1_Tint_handle)
    s_wall_top_1_Tint_c = parent.ep_api.exchange.get_variable_value(state, s_wall_top_1_Tint_handle)
    n_wall_bot_1_Tint_c = parent.ep_api.exchange.get_variable_value(state, n_wall_bot_1_Tint_handle)
    n_wall_mid_1_Tint_c = parent.ep_api.exchange.get_variable_value(state, n_wall_mid_1_Tint_handle)
    n_wall_top_1_Tint_c = parent.ep_api.exchange.get_variable_value(state, n_wall_top_1_Tint_handle)

    s_wall_bot_1_Solar_w_m2 = parent.ep_api.exchange.get_variable_value(state, s_wall_bot_1_Solar_handle)
    s_wall_mid_1_Solar_w_m2 = parent.ep_api.exchange.get_variable_value(state, s_wall_mid_1_Solar_handle)
    s_wall_top_1_Solar_w_m2 = parent.ep_api.exchange.get_variable_value(state, s_wall_top_1_Solar_handle)
    n_wall_bot_1_Solar_w_m2 = parent.ep_api.exchange.get_variable_value(state, n_wall_bot_1_Solar_handle)
    n_wall_mid_1_Solar_w_m2 = parent.ep_api.exchange.get_variable_value(state, n_wall_mid_1_Solar_handle)
    n_wall_top_1_Solar_w_m2 = parent.ep_api.exchange.get_variable_value(state, n_wall_top_1_Solar_handle)


    parent.ep_indoorTemp_C = zone_indor_temp_value
    parent.ep_indoorHum_Ratio = zone_indor_spe_hum_value
    parent.ep_sensCoolDemand_w_m2 = sens_cool_demand_w_m2_value
    parent.ep_sensHeatDemand_w_m2 = sens_heat_demand_w_m2_value
    parent.ep_coolConsump_w_m2 = cool_consumption_w_m2_value
    parent.ep_heatConsump_w_m2 = heat_consumption_w_m2_value

    oat_temp_c = parent.ep_api.exchange.get_variable_value(state, oat_sensor_handle)
    parent.overwriten_time_index = curr_sim_time_in_seconds
    # print(f"EP OAT: {oat_temp_c}")
    parent.ep_oaTemp_C = oat_temp_c

    floor_Text_C = (flr_core_Text_c + flr_pre1_Text_c + flr_pre2_Text_c + flr_pre3_Text_c + flr_pre4_Text_c )/5
    floor_Tint_C = (flr_core_Tint_c + flr_pre1_Tint_c + flr_pre2_Tint_c + flr_pre3_Tint_c + flr_pre4_Tint_c )/5

    parent.ep_floor_Text_K = floor_Text_C + 273.15
    parent.ep_floor_Tint_K = floor_Tint_C + 273.15

    parent.ep_roof_Text_K = roof_Text_c + 273.15
    parent.ep_roof_Tint_K = roof_Tint_c + 273.15

    s_wall_Solar_w_m2 = (s_wall_bot_1_Solar_w_m2 + s_wall_mid_1_Solar_w_m2 + s_wall_top_1_Solar_w_m2)/3
    n_wall_Solar_w_m2 = (n_wall_bot_1_Solar_w_m2 + n_wall_mid_1_Solar_w_m2 + n_wall_top_1_Solar_w_m2)/3

    s_wall_Text_c = (s_wall_bot_1_Text_c + s_wall_mid_1_Text_c + s_wall_top_1_Text_c)/3
    s_wall_Tint_c = (s_wall_bot_1_Tint_c + s_wall_mid_1_Tint_c + s_wall_top_1_Tint_c)/3
    n_wall_Text_c = (n_wall_bot_1_Text_c + n_wall_mid_1_Text_c + n_wall_top_1_Text_c)/3
    n_wall_Tint_c = (n_wall_bot_1_Tint_c + n_wall_mid_1_Tint_c + n_wall_top_1_Tint_c)/3

    if s_wall_Solar_w_m2 > n_wall_Solar_w_m2:
        parent.ep_wallSun_Text_K = s_wall_Text_c + 273.15
        parent.ep_wallSun_Tint_K = s_wall_Tint_c + 273.15
        parent.ep_wallShade_Text_K = n_wall_Text_c + 273.15
        parent.ep_wallShade_Tint_K = n_wall_Tint_c + 273.15
    else:
        parent.ep_wallSun_Text_K = n_wall_Text_c + 273.15
        parent.ep_wallSun_Tint_K = n_wall_Tint_c + 273.15
        parent.ep_wallShade_Text_K = s_wall_Text_c + 273.15
        parent.ep_wallShade_Tint_K = s_wall_Tint_c + 273.15

    parent.sem3.release()