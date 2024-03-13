import unittest
import json
import tempfile
import magic
import datetime
import logging
import pytest
import os
import random
import requests
import urllib.parse
import cloudlanguagetools.constants

logger = logging.getLogger(__name__)

def get_authenticated(base_url, url_endpoint, api_key, use_vocab_api=False):
    if use_vocab_api:
        url = f'{base_url}/languagetools-api/v2/{url_endpoint}'
        response = requests.get(url, headers={
            'Content-Type': 'application/json', 
            'Authorization': f'Api-Key {api_key}'})
    else:
        url = f'{base_url}/{url_endpoint}'
        response = requests.get(url, headers={'Content-Type': 'application/json', 'api_key': api_key})
    response.raise_for_status()    
    return response.json()

def post_authenticated(base_url, url_endpoint, api_key, data, use_vocab_api=False):
    if use_vocab_api:
        url = f'{base_url}/languagetools-api/v2/{url_endpoint}'
        logger.info(f'post request on url {url}')
        response = requests.post(url, json=data, headers={
            'Content-Type': 'application/json', 
            'Authorization': f'Api-Key {api_key}'})
    else:
        url = f'{base_url}/{url_endpoint}'
        response = requests.post(url, json=data, headers={'Content-Type': 'application/json', 'api_key': api_key})
    response.raise_for_status()    
    return response.json()

class PostDeployTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(PostDeployTests, cls).setUpClass()

        cls.base_url = os.environ['ANKI_LANGUAGE_TOOLS_BASE_URL']
        cls.api_key=os.environ['ANKI_LANGUAGE_TOOLS_API_KEY']
        cls.use_vocab_api = int(os.environ.get('ANKI_LANGUAGE_TOOLS_API_VOCAB', 0)) == 1
        cls.client_version = 'v0.01'

        cls.voice_list = get_authenticated(cls.base_url, 'voice_list', cls.api_key, use_vocab_api=cls.use_vocab_api)

    @classmethod
    def tearDownClass(cls):
        pass

    def get_request_authenticated(self, url_endpoint):
        return get_authenticated(self.base_url, url_endpoint, self.api_key, use_vocab_api=self.use_vocab_api)

    def post_request_authenticated(self, url_endpoint, data):
        return post_authenticated(self.base_url, url_endpoint, self.api_key, data, use_vocab_api=self.use_vocab_api)

    def get_url(self, path):
        if self.use_vocab_api:
            return f'{self.base_url}/languagetools-api/v2/{path}'
        else:
            return f'{self.base_url}{path}'

    def test_verify_api_key(self):
        # pytest manual_test_postdeploy.py -rPP -s -k test_verify_api_key
        data = self.get_request_authenticated('verify_api_key')
        self.assertEqual({'key_valid': True, 'msg': 'API Key is valid'}, data)


    def test_language_list(self):
        # pytest manual_test_postdeploy.py -rPP -s -k test_language_list
        actual_language_list = get_authenticated(self.base_url, 'language_list', self.api_key, use_vocab_api=self.use_vocab_api)

        self.assertTrue('fr' in actual_language_list)
        self.assertEqual(actual_language_list['fr'], 'French')
        self.assertEqual(actual_language_list['yue'], 'Chinese (Cantonese, Traditional)')
        self.assertEqual(actual_language_list['zh_cn'], 'Chinese (Simplified)')

    def test_voice_list(self):
        # pytest manual_test_postdeploy.py -rPP -s -k test_voice_list

        voice_list = self.get_request_authenticated('voice_list')

        self.assertTrue(len(voice_list) > 100) # with google and azure, we already have 400 voices or so
        
        subset_1 = [x for x in voice_list if x['language_code'] == 'fr']
        self.assertTrue(len(subset_1) > 10) # there should be a dozen french voices

        voice1 = subset_1[0]

        self.assertTrue(len(voice1['gender']) > 0)
        self.assertTrue(len(voice1['language_code']) > 0)
        self.assertTrue(len(voice1['audio_language_code']) > 0)
        self.assertTrue(len(voice1['audio_language_name']) > 0)
        self.assertTrue(len(voice1['voice_description']) > 0)
        self.assertTrue(len(voice1['service']) > 0)
        self.assertTrue('voice_key' in voice1)

    def test_translation_language_list(self):
        # pytest manual_test_postdeploy.py -rPP -k 'test_translation_language_list'
        if self.use_vocab_api:
            # on vocabai API, only the language_data endpoint is supported
            language_data = self.get_request_authenticated('language_data')
            translation_language_list = language_data['translation_options']
        else:
            # translation_language_list in the old way of doing things
            response = requests.get(self.get_url('/translation_language_list'))
            translation_language_list = response.json()
        self.assertTrue(len(translation_language_list) > 100) # with google and azure, we already have 400 voices or so
        
        subset_1 = [x for x in translation_language_list if x['language_code'] == 'fr']
        self.assertTrue(len(subset_1) >= 2) # at least one for google, one for azure

        language1 = subset_1[0]

        self.assertTrue(len(language1['language_code']) > 0)
        self.assertTrue(len(language1['language_id']) > 0)
        self.assertTrue(len(language1['language_name']) > 0)
        self.assertTrue(len(language1['service']) > 0)

    def test_transliteration_language_list(self):
        # pytest manual_test_postdeploy.py -rPP -k 'test_transliteration_language_list'

        if self.use_vocab_api:
            # on vocabai API, only the language_data endpoint is supported
            language_data = self.get_request_authenticated('language_data')
            transliteration_language_list = language_data['transliteration_options']
        else:
            response = requests.get(self.get_url('/transliteration_language_list'))
            transliteration_language_list = response.json()


        self.assertTrue(len(transliteration_language_list) > 30) # 
        
        subset_1 = [x for x in transliteration_language_list if x['language_code'] == 'zh_cn']
        self.assertTrue(len(subset_1) >= 1) # at least one, azure

        language1 = subset_1[0]

        self.assertTrue(len(language1['language_code']) > 0)
        self.assertTrue(len(language1['language_name']) > 0)
        self.assertTrue(len(language1['service']) > 0)
        self.assertTrue(len(language1['transliteration_name']) > 0)


    def test_translate(self):
        # pytest manual_test_postdeploy.py -rPP -k test_translate

        source_text = 'Je ne suis pas intéressé.'
        data = self.post_request_authenticated('translate', {
            'text': source_text,
            'service': 'Azure',
            'from_language_key': 'fr',
            'to_language_key': 'en'
        })
        self.assertEqual(data['translated_text'], "I'm not interested.")

        # locate the azure language_id for simplified chinese
        language_data = self.get_request_authenticated('language_data')
        translation_language_list = language_data['translation_options']
        chinese_azure = [x for x in translation_language_list if x['language_code'] == 'zh_cn' and x['service'] == 'Azure']
        translation_azure_chinese = chinese_azure[0]

        data = self.post_request_authenticated('translate', {
            'text': '中国有很多外国人',
            'service': 'Azure',
            'from_language_key': translation_azure_chinese['language_id'],
            'to_language_key': 'en'
        })
        self.assertIn(data['translated_text'], ['There are many foreigners in China', 'There are a lot of foreigners in China'])

    def test_translate_all(self):
        # pytest manual_test_postdeploy.py -k test_translate_all

        source_text = '成本很低'
        data = self.post_request_authenticated('translate_all', {
            'text': source_text,
            'from_language': 'zh_cn',
            'to_language': 'fr'
        })

        possible_translations = ['à bas prix', 'Faible coût', 'À bas prix', 'faible coût', 'très faible coût', 'Le coût est très bas', 'Le coût est très faible',
            'Très faible coût']
        self.assertTrue(data['Azure'] == 'Le coût est faible' or data['Azure'] == 'Le coût est très faible')
        self.assertIn(data['Amazon'], possible_translations)
        self.assertIn(data['Google'], possible_translations)
        self.assertEqual(data['Watson'], 'Le coût est très bas.')

    def test_translate_error(self):


        source_text = 'Je ne suis pas intéressé.'

        translate_url = self.get_url('translate')
        json_data = {
            'text': source_text,
            'service': 'Azure',
            'from_language_key': 'fr',
            'to_language_key': 'zh_cn'
        }

        if self.use_vocab_api:
            response = requests.post(translate_url, json=json_data, headers={
            'Content-Type': 'application/json', 
            'Authorization': f'Api-Key {self.api_key}'})
        else:
            response = requests.post(translate_url, json=json_data, headers={'api_key': self.api_key})

        self.assertEqual(response.status_code, 400)
        error_response = response.json()
        error_message = error_response['error']
        self.assertTrue('The target language is not valid' in error_message)


    def test_transliteration(self):
        if int(os.environ['CLT_RUN_NLP_TESTS']) == 0:
            raise unittest.SkipTest(f'NLP tests not enabled, skipping')

        response = requests.get(self.get_url('/transliteration_language_list'))
        transliteration_language_list = response.json()

        service = 'Azure'
        source_text = '成本很低'
        from_language = 'zh_cn'
        transliteration_candidates = [x for x in transliteration_language_list if x['language_code'] == from_language and x['service'] == service]
        self.assertTrue(len(transliteration_candidates) == 1) # once more services are introduced, change this
        transliteration_option = transliteration_candidates[0]
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']

        response = requests.post(self.get_url('/transliterate'), json={
            'text': source_text,
            'service': service,
            'transliteration_key': transliteration_key
        }, headers={'api_key': self.api_key})

        result = response.json()
        self.assertEqual({'transliterated_text': 'chéngběn hěndī'}, result)

    def test_transliteration_mandarin_cantonese(self):
        if int(os.environ['CLT_RUN_NLP_TESTS']) == 0:
            # skip 
            raise unittest.SkipTest(f'NLP tests not enabled, skipping')

        response = requests.get(self.get_url('/transliteration_language_list'))
        transliteration_language_list = response.json()

        service = 'MandarinCantonese'
        source_text = '成本很低'
        from_language = 'zh_cn'
        transliteration_candidates = [x for x in transliteration_language_list if x['language_code'] == from_language and x['service'] == service]
        self.assertTrue(len(transliteration_candidates) > 0) # once more services are introduced, change this

        # pick the one
        selected_candidate = [x for x in transliteration_candidates if '(Diacritics )' in x['transliteration_name']]
        self.assertTrue(len(selected_candidate) == 1)

        transliteration_option = selected_candidate[0]
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']

        response = requests.post(self.get_url('/transliterate'), json={
            'text': source_text,
            'service': service,
            'transliteration_key': transliteration_key
        }, headers={'api_key': self.api_key})

        result = response.json()
        self.assertEqual({'transliterated_text': 'chéngběn hěn dī'}, result)

    def test_transliteration_mandarin_cantonese_2(self):
        if int(os.environ['CLT_RUN_NLP_TESTS']) == 0:
            # skip 
            raise unittest.SkipTest(f'NLP tests not enabled, skipping')

        response = requests.get(self.get_url('/transliteration_language_list'))
        transliteration_language_list = response.json()

        service = 'MandarinCantonese'
        source_text = '好多嘢要搞'
        from_language = 'yue'
        transliteration_candidates = [x for x in transliteration_language_list if x['language_code'] == from_language and x['service'] == service]
        self.assertTrue(len(transliteration_candidates) > 0) # once more services are introduced, change this

        # pick the one
        selected_candidate = [x for x in transliteration_candidates if '(Diacritics )' in x['transliteration_name']]
        self.assertTrue(len(selected_candidate) == 1)

        transliteration_option = selected_candidate[0]
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']

        response = requests.post(self.get_url('/transliterate'), json={
            'text': source_text,
            'service': service,
            'transliteration_key': transliteration_key
        }, headers={'api_key': self.api_key})

        result = response.json()
        self.assertEqual({'transliterated_text': 'hóudō jě jîu gáau'}, result)


    def test_detection(self):
        if int(os.environ['CLT_RUN_NLP_TESTS']) == 0:
            raise unittest.SkipTest(f'NLP tests not enabled, skipping')

        source_list = [
            'Pouvez-vous me faire le change ?',
            'Pouvez-vous débarrasser la table, s\'il vous plaît?'
        ]

        response = requests.post(self.get_url('/detect'), json={
            'text_list': source_list
        }, headers={'api_key': self.api_key})

        data = response.json()
        self.assertEqual(data['detected_language'], 'fr')


    def test_audio(self):
        # pytest test_postdeploy.py -k test_audio
        # get one azure voice for french
        service = 'Azure'
        french_voices = [x for x in self.voice_list if x['language_code'] == 'fr' and x['service'] == service]
        first_voice = french_voices[0]

        response = requests.post(self.get_url('/audio'), json={
            'text': 'Je ne suis pas intéressé.',
            'service': service,
            'voice_key': first_voice['voice_key'],
            'options': {}
        }, headers={'api_key': self.api_key})

        self.assertEqual(response.status_code, 200)

        output_temp_file = tempfile.NamedTemporaryFile()
        with open(output_temp_file.name, 'wb') as f:
            f.write(response.content)
        f.close()

        # verify file type
        filetype = magic.from_file(output_temp_file.name)
        # should be an MP3 file
        expected_filetype = 'MPEG ADTS, layer III'

        self.assertTrue(expected_filetype in filetype)

    def test_audio_v2(self):
        # pytest test_api.py -k test_audio_v2


        source_text_french = 'Je ne suis pas intéressé.'
        source_text_japanese = 'おはようございます'

        # get one azure voice for french

        service = 'Azure'
        french_voices = [x for x in self.voice_list if x['language_code'] == 'fr' and x['service'] == service]
        first_voice = french_voices[0]
        response = requests.post(self.get_url('/audio_v2'), json={
            'text': source_text_french,
            'service': service,
            'deck_name': 'french_deck_1',
            'request_mode': 'batch',
            'language_code': first_voice['language_code'],
            'voice_key': first_voice['voice_key'],
            'options': {}
        }, headers={'api_key': self.api_key, 'client': 'test', 'client_version': self.client_version})

        self.assertEqual(response.status_code, 200)

        # retrieve file
        output_temp_file = tempfile.NamedTemporaryFile()
        with open(output_temp_file.name, 'wb') as f:
            f.write(response.content)
        f.close()

        # perform checks on file
        # ----------------------

        # verify file type
        filetype = magic.from_file(output_temp_file.name)
        # should be an MP3 file
        expected_filetype = 'MPEG ADTS, layer III'

        self.assertTrue(expected_filetype in filetype)

    def verify_audio_service_english(self, service):
        source_text_english = 'success'

        english_voices = [x for x in self.voice_list if x['language_code'] == 'en' and x['service'] == service]
        # pick random voice
            # pick random voice
        selected_voice = random.choice(english_voices)

        response = requests.post(self.get_url('/audio_v2'), json={
            'text': source_text_english,
            'service': service,
            'request_mode': 'batch',
            'language_code': selected_voice['language_code'],
            'voice_key': selected_voice['voice_key'],
            'options': {}
        }, headers={'api_key': self.api_key, 'client': 'test', 'client_version': self.client_version})

        self.assertEqual(response.status_code, 200, msg=f'Verifying status code for {service}')

        # retrieve file
        output_temp_file = tempfile.NamedTemporaryFile()
        with open(output_temp_file.name, 'wb') as f:
            f.write(response.content)
        f.close()

        # perform checks on file
        # ----------------------

        # verify file type
        filetype = magic.from_file(output_temp_file.name)
        # should be an MP3 file
        expected_filetype = 'MPEG ADTS, layer III'

        self.assertTrue(expected_filetype in filetype, f'Verifying file type for {service}, expected: {expected_filetype} actual: {filetype}, voice: {selected_voice}')

    def test_audio_v2_all_services_english(self):
        # pytest manual_test_postdeploy.py -rPP -k test_audio_v2_all_services_english
        # exclude Forvo from this test
        service_list = ['Azure', 'Google', 'Watson', 'Naver', 'Amazon', 'CereProc', 'VocalWare']
        for service in service_list:
            self.verify_audio_service_english(service)



    def test_audio_yomichan(self):
        # pytest test_api.py -rPP -k test_audio_yomichan
        
        # get one azure voice for japanese
        service = 'Azure'
        japanese_voices = [x for x in self.voice_list if x['language_code'] == 'ja' and x['service'] == service]
        first_voice = japanese_voices[0]

        source_text = 'おはようございます'
        voice_key_str = urllib.parse.quote_plus(json.dumps(first_voice['voice_key']))
        url_params = f'api_key={self.api_key}&service={service}&voice_key={voice_key_str}&text={source_text}'
        url = self.get_url(f'/yomichan_audio?{url_params}')

        print(f'url: {url}')

        response = requests.get(url)

        self.assertEqual(response.status_code, 200)

        output_temp_file = tempfile.NamedTemporaryFile()
        with open(output_temp_file.name, 'wb') as f:
            f.write(response.content)
        f.close()

        # verify file type
        filetype = magic.from_file(output_temp_file.name)
        # should be an MP3 file
        expected_filetype = 'MPEG ADTS, layer III'

        self.assertTrue(expected_filetype in filetype)

    def test_account(self):
        # pytest manual_test_postdeploy.py -rPP -k test_account

        url = self.get_url('/account')
        response = requests.get(url, headers={'api_key': self.api_key})
        data = response.json()

        self.assertEqual(data['type'], '250,000 characters')

    def test_spacy_tokenization(self):
        # pytest manual_test_postdeploy.py -rPP -k test_spacy_tokenization

        if int(os.environ['CLT_RUN_NLP_TESTS']) == 0:
            # skip 
            raise unittest.SkipTest(f'NLP tests not enabled, skipping')

        service = 'Spacy'

        # english
        source_text = "I was reading today's paper."
        from_language = 'en'
        tokenization_key = {
            'model_name': 'en'
        }

        url = self.get_url('/tokenize_v1')
        response = requests.post(url, json={
            'text': source_text,
            'service': service,
            'tokenization_key': tokenization_key
        }, headers={'api_key': self.api_key})

        self.assertEqual(response.status_code, 200)


        # french
        source_text = "Le nouveau plan d’investissement du gouvernement."
        from_language = 'fr'
        tokenization_key = {
            'model_name': 'fr'
        }

        url = self.get_url('/tokenize_v1')
        response = requests.post(url, json={
            'text': source_text,
            'service': service,
            'tokenization_key': tokenization_key
        }, headers={'api_key': self.api_key})

        self.assertEqual(response.status_code, 200)        

        # chinese
        source_text = "送外卖的人"
        from_language = 'zh_cn'
        tokenization_key = {
            'model_name': 'zh_jieba'
        }

        url = self.get_url('/tokenize_v1')
        response = requests.post(url, json={
            'text': source_text,
            'service': service,
            'tokenization_key': tokenization_key
        }, headers={'api_key': self.api_key})

        self.assertEqual(response.status_code, 200)




if __name__ == '__main__':
    # how to run with logging on: pytest test_api.py -s -p no:logging -k test_translate
    unittest.main()  
