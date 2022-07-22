import os
import sys
import logging
import pprint
import base64
import json
import tempfile
import shutil 
import unittest
import pydub
import pydub.playback
import epitran
import pandas
import requests
import re
import clt_secrets as secrets
import redisdb
import cloudlanguagetools
import cloudlanguagetools.servicemanager


def get_manager():
    manager = cloudlanguagetools.servicemanager.ServiceManager(secrets.config)
    manager.configure()    
    return manager


def test_azure_audio():
    manager = get_manager()

    service = 'Azure'
    text = """<mstts:silence type="Sentenceboundary" value="200ms"/>My mother is ill. She's in bed."""
    voice_key = {
        'name': 'Microsoft Server Speech Text to Speech Voice (en-US, AriaNeural)' 
    }

    result = manager.get_tts_audio(text, service, voice_key, {})
    permanent_file_name = 'azure_output.mp3'
    shutil.copyfile(result.name, permanent_file_name)
    print(f'tts result: {permanent_file_name}')

def generate_video_audio():
    manager = get_manager()

    service = 'Azure'
    text = """Language Tools is an new Anki add-on designed to help you build language learning flashcards.
    It understands which languages you're studying and provides intelligent defaults. You can choose your favorite text to speech voice for each language,
    from a list of over 600 premium voices which cover more than 50 languages. <break time="2s"/> Once you're done, you can try translation. Language Tools offers high quality translation
    from neural network services such as Google, Microsoft, Amazon. It's really easy to use ! <break time="3s"/> You can also add text to speech audio to many cards at once. 
    Just pick the source field, the target field, and click apply. Your audio is now getting added. <break time="2s"/> You will see the sound tag in your notes, and you will hear the sounds when reviewing.
    <break time="3s"/>
    Now, let's add a transliteration. This means going from one alphabet to another, for example for Chinese or Japanese to Latin alphabet. In this case, we're adding French IPA, or international phonetic alphabet pronunciations.
    <break time="2s"/>
    And now, let's add some new cards. All of the transformation you've added previously are memorized, and they'll be added to new cards too. Notice how the French to English translation, the sound, and the IPA pronunciation is added automatically.
    This is a huge time saver for people who create a lot of flashcards. You'll have more time to review your cards instead of spending most of your time creating them. No more excuses now !
    <break time="3s"/>
    You can see which transformations you've setup for your decks and remove them if needed.
    <break time="2s"/>
    And you can add those transformations all at once. That's right, add audio text to speech, translation and transliteration in one step. Again, a huge time saver for those who create a lot of cards
    Are you interested in trying it out ? Download Language Tools for Anki using the link below.
    <break time="1s"/>
    By the way, this is Microsoft Azure voice Aria, available on Language Tools.
    """

    text = """In this tutorial, we'll see how to add audio to your flashcards using batch generation. This means we will create some audio files which will be stored in your collection and will be played back when you review your cards.
    Let's first make sure our installation of Awesome TTS is working. Go to the Awesome TTS configuration, advanced, managed presets. Let's pick the Microsoft Azure service. Pick a french voice, type in some French text, then hit preview.
    <break time="1s"/>
    Now, let's go to the card browser. Select your deck, then select a few notes. Go to the Awesome TTS menu, then select add audio to selected notes.
    Make sure to pick a French voice from the Azure service. The source field should be front, that's the one which contains french text. The destination field should also be front, and the sound tag will be added alongside the french text.
    Note that we have the append option checked, as well as removing existing sound tag.
    Press Generate to start creating the audio files. 
    Wait a little bit, it should be done soon.
    Let's look at our notes. You can see we now have a sound tag on the front field, after the french text. Let's hit preview for this note. The sound plays automatically, and we can play again using this play icon.
    The other cards should also have a sound tag.
    By the way, this is the Aria voice, available in Awesome TTS.
    """    

    text = """etes vous vraiment malade ?"""

    voice_key = {
        'name': 'Microsoft Server Speech Text to Speech Voice (en-US, AriaNeural)' 
    }

    voice_key = {
            "name": "Microsoft Server Speech Text to Speech Voice (fr-FR, HenriNeural)"
    }

    result = manager.get_tts_audio(text, service, voice_key, {})
    permanent_file_name = 'languagetools_video.mp3'
    permanent_file_name = 'french.mp3'
    shutil.copyfile(result.name, permanent_file_name)
    print(f'tts result: {permanent_file_name}')


def test_google_audio():
    manager = get_manager()

    service = 'Google'
    text = 'hello world test 1'

    voice_key = {
        'language_code': "en-US",
        'name': "en-US-Standard-C",
        'ssml_gender': "FEMALE"
    }    

    result = manager.get_tts_audio(text, service, voice_key, {})
    permanent_file_name = 'google_output.mp3'
    shutil.copyfile(result.name, permanent_file_name)
    print(f'tts result: {permanent_file_name}')


def play_google_audio():
    manager = get_manager()

    service = 'Google'
    text = 'hello<break time="2s"/>world test 1'

    voice_key = {
        'language_code': "en-GB",
        'name': "en-GB-Wavenet-A",
        'ssml_gender': "FEMALE"
    }    

    options = {'speaking_rate': 1.5} # 0.25 to 4.0
    options = {'pitch': 5} # -20.0 to 20.0
    options = {}
    result = manager.get_tts_audio(text, service, voice_key, options)
    filename = result.name
    music = pydub.AudioSegment.from_mp3(filename)
    pydub.playback.play(music)    

def play_azure_audio():
    manager = get_manager()

    service = 'Azure'
    text = 'hello<break time="2s"/>world test 1'

    voice_key = {
        "name": "Microsoft Server Speech Text to Speech Voice (en-GB, MiaNeural)"
    }
    voice_key = {
        'name': 'Microsoft Server Speech Text to Speech Voice (en-US, AriaNeural)' 
    }    

    #options = {'speaking_rate': 1.5}
    #options = {'pitch': 5}
    # options = {'pitch': 100} # -100 to +100?
    # options = {'rate': 3.0} # 0.5 to 3 ?
    options = {}
    result = manager.get_tts_audio(text, service, voice_key, options)
    filename = result.name
    music = pydub.AudioSegment.from_mp3(filename)
    pydub.playback.play(music)    

def get_watson_voice_list():
    manager = get_manager()
    #tts_voice_list_json = manager.get_tts_voice_list_json()
    # print(tts_voice_list_json)    
    data = manager.services[cloudlanguagetools.constants.Service.Watson.name].list_voices()
    output_filename = 'temp_data_files/watson_voicelist.json'
    with open(output_filename, 'w', encoding='utf8') as f:
        f.write(json.dumps(data, indent=4, sort_keys=True, ensure_ascii=False))
        f.close()
    print(f'wrote {output_filename}')

def get_amazon_voice_list():
    manager = get_manager()
    #tts_voice_list_json = manager.get_tts_voice_list_json()
    # print(tts_voice_list_json)    
    manager.services[cloudlanguagetools.constants.Service.Amazon.name].get_tts_voice_list()

def get_forvo_voice_list():
    manager = get_manager()
    #tts_voice_list_json = manager.get_tts_voice_list_json()
    # print(tts_voice_list_json)    
    manager.services[cloudlanguagetools.constants.Service.Forvo.name].get_tts_voice_list()

def get_amazon_voice_list_awesometts():
    manager = get_manager()
    #tts_voice_list_json = manager.get_tts_voice_list_json()
    # print(tts_voice_list_json)    
    voice_list = manager.services[cloudlanguagetools.constants.Service.Amazon.name].get_tts_voice_list()
    # print(voice_list)
    for voice in voice_list:
        code = f"AmazonVoice(Language.{voice.audio_language.name}, Gender.{voice.gender.name}, '{voice.name}', '{voice.voice_id}', '{voice.engine}'),"
        print(code)

def print_all_languages():
    languages = [language for language in cloudlanguagetools.languages.Language]
    languages = sorted(languages, key = lambda x: x.lang_name)
    for entry in languages:
        print(f'{entry.name},{entry.lang_name}')

def print_all_audio_languages():
    languages = [language for language in cloudlanguagetools.languages.AudioLanguage]
    languages = sorted(languages, key = lambda x: x.audio_lang_name)
    for entry in languages:
        print(f'{entry.lang.name},{entry.name},{entry.audio_lang_name}')


def get_voice_list():
    manager = get_manager()
    tts_voice_list_json = manager.get_tts_voice_list_json()
    # print(tts_voice_list_json)    
    output_filename = 'temp_data_files/voicelist.json'
    with open(output_filename, 'w', encoding='utf8') as f:
        f.write(json.dumps(tts_voice_list_json, indent=4, sort_keys=True, ensure_ascii=False))
        f.close()
    print(f'wrote {output_filename}')

def get_voice_list_awesometts():
    # for awesometts
    manager = get_manager()
    tts_voice_list = manager.get_tts_voice_list_json()
    output_filename = 'temp_data_files/voicelist.py'
    #processed_voice_list = [x.python_obj() for x in tts_voice_list]
    with open(output_filename, 'w', encoding='utf8') as f:
        list_formatted = pprint.pformat(tts_voice_list, width=250)
        f.write('VOICE_LIST = ')
        f.write(list_formatted)
        f.close()
    print(f'wrote {output_filename}')    

def get_translation_language_list():
    manager = get_manager()
    language_list_json = manager.get_translation_language_list_json()
    #print(tts_voice_list_json)    
    output_filename = 'temp_data_files/translation_language_list.json'
    with open(output_filename, 'w') as f:
        f.write(json.dumps(language_list_json, indent=4, sort_keys=True))
        f.close()
    print(f'wrote {output_filename}')

def get_transliteration_language_list():
    manager = get_manager()
    language_list_json = manager.get_transliteration_language_list_json()
    #print(tts_voice_list_json)    
    output_filename = 'temp_data_files/transliteration_language_list.json'
    with open(output_filename, 'w') as f:
        f.write(json.dumps(language_list_json, indent=4, sort_keys=True))
        f.close()
    print(f'wrote {output_filename}')

def get_azure_translation_languages():
    manager = get_manager()
    data = manager.services[cloudlanguagetools.constants.Service.Azure.name].get_translation_languages()
    # print(data)
    output_filename = 'azure_translation_languages.json'
    with open(output_filename, 'w') as f:
        f.write(json.dumps(data, sort_keys=True, indent=4, ensure_ascii=False, separators=(',', ': ')))
        f.close()
    print(f'wrote output to {output_filename}')


def get_google_translation_languages():
    manager = get_manager()
    data = manager.services[cloudlanguagetools.constants.Service.Google.name].get_translation_languages()
    # print(data)
    output_filename = 'temp_data_files/google_translation_languages.json'
    with open(output_filename, 'w') as f:
        f.write(json.dumps(data, sort_keys=True, indent=4, ensure_ascii=False, separators=(',', ': ')))
        f.close()
    print(f'wrote output to {output_filename}')    


def get_watson_translation_languages():
    manager = get_manager()
    data = manager.services[cloudlanguagetools.constants.Service.Watson.name].get_translation_languages()
    # data = manager.services[cloudlanguagetools.constants.Service.Google.name].get_translation_language_list()
    # print(data)
    output_filename = 'temp_data_files/watson_translation_languages.json'
    with open(output_filename, 'w') as f:
        f.write(json.dumps(data, sort_keys=True, indent=4, ensure_ascii=False, separators=(',', ': ')))
        f.close()
    print(f'wrote output to {output_filename}')        

def output_languages_enum():
    manager = get_manager()
    data_google = manager.services[cloudlanguagetools.constants.Service.Google.name].get_translation_languages()
    data_azure = manager.services[cloudlanguagetools.constants.Service.Azure.name].get_translation_languages()

    language_map = {}

    for entry in data_google:
        language_map[entry['language']] = entry['name']

    for key, data in data_azure['translation'].items():
        language_map[key] = data['name']

    output_filename = 'languages_enum.txt'
    with open(output_filename, 'w') as f:
        for key, name in language_map.items():
            output = f"{key} = (\"{name}\")\n"
            f.write(output)
        f.close()
    print(f'wrote output to {output_filename}')    

def output_language_audio_mapping():
    language_map = {}
    for audio_language in cloudlanguagetools.languages.AudioLanguage:
        language = audio_language.lang
        if language not in language_map:
            language_map[language] = []
        language_map[language].append(audio_language)

    output_filename = 'temp_data_files/output_language_audio_mapping.txt'
    with open(output_filename, 'w') as f:
        for key, data in language_map.items():
            f.write(f'language: {key} ({key.lang_name})\n')
            for item in data:
                f.write(f'    audio language: {item} ({item.audio_lang_name})\n')
        f.close()
                

def detect_language():
    input_text = 'ผมจะไปประเทศไทยพรุ่งนี้ครับ'
    manager = get_manager()
    #manager.services[cloudlanguagetools.constants.Service.Azure.name].detect_language(input_text)
    manager.services[cloudlanguagetools.constants.Service.Google.name].detect_language(input_text)

def translate_google():
    text = 'Bonjour Madame'
    manager = get_manager()
    translated_text = manager.get_translation(text, 'Google', 'fr', 'cs')
    print(translated_text)

def translate_azure():
    text = 'Je suis un ours.'
    manager = get_manager()
    translated_text = manager.get_translation(text, 'Azure', 'fr', 'cs')
    print(translated_text)    

def transliterate_azure():
    text = 'Je suis un ours.'
    manager = get_manager()
    service = manager.services[cloudlanguagetools.constants.Service.Azure.name]
    test_thai = True
    text = 'ผมจะไปประเทศไทยพรุ่งนี้ครับ'
    text = 'ผม | จะ | ไป | ประเทศไทย | พรุ่ง | นี้ | ครับ'
    language_key = 'th'
    from_script = 'Thai'
    to_script = 'Latn'
    result = service.transliteration(text, language_key, from_script, to_script)
    print(result)



def dictionary_lookup_azure():
    text = '出事'
    manager = get_manager()
    manager.services[cloudlanguagetools.constants.Service.Azure.name].dictionary_lookup(text, 'zh-Hans', 'en')

def dictionary_examples_azure():
    text = '饥不择食'
    translated_text = 'beggars can\'t be choosers'
    manager = get_manager()
    manager.services[cloudlanguagetools.constants.Service.Azure.name].dictionary_examples(text, translated_text, 'en', 'zh-Hans')    

def end_to_end_test():
    field1_list = [
        'Pouvez-vous me faire le change ?',
        'Pouvez-vous débarrasser la table, s\'il vous plaît?',
        'Je ne suis pas intéressé.'
    ]    
    field2_list = [
        'Can you change money for me?',
        'Can you please clear the plates?',
        'I\'m not interested.'
    ]
    # step 1: recognize languages
    manager = get_manager()
    language1 = manager.detect_language(field1_list)
    print(language1)
    language2 = manager.detect_language(field2_list)
    print(language2)

    # step2 retrieve list of languages supported for translation
    translation_language_list = manager.get_translation_language_list_json()

    service_wanted = 'Google'
    languages_service = [x for x in translation_language_list if x['service'] == service_wanted]

    field1_language_id = [x for x in languages_service if x['language_code'] == language1.name][0]['language_id']
    field2_language_id = [x for x in languages_service if x['language_code'] == language2.name][0]['language_id']

    target_language_enum = cloudlanguagetools.languages.Language.cs

    target_language_id = [x for x in languages_service if x['language_code'] == target_language_enum.name][0]['language_id']

    for text in field1_list:
        translated_text = manager.get_translation(text, service_wanted, field1_language_id, target_language_id)
        print(f'source: {text} translated: {translated_text}')
    

def cereproc_authentication():
    url = 'https://api.cerevoice.com/v2/auth'
    username = os.environ['CEREPROC_USERNAME']
    password = os.environ['CEREPROC_PASSWORD']
    combined = f'{username}:{password}'
    auth_string = base64.b64encode(combined.encode('utf-8')).decode('utf-8')
    headers = {'authorization': f'Basic {auth_string}'}

    response = requests.get(url, headers=headers)

    print(response.json())

    access_token = response.json()['access_token']

    voices_url = 'https://api.cerevoice.com/v2/voices'

    response = requests.get(voices_url, headers={'Authorization': f'Bearer {access_token}'})
    print(response.json())


def cereproc_tts_voice_list():
    manager = get_manager()
    voice_list = manager.services[cloudlanguagetools.constants.Service.CereProc.name].get_tts_voice_list()
    print(f'voices: {len(voice_list)}')


def test_epitran():
    epi = epitran.Epitran('eng-Latn')
    result = epi.transliterate('Hello my friends')
    print(result)


def create_epitran_mappings():
    language_map = {'aar-Latn': 'Afar',
        'amh-Ethi': 'Amharic',
        'ara-Arab': 'Arabic',
        'aze-Cyrl': 'Azerbaijani',
        'aze-Latn': 'Azerbaijani',
        'ben-Beng': 'Bengali',
        'ben-Beng-red': 'Bengali',
        'cat-Latn': 'Catalan',
        'ceb-Latn': 'Cebuano',
        'ckb-Arab': 'Sorani',
        'deu-Latn': 'German',
        'deu-Latn-np': 'German',
        'deu-Latn-nar': 'German',
        'eng-Latn': 'English',
        'fas-Arab': 'Farsi',
        'fra-Latn': 'French',
        'fra-Latn-np': 'French',
        'hau-Latn': 'Hausa',
        'hin-Deva': 'Hindi',
        'hun-Latn': 'Hungarian',
        'ilo-Latn': 'Ilocano',
        'ind-Latn': 'Indonesian',
        'ita-Latn': 'Italian',
        'jav-Latn': 'Javanese',
        'kaz-Cyrl': 'Kazakh',
        'kaz-Latn': 'Kazakh',
        'kin-Latn': 'Kinyarwanda',
        'kir-Arab': 'Kyrgyz',
        'kir-Cyrl': 'Kyrgyz',
        'kir-Latn': 'Kyrgyz',
        'kmr-Latn': 'Kurmanji',
        'lao-Laoo': 'Lao',
        'mar-Deva': 'Marathi',
        'mlt-Latn': 'Maltese',
        'mya-Mymr': 'Burmese',
        'msa-Latn': 'Malay',
        'nld-Latn': 'Dutch',
        'nya-Latn': 'Chichewa',
        'orm-Latn': 'Oromo',
        'pan-Guru': 'Punjabi',
        'pol-Latn': 'Polish',
        'por-Latn': 'Portuguese',
        'ron-Latn': 'Romanian',
        'rus-Cyrl': 'Russian',
        'sna-Latn': 'Shona',
        'som-Latn': 'Somali',
        'spa-Latn': 'Spanish',
        'swa-Latn': 'Swahili',
        'swe-Latn': 'Swedish',
        'tam-Taml': 'Tamil',
        'tel-Telu': 'Telugu',
        'tgk-Cyrl': 'Tajik',
        'tgl-Latn': 'Tagalog',
        'tha-Thai': 'Thai',
        'tir-Ethi': 'Tigrinya',
        'tpi-Latn': 'Tok Pisin',
        'tuk-Cyrl': 'Turkmen',
        'tuk-Latn': 'Turkmen',
        'tur-Latn': 'Turkish',
        'ukr-Cyrl': 'Ukrainian',
        'uig-Arab': 'Uyghur',
        'uzb-Cyrl': 'Uzbek',
        'uzb-Latn': 'Uzbek',
        'vie-Latn': 'Vietnamese',
        'xho-Latn': 'Xhosa',
        'yor-Latn': 'Yoruba',
        'zul-Latn': 'Zulu'}
    # print(language_map)

    clt_reverse_language_map = {}
    for language in cloudlanguagetools.languages.Language:
        clt_reverse_language_map[language.lang_name] = language

    print(clt_reverse_language_map)

    for language_key, language_name in language_map.items():
        if language_name in clt_reverse_language_map:
            # print(f'found: {language_name}')
            language_enum = clt_reverse_language_map[language_name]
            assignment = f"""EpitranTransliterationLanguage(cloudlanguagetools.constants.{language_enum}, '{language_key}'),"""
            print(assignment)

def test_debounce():
    import convertkit
    convertkit_client = convertkit.ConvertKit()
    # email = '4wstpt6hpu@cloud-mail.top'
    email = sys.argv[1]
    logging.info(f'calling debounce.io api on {email}')
    valid, reason = convertkit_client.check_email_valid(email)
    print(f'valid: {valid} reason: {reason}')

def load_vocalware_voices():
    f = open('temp_data_files/vocalware_languages.json')
    languages_content = f.read()
    languages = json.loads(languages_content)
    # pprint.pprint(languages)

    # build map of language name to enum
    language_enum_map = {}
    for language in cloudlanguagetools.languages.Language:
        language_enum_map[language.lang_name] = language
    
    # add some exceptions
    language_enum_map['Chinese'] = cloudlanguagetools.languages.Language.zh_cn
    language_enum_map['Bengali'] = cloudlanguagetools.languages.Language.bn
    language_enum_map['Malaylam'] = cloudlanguagetools.languages.Language.ml
    language_enum_map['Portuguese'] = cloudlanguagetools.languages.Language.pt_pt
    language_enum_map['Slovanian'] = cloudlanguagetools.languages.Language.sl
    language_enum_map['Valencian'] = cloudlanguagetools.languages.Language.ca
    # print(language_enum_map)

    vocalware_language_id_to_language_enum = {}
    for entry in languages['LANGUAGELIST']['LANGUAGE']:
        language_name = entry['@NAME']
        language_id = int(entry['@ID'])
        # print(f'language_id: {language_id} language_name: {language_name}')
        if language_name in language_enum_map:
            lang_enum = language_enum_map[language_name]
            vocalware_language_id_to_language_enum[language_id] = lang_enum
        else:
            logging.error(f'language not found: {language_name}')

    print(vocalware_language_id_to_language_enum)

    language_to_audio_language_map = {}
    for audio_language in cloudlanguagetools.languages.AudioLanguage:
        language_to_audio_language_map[audio_language.lang] = audio_language
    

    f = open('temp_data_files/vocalware_voices.json')
    voices_content = f.read()
    voices = json.loads(voices_content)    
    # pprint.pprint(voices)

    voice_list = voices['VOICELIST']['VOICE']
    # pprint.pprint(voice_list)

    pandas.set_option('display.max_rows', 999)
    voices_df = pandas.DataFrame(voice_list)
    voices_df['engine_id'] = voices_df['@ENGINE'].astype(int)
    # voices_subset_df = voices_df[~voices_df['engine_id'].isin([21, 22])]
    voices_subset_df = voices_df[voices_df['engine_id'].isin([2, 3, 7])]

    # print(voices_subset_df)

    audio_language_substr_mappings = {
        'Cantonese': cloudlanguagetools.languages.AudioLanguage.zh_HK,
        'Brazilian': cloudlanguagetools.languages.AudioLanguage.pt_BR,
        'Brasilian': cloudlanguagetools.languages.AudioLanguage.pt_BR,
        'Portugal': cloudlanguagetools.languages.AudioLanguage.pt_PT,
        'Canadian': cloudlanguagetools.languages.AudioLanguage.fr_CA,
        'Taiwanese': cloudlanguagetools.languages.AudioLanguage.zh_TW,
        'US': cloudlanguagetools.languages.AudioLanguage.en_US,
        'UK': cloudlanguagetools.languages.AudioLanguage.en_GB,
        'Australian': cloudlanguagetools.languages.AudioLanguage.en_AU,
        'Indian': cloudlanguagetools.languages.AudioLanguage.en_IN,
        'Castilian': cloudlanguagetools.languages.AudioLanguage.es_ES,
        'Chilean': cloudlanguagetools.languages.AudioLanguage.es_LA,
        'Argentine': cloudlanguagetools.languages.AudioLanguage.es_LA,
        'Mexican': cloudlanguagetools.languages.AudioLanguage.es_MX,
    }

    # voices_subset_df = voices_subset_df.head(5)

    gender_api_key = os.environ['GENDER_API_KEY']

    vocalware_voice_file = open('temp_data_files/vocalware_voices.py', 'w')
    for index, row in voices_subset_df.iterrows():
        voice_name = row['@NAME']
        voice_id = int(row['@ID'])
        language_id = int(row['@LANG'])
        engine_id = row['engine_id']

        if language_id != 0:
            language_enum = vocalware_language_id_to_language_enum[language_id]
            audio_language_enum = language_to_audio_language_map[language_enum]
            for key, value in audio_language_substr_mappings.items():
                if key in voice_name:
                    audio_language_enum = value
                    break
            # print(f'name: {voice_name} audio_language: {audio_language_enum} language_id: {language_id} voice_id: {voice_id} engine_id: {engine_id}')
            voice_name = re.sub('\(.*\)', '', voice_name)
            voice_name = voice_name.strip()
            # https://gender-api.com/get?name=elizabeth&key=afwY7pbzKjAJJxUL8AKzRzCVQujWLyuNN9ES
            print(f'processing voice {voice_name}')
            response = requests.get(f'https://gender-api.com/get?name={voice_name}&key={gender_api_key}')
            response_data = response.json()
            gender_response = response_data['gender']
            if gender_response == 'unknown':
                logging.error(f'could not detect gender for {voice_name}')
                gender_response = 'male'
            gender = cloudlanguagetools.constants.Gender[gender_response.capitalize()]
            voice_code = f"""VocalWareVoice(cloudlanguagetools.languages.AudioLanguage.{audio_language_enum.name}, '{voice_name}', cloudlanguagetools.constants.Gender.{gender.name}, {language_id}, {voice_id}, {engine_id}),\n"""
            vocalware_voice_file.write(voice_code)
    
    vocalware_voice_file.close()

def thai_tokenization():
    manager = get_manager()
    pythainlp_service = manager.services[cloudlanguagetools.constants.Service.PyThaiNLP.name]
    azure_service = manager.services[cloudlanguagetools.constants.Service.Azure.name]

    text = 'รถแท็กซี่อยู่ที่หน้าโรงแรมค่ะ'
    
    tokenized_result = pythainlp_service.tokenize(text, {})
    tokenized_result = [token for token in tokenized_result if len(token.strip()) > 0]

    if False:
        tokenized_result = [
            'ขอโทษ',
            'ครับ',
            'ช่วย',
            'พูด',
            'ช้าๆ',
            'ได้ไหม',
            'ครับ'
        ]

    print(tokenized_result)

    breakdown_entries = []
    for token in tokenized_result:
        romanization = pythainlp_service.get_transliteration(token, {})
        dictionary_lookup_result = azure_service.dictionary_lookup(token, 'th', 'en')
        translation = azure_service.get_translation(token, 'th', 'en')
        
        breakdown_entries.append({
            'token': token,
            'transliteration':  romanization,
            'dictionary_lookups': dictionary_lookup_result,
            'translation': translation
        })

    # pprint.pprint(breakdown_entries)

    def format_entry(entry):
        # do we have dictionary lookups ?
        token = entry['token']
        transliteration = entry['transliteration']

        translation = entry['translation']
        dictionary_lookups = entry['dictionary_lookups']

        meanings = [translation] + dictionary_lookups

        result = f"{token} <b>{transliteration}</b>: {' / '.join(meanings)}"
        return result

    html_entries = [format_entry(x) for x in breakdown_entries]

    html_text = '<br/>\n'.join(html_entries)
    output_filename = 'temp_data_files/breakdown.html'
    with open(output_filename, 'w', encoding='utf8') as f:
        f.write(html_text)
        f.close()    
    logging.info(f'wrote {output_filename}')

def test_get_language_data():
    manager = get_manager()
    language_data = manager.get_language_data_json()
    output_filename = 'temp_data_files/language_data_v1.json'
    with open(output_filename, 'w', encoding='utf8') as f:
        f.write(json.dumps(language_data, indent=4, sort_keys=True, ensure_ascii=False))
        f.close()    
    logging.info(f'wrote {output_filename}')

def test_get_language_data_redis():
    redis_connection = redisdb.RedisDb()
    language_data = redis_connection.get_language_data()
    output_filename = 'temp_data_files/language_data_redis.json'
    with open(output_filename, 'w', encoding='utf8') as f:
        f.write(json.dumps(language_data, indent=4, sort_keys=True, ensure_ascii=False))
        f.close()    
    logging.info(f'wrote {output_filename}')

def test_voicen():
    
    import requests
    import json

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Token $VOICEN_ACCESS_TOKEN',
    }

    data = '{"text":"salam", "lang":"az", "voice_id": "325640"}'

    response = requests.post('https://tts.voicen.com/api/v1/jobs/text/', headers=headers, data=data)

    print(json.dumps(response.json(), indent=4, sort_keys=True))    

if __name__ == '__main__':
    logger = logging.getLogger()
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])        
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', 
                        datefmt='%Y%m%d-%H:%M:%S',
                        stream=sys.stdout,
                        level=logging.INFO)    

    # generate_video_audio()
    # test_azure_audio()
    # test_google_audio()
    # play_google_audio()
    # play_azure_audio()
    get_voice_list()
    # get_voice_list_awesometts()
    # get_watson_voice_list()
    # get_amazon_voice_list()
    # get_forvo_voice_list()
    # get_amazon_voice_list_awesometts()
    # get_azure_translation_languages()
    # get_google_translation_languages()
    # get_watson_translation_languages()
    #output_languages_enum()
    # get_translation_language_list()
    # output_language_audio_mapping()
    # detect_language()
    # translate_google()
    # translate_azure()
    # dictionary_lookup_azure()
    # dictionary_examples_azure()
    # end_to_end_test()
    # transliterate_azure()
    # get_transliteration_language_list()
    # print_all_languages()
    # print_all_audio_languages()
    # cereproc_authentication()
    # cereproc_tts_voice_list()
    # test_epitran()
    # create_epitran_mappings()
    # test_debounce()
    # load_vocalware_voices()
    # thai_tokenization()
    # test_get_language_data()
    # test_get_language_data_redis()