import os
import sys
import json
import tempfile
import shutil 
import logging
import boto3
import pandas
import clt_secrets as secrets
import random
import urllib.parse
import cloudlanguagetools
import cloudlanguagetools.constants
import cloudlanguagetools.languages
import cloudlanguagetools.servicemanager
import webflow_cms_utils


def get_manager():
    manager = cloudlanguagetools.servicemanager.ServiceManager(secrets.config)
    manager.configure()    
    return manager

class SoundSampleGeneration():
    def __init__(self):
        self.webflow_utils = webflow_cms_utils.WebflowCMSUtils()

    def generate_audio_language_list(self, language_set):
        records = []
        for language in cloudlanguagetools.languages.Language:
            if language in language_set:
                records.append({
                    'id': language.name,
                    'name': language.lang_name
                })
        data_df = pandas.DataFrame(records)
        filename = 'temp_data_files/languages_with_audio.csv'
        data_df.to_csv(filename)
        logging.info(f'wrote {filename}')
        return records

    def generate_sound_sample(self, language_set):
        logging.info(f'generating sound samples')
        session = boto3.session.Session()
        client = session.client('s3',
                                region_name=os.environ['SPACE_REGION'],
                                endpoint_url=os.environ['SPACE_ENDPOINT_URL'],
                                aws_access_key_id=os.environ['SPACE_KEY'],
                                aws_secret_access_key=os.environ['SPACE_SECRET'])

        manager = get_manager()
        voice_list = manager.get_tts_voice_list()
        translation_language_list = manager.get_translation_language_list()
        source_text = 'How many languages can you speak ? The more the better !'
        source_language = cloudlanguagetools.languages.Language.en
        source_translation_option = [x for x in translation_language_list if x.language == source_language][0]
        translation_service = 'Azure'
        translations = {}

        entries = []

        # testing only (restrict to N voices)
        # voice_list = random.sample(voice_list, 3)
        # voice_list = voice_list[0:5]

        for voice in voice_list:
            try:
                if voice.service == cloudlanguagetools.constants.Service.Forvo:
                    # skip forvo service
                    continue

                audio_language = voice.audio_language
                target_language = audio_language.lang

                dir_path = f'sound_samples/{target_language.lang_name}'
                file_name = f'{voice.get_voice_description()}.mp3'
                final_path = os.path.join(dir_path, file_name)

                if not os.path.isfile(final_path):
                    logging.info(f'{final_path} not present, requesting')
                    # print(f'source_language: {source_language} target_language: {target_language}')
                    if target_language == source_language:
                        # don't translate
                        translation = source_text
                    elif target_language not in translations:
                        logging.info(f'need to translate into {target_language}')
                        # translate
                        # get azure translation service
                        target_translation_option = [x for x in translation_language_list if x.language == target_language][0]
                        # print(source_translation_option.json_obj())
                        # print(target_translation_option.json_obj())
                        translation = manager.get_translation(source_text, translation_service, source_translation_option.get_language_id(), target_translation_option.get_language_id())
                        translations[target_language] = translation
                        # print(translation)
                    else:
                        translation = translations[target_language]
                    logging.info(f'translation into {target_language}: {translation}')
                    # print(voice)

                    # generate audio
                    audio_temp_file = manager.get_tts_audio(translation, voice.service.name, voice.get_voice_key(), {})

                    os.makedirs(dir_path, exist_ok=True)

                    shutil.copyfile(audio_temp_file.name, final_path)
                    logging.info(f'copied into {final_path}')

                # upload to the space
                s3_path = f'{target_language.lang_name}/{voice.get_voice_description()}.mp3'
                client.upload_file(final_path, 'cloud-language-tools-samples', s3_path, ExtraArgs={'ACL':'public-read'})
                # urllib.parse.urlencode(f)
                public_url = f'https://sound-samples.anki.study/{urllib.parse.quote(s3_path)}'

                language_set[audio_language.lang] = True

                voice_entry = {
                    'language': audio_language.lang.name,
                    'language_name': audio_language.lang.lang_name,
                    'voice_description': voice.get_voice_description(),
                    'public_url': public_url
                }

                print(voice_entry)
                entries.append(voice_entry)
            
            except:
                e = sys.exc_info()[0]
                logging.exception(e)

        # write out voice entries as CSV
        voices_df = pandas.DataFrame(entries)
        filename = f'temp_data_files/voicelist.csv'
        voices_df.to_csv(filename)
        logging.info(f'wrote {filename}')

        return entries

    def upload_language_items(self, language_entries, webflow_language_list):
        logging.info(f'uploading languages')
        language_exists = {}
        for language in webflow_language_list:
            language_exists[language['slug']] = True
        for entry in language_entries:
            if not language_exists.get(entry['id'], False):
                data = {
                    'name': entry['name'],
                    'slug': entry['id'],
                    '_archived': False,
                    '_draft': False
                }
                self.webflow_utils.add_language(data)

    def upload_voice_entries(self, voice_entries, webflow_language_list, webflow_voice_list):
        logging.info(f'uploading voices')
        language_to_id_map = {}
        for language in webflow_language_list:
            language_to_id_map[language['slug']] = language['_id']
        voice_exists_map = {}
        for webflow_voice in webflow_voice_list:
            voice_exists_map[webflow_voice['name']] = True
        for entry in voice_entries:
            if not voice_exists_map.get(entry['voice_description'], False):
                data = {
                    'name': entry['voice_description'],
                    'audio-language': language_to_id_map[entry['language']],
                    'sample-url': entry['public_url'],
                    '_archived': False,
                    '_draft': False
                }
                self.webflow_utils.add_voice(data)

    def update_voices(self):
        language_set = {}
        voice_entries = self.generate_sound_sample(language_set)
        language_entries = self.generate_audio_language_list(language_set)
        webflow_language_list = self.webflow_utils.list_languages()
        self.upload_language_items(language_entries, webflow_language_list)
        webflow_language_list = self.webflow_utils.list_languages()
        webflow_voice_list = self.webflow_utils.list_voices()
        self.upload_voice_entries(voice_entries, webflow_language_list, webflow_voice_list)

        



if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', 
                        datefmt='%Y%m%d-%H:%M:%S',
                        level=logging.INFO)    
    generation = SoundSampleGeneration()
    generation.update_voices()
