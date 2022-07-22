import sys
import os
import inspect
import pprint


currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

import clt_secrets as secrets
import cloudlanguagetools
import cloudlanguagetools.servicemanager

def get_manager():
    manager = cloudlanguagetools.servicemanager.ServiceManager(secrets.config)
    manager.configure()    
    return manager

def get_voice_list_awesometts():
    # for awesometts
    manager = get_manager()
    tts_voice_list = manager.get_tts_voice_list_json()
    # sort by voice_description
    tts_voice_list.sort(key=lambda voice: voice['voice_description'])
    output_filename = 'temp_data_files/voicelist.py'
    #processed_voice_list = [x.python_obj() for x in tts_voice_list]
    with open(output_filename, 'w', encoding='utf8') as f:
        list_formatted = pprint.pformat(tts_voice_list, width=250)
        f.write('VOICE_LIST = ')
        f.write(list_formatted)
        f.close()
    print(f'wrote {output_filename}')    


if __name__ == '__main__':
    get_voice_list_awesometts()