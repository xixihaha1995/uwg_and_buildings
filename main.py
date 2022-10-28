from threading import Thread
from uwg import UWG, _0_parent as parent

def run_uwg():
    model = UWG.from_param_file(param_path=parent.uwg_param_path,
                                epw_path=parent.epw_path,
                                new_epw_dir= parent.output_folder)
    model.generate()
    model.simulate()
    model.write_epw()

def save_data():
    data_name_lst = ['debugging_canyon', 'can_Averaged_temp_k_specHum_ratio_press_pa', 's_wall_Text_K_n_wall_Text_K']
    start_time = parent.config['Default']['start_time']
    for data_name in data_name_lst:
        parent.save_data_to_csv(parent.saving_data, data_name, parent.config['Default']['saving_case_name'],
                                start_time, 300, parent.output_folder)

if __name__ == '__main__':
    prompt = 'Please enter the case name: [CAPITOUL]'
    case_name = input(prompt) or 'CAPITOUL'
    # 1. Read configuration, Inputs/#/*.uwg, *.idf for case study
    parent.init_all(case_name)
    uwg_thread = Thread(target=run_uwg)
    uwg_thread.daemon = True
    uwg_thread.start()
    uwg_thread.join()
    save_data()






