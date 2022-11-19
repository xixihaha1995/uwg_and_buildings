from threading import Thread
from uwg import UWG, _0_parent as parent

def run_uwg():
    model = UWG.from_param_file(param_path=parent.uwg_param_path,
                                epw_path=parent.epw_path,
                                new_epw_dir= parent.output_folder)
    model.generate()
    model.simulate()
    model.write_epw()

if __name__ == '__main__':
    prompt = 'Please enter the case name: [CAPITOUL]'
    ini_file_name = input(prompt) or 'CAPITOUL.ini'
    # 1. Read configuration, Inputs/#/*.uwg, *.idf for case study
    parent.init_all(ini_file_name)
    uwg_thread = Thread(target=run_uwg)
    uwg_thread.start()
    uwg_thread.join()






