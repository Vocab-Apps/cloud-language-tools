import json
import requests

import cloudlanguagetools.service
import cloudlanguagetools.constants
import cloudlanguagetools.ttsvoice
import cloudlanguagetools.translationlanguage
import cloudlanguagetools.transliterationlanguage
import cloudlanguagetools.errors

def get_translation_language_enum(language_id):
    # print(f'language_id: {language_id}')
    watson_language_id_map = {
        'fr-CA': 'fr_ca',
        'id': 'id_',
        'pt': 'pt_pt',
        'sr': 'sr_cyrl',
        'zh':'zh_cn',
        'zh-TW': 'zh_tw'

    }
    if language_id in watson_language_id_map:
        language_id = watson_language_id_map[language_id]
    return cloudlanguagetools.constants.Language[language_id]

def get_audio_language_enum(voice_language):
    watson_audio_id_map = {
        'ar-MS': 'ar_XA'
    }
    language_enum_name = voice_language.replace('-', '_')
    if voice_language in watson_audio_id_map:
        language_enum_name = watson_audio_id_map[voice_language]
    return cloudlanguagetools.constants.AudioLanguage[language_enum_name]

class WatsonTranslationLanguage(cloudlanguagetools.translationlanguage.TranslationLanguage):
    def __init__(self, language_id):
        self.service = cloudlanguagetools.constants.Service.Watson
        self.language_id = language_id
        self.language = get_translation_language_enum(language_id)

    def get_language_id(self):
        return self.language_id

class WatsonVoice(cloudlanguagetools.ttsvoice.TtsVoice):
    def __init__(self, voice_data):
        self.service = cloudlanguagetools.constants.Service.Watson
        self.audio_language = get_audio_language_enum(voice_data['language'])
        self.name = voice_data['name']
        self.description = voice_data['description']
        self.gender = cloudlanguagetools.constants.Gender[voice_data['gender'].capitalize()]


    def get_voice_key(self):
        return {
            'name': self.name
        }

    def get_voice_shortname(self):
        return self.description.split(':')[0]

    def get_options(self):
        return {}

class WatsonService(cloudlanguagetools.service.Service):
    def __init__(self):
        pass

    def configure(self, translator_key, translator_url, speech_key, speech_url):
        self.translator_key = translator_key
        self.translator_url = translator_url
        self.speech_key = speech_key
        self.speech_url = speech_url
    
    def get_tts_voice_list(self):
        return []

    def get_translation_languages(self):
        response = requests.get(self.translator_url + '/v3/languages?version=2018-05-01', auth=('apikey', self.translator_key))
        return response.json()

    def get_translation_language_list(self):
        language_list = self.get_translation_languages()['languages']
        result = []
        # print(language_list)
        for entry in language_list:
            if entry['supported_as_source'] == True and entry['supported_as_target'] == True:
                # print(entry)
                language_id = entry['language']
                result.append(WatsonTranslationLanguage(language_id))
        return result        

    def list_voices(self):
        response = requests.get(self.speech_url + '/v1/voices', auth=('apikey', self.speech_key))
        data = response.json()
        return data['voices']

    def get_tts_voice_list(self):
        result = []

        voice_list = self.list_voices()
        for voice in voice_list:
            result.append(WatsonVoice(voice))

        return result

    def get_transliteration_language_list(self):
        return []

    def get_translation(self, text, from_language_key, to_language_key):
        body = {
            'text': text,
            'source': from_language_key,
            'target': to_language_key
        }
        response = requests.post(self.translator_url + '/v3/translate?version=2018-05-01', auth=('apikey', self.translator_key), json=body)

        if response.status_code == 200:
            # {'translations': [{'translation': 'Le coût est très bas.'}], 'word_count': 2, 'character_count': 4}
            data = response.json()
            return data['translations'][0]['translation']

        error_message = error_message = f'Watson: could not translate text [{text}] from {from_language_key} to {to_language_key} ({response.json()})'
        raise cloudlanguagetools.errors.RequestError(error_message)