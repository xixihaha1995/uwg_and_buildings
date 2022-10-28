import numpy as np, pandas as pd, os

def init_saving_data():
    global saving_data
    saving_data = {}
    saving_data['debugging_canyon'] = []

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
        df.columns = ['UWG_CanTemp_C']
    else:
        df.columns = [f'(m) {file_name}_' + str(0.5 + i) for i in range(len(df.columns))]
    df = add_date_index(df, start_time, time_interval_sec)
    # save to excel, if non-exist, create one
    if not os.path.exists(vcwg_ep_saving_path):
        os.makedirs(vcwg_ep_saving_path)
    df.to_excel(os.path.join(vcwg_ep_saving_path, f'{case_name}_{file_name}.xlsx'))