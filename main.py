from threading import Thread
from uwg import _0_parent as parent
from uwg import _1_EP_module as EP_module



if __name__ == '__main__':
    prompt = 'Please enter the case name: [only_uwg.ini]'
    ini_file_name = input(prompt) or 'only_uwg.ini'
    # 1. Read configuration, Inputs/#/*.uwg, *.idf for case study
    parent.init_all(ini_file_name)
    if parent.config['Default']['software'] =='UWG_EP':
        ep_thread = Thread(target=EP_module.run_ep)
        ep_thread.start()
    else:
        uwg_thread = Thread(target=EP_module.run_uwg)
        uwg_thread.start()






