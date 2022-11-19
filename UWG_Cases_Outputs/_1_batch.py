import os, csv, numpy as np, pandas as pd, re
import pathlib
import sqlite3
from shutil import copyfile

from matplotlib import pyplot as plt

def cvrmse(measurements, predictions):
    bias = predictions - measurements
    rmse = np.sqrt(np.mean(bias**2))
    cvrmse = rmse / np.mean(abs(measurements))
    return cvrmse

def get_measurements():
    if os.path.exists('measurements\\' + processed_measurements):
        measurements = pd.read_csv('measurements\\' + processed_measurements, index_col=0, parse_dates=True)
        measurements = measurements[compare_start_time:compare_end_time]
        return measurements
    urban_path = r'measurements\Urban_Pomme_Ori_1_min.csv'
    rural_path = r'measurements\Rural_Ori_1_min.csv'
    urban = pd.read_csv(urban_path, index_col=0, parse_dates=True)
    rural = pd.read_csv(rural_path, index_col=0, parse_dates=True)
    urban_5min = urban.resample('5min').mean()
    rural_5min = rural.resample('5min').mean()
    urban_5min = urban_5min[compare_start_time:compare_end_time]
    rural_5min = rural_5min[compare_start_time:compare_end_time]
    #Air_Temperature_C, tpr_air2m_c13_cal_%60'_celsius, pre_air_c13_cal_%60'_hPa
    # initialize the dataframe, with the same index as rural, and 3 columns
    comparison = pd.DataFrame(index=rural_5min.index, columns=['Urban_DBT_C', 'Rural_DBT_C'])
    comparison['Urban_DBT_C'] = urban_5min['Air_Temperature_C']
    comparison['Rural_DBT_C'] = rural_5min['tpr_air2m_c13_cal_%60\'_celsius']
    comparison['Rural_Pres_Pa'] = rural_5min['pre_air_c13_cal_%60\'_hPa'] * 100

    comparison.to_csv('measurements\\' + processed_measurements)
    return comparison

def read_sql(csv_file):
    csv_name = re.search(r'(.*)\.csv', csv_file).group(1)
    current_path = f'.\\{experiments_folder}'
    sql_path = "foo"
    for folder in os.listdir(current_path):
        if csv_name in folder and 'ep_outputs' in folder:
            sql_path = os.path.join(current_path, folder, 'eplusout.sql')
            break
    if not os.path.exists(sql_path):
        return None
    abs_sql_path = os.path.abspath(sql_path)
    sql_uri = '{}?mode=ro'.format(pathlib.Path(abs_sql_path).as_uri())
    query = f"SELECT * FROM TabularDataWithStrings WHERE ReportName = '{sql_report_name}' AND TableName = '{sql_table_name}'" \
            f" AND RowName = '{sql_row_name}' AND ColumnName = '{sql_col_name}'"
    with sqlite3.connect(sql_uri, uri=True) as con:
        cursor = con.cursor()
        results = cursor.execute(query).fetchall()
        if results:
            pass
        else:
            msg = ("Cannot find the EnergyPlusVersion in the SQL file. "
                   "Please inspect query used:\n{}".format(query))
            raise ValueError(msg)
    regex = r'(\d+\.?\d*)'
    number = float(re.findall(regex, results[0][1])[0])
    return number
def process_one_theme(path):
    #find all csv files in the path, which does not contain 'save'
    csv_files = []
    for file in os.listdir(path):
        if file.endswith('.csv'):
            csv_files.append(file)
    #process each csv file
    comparison = get_measurements()
    cvrmse_dict = {}
    cvrmse_dict['Rural'] = cvrmse(comparison['Urban_DBT_C'], comparison['Rural_DBT_C'])
    sql_dict = {}
    for csv_file_full in csv_files:
        df = pd.read_csv(path + '\\' + csv_file_full, index_col=0, parse_dates=True)
        csv_file = csv_file_full[:-4]
        df = df[compare_start_time:compare_end_time]
        comparison['CanyonReal_' + csv_file] = df['UWG_canTemp_K']- 273.15
        comparison['senWaste_' + csv_file] = df['senWaste']
        cvrmse_dict[csv_file] = cvrmse(comparison['Urban_DBT_C'], comparison['CanyonReal_' + csv_file])

    if os.path.exists(f'{experiments_folder}\\comparison.xlsx'):
        os.remove(f'{experiments_folder}\\comparison.xlsx')
    writer = pd.ExcelWriter(f'{experiments_folder}\\comparison.xlsx')
    comparison.to_excel(writer, 'comparison')
    cvrmse_df = pd.DataFrame.from_dict(cvrmse_dict, orient='index', columns=['cvrmse'])
    cvrmse_df.to_excel(writer, 'cvrmse')
    writer.save()



def plot_one_subfigure(fig, df, ax, category, compare_cols):
    pass
    global legend_bool
    x = pd.to_datetime(df.index)
    ax.set_title(category)
    if category == 'senWaste':
        ax.set_ylabel('W/m2')
    else:
        ax.set_ylabel(' Temperature (C)')
    col_name_fix = category + '_'
    if not legend_bool:
        for col in compare_cols:
            if col == "Rural_DBT_C":
                ax.plot(x, df[col], label=col, color='black', linestyle='--')
            elif col == "Urban_DBT_C":
                ax.plot(x, df[col], label=col, color='black', linestyle=':')
            else:
                ax.plot(x, df[col_name_fix+col], label=col)
        legend_bool = True
        fig.legend(loc='center right', bbox_to_anchor=(1, 0.5), borderaxespad=0., fontsize=plot_fontsize)
    else:
        for col in compare_cols:
            ax.plot(x, df[col_name_fix+col])

def plots():
    #Measurements: Rural, Urban
    #Predictions: VCWG, Bypass-Default, Bypass-Shading, Bypass-ViewFactor, Bypass-Shading_ViewFactor
    # All_subfigures: Canyon, Wallshade, Walllit, Roof, Wastez
    global plot_fontsize, legend_bool
    legend_bool = False
    data = pd.read_excel(f'{experiments_folder}\\comparison.xlsx', sheet_name='comparison', index_col=0, parse_dates=True)
    plot_fontsize = 6
    measurements_cols = ['Rural_DBT_C','Urban_DBT_C']

    predictions_cols = []
    for file in os.listdir(f'.\\{experiments_folder}'):
        if file.endswith('.csv'):
            #remove the '.csv' in the file name
            predictions_cols.append(file.replace('.csv', ''))
    all_subfigures_cols = ['CanyonReal','senWaste']
    fig, axes = plt.subplots(2, 1, figsize=(12, 4), sharex=True)
    fig.subplots_adjust(right=0.76)
    for ax in axes:
        ax.tick_params(axis='x', labelsize=plot_fontsize)
    for i, sub_fig in enumerate(all_subfigures_cols):
        if sub_fig == 'CanyonReal':
            compare_cols = measurements_cols + predictions_cols
        else:
            compare_cols = predictions_cols
        plot_one_subfigure(fig, data, axes[i],sub_fig, compare_cols)
    plt.show()

def main():
    global processed_measurements, compare_start_time, compare_end_time, sql_report_name, sql_table_name, sql_row_name, sql_col_name
    global experiments_folder
    experiments_folder = 'Comparison_UWG_Bypass'
    sql_report_name = 'AnnualBuildingUtilityPerformanceSummary'
    sql_table_name = 'Site and Source Energy'
    sql_row_name = 'Total Site Energy'
    sql_col_name = 'Total Energy'
    compare_start_time = '2004-06-01 00:10:00'
    compare_end_time = '2004-06-30 22:55:00'
    processed_measurements = 'CAPITOUL_measurements_' + pd.to_datetime(compare_start_time).strftime('%Y-%m-%d') \
                             + '_to_' + pd.to_datetime(compare_end_time).strftime('%Y-%m-%d') + '.csv'
    # Copy r'.\offline_saving\CAPITOUL\albedo\positive0.25.csv' to 'VCWG.csv'
    # copyfile(r'.\offline_saving\CAPITOUL\albedo\positive0.25.csv', f'.\\{experiments_folder}\\VCWG.csv')
    process_one_theme(experiments_folder)
    plots()
if __name__ == '__main__':
    main()
