from threading import Thread
from uwg import _0_parent as parent
from uwg import _1_EP_module as EP_module



if __name__ == '__main__':
    prompt = 'Please enter the case name: [CAPITOUL.ini]'
    ini_file_name = input(prompt) or 'CAPITOUL.ini'
    # 1. Read configuration, Inputs/#/*.uwg, *.idf for case study
    parent.init_all(ini_file_name)
    uwg_thread = Thread(target=EP_module.run_ep)
    uwg_thread.start()






