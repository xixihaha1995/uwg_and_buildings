import configparser
import os
from multiprocessing import Process
from threading import Thread
from uwg import _0_parent as parent
from uwg import _1_EP_module as EP_module

def read_ini(config_file_name):
    global config
    config = configparser.ConfigParser()
    project_path = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(project_path, 'UWG_Cases_Inputs')
    config_path = os.path.join(input_folder, ini_file_name)
    config.read(config_path)

def one_ini(sensitivity_file_name):
    read_ini(sensitivity_file_name)
    value_list = [i for i in config['Default']['software'].split(',')]
    print(value_list)

    for value in value_list:
        if value == 'UWG_EP':
            p = Process(target=EP_module.run_ep, args=(config,value))
            p.start()
        else:
            p = Process(target=EP_module.run_uwg, args=(config,value))
            p.start()

if __name__ == '__main__':
    prompt = 'Please enter the case name: [list_software.ini]'
    ini_file_name = input(prompt) or 'list_software.ini'
    # 1. Read configuration, Inputs/#/*.uwg, *.idf for case study
    one_ini(ini_file_name)





