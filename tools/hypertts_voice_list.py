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
    manager = cloudlanguagetools.servicemanager.ServiceManager()
    manager.configure_default()
    return manager

def process_voice(voice):
    return {
        'language': voice['audio_language_code'],
        'gender': voice['gender'],
        'service': voice['service'],
        'name': voice['voice_name'],
        'key': voice['voice_key'],
        'options': voice['options']
    }

def get_voice_list_hypertts():
    # for hypertts
    manager = get_manager()
    tts_voice_list = manager.get_tts_voice_list_json()
    # sort by voice_description
    tts_voice_list.sort(key=lambda voice: voice['voice_description'])
    tts_voice_list = [process_voice(voice) for voice in tts_voice_list]
    output_filename = 'temp_data_files/hypertts_voicelist.py'
    with open(output_filename, 'w', encoding='utf8') as f:
        list_formatted = pprint.pformat(tts_voice_list, width=250)
        f.write('VOICE_LIST = ')
        f.write(list_formatted)
        f.close()
    print(f'wrote {output_filename}')    


if __name__ == '__main__':
    get_voice_list_hypertts()