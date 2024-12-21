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
import pprint
import urllib.parse
import cloudlanguagetools.constants

logger = logging.getLogger(__name__)

CLIENT_VERSION='v0.01'
CLIENT_NAME='test'

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

def post_authenticated(base_url, url_endpoint, api_key, data, use_vocab_api=False, return_json=True):
    if use_vocab_api:
        url = f'{base_url}/languagetools-api/v2/{url_endpoint}'
        logger.info(f'post request on url {url}')
        headers = {
            'Content-Type': 'application/json', 
            'Authorization': f'Api-Key {api_key}'
        }
        response = requests.post(url, json=data, headers=headers)
    else:
        url = f'{base_url}/{url_endpoint}'
        print(f'using API key: [{api_key}], url: {url}')
        headers = {
            'Content-Type': 'application/json', 
            'api_key': api_key,
            'client': CLIENT_NAME, 
            'client_version': CLIENT_VERSION
        }
        # pprint.pprint(headers)
        response = requests.post(url, json=data, headers=headers)
    if response.status_code != 200:
        logger.error(f'Error in post_authenticated, url: {url}, status_code: {response.status_code}, response: {response.text}, data: {data}')
    response.raise_for_status()    
    if return_json:
        return response.json()
    else:
        return response.content

class PostDeployTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(PostDeployTests, cls).setUpClass()

        cls.base_url = os.environ['ANKI_LANGUAGE_TOOLS_BASE_URL']
        cls.api_key=os.environ['ANKI_LANGUAGE_TOOLS_API_KEY']
        cls.use_vocab_api = int(os.environ.get('ANKI_LANGUAGE_TOOLS_API_VOCAB', 0)) == 1
        cls.client_version = CLIENT_VERSION

        cls.voice_list = get_authenticated(cls.base_url, 'voice_list', cls.api_key, use_vocab_api=cls.use_vocab_api)

    @classmethod
    def tearDownClass(cls):
        pass

    def get_request_authenticated(self, url_endpoint):
        return get_authenticated(self.base_url, url_endpoint, self.api_key, use_vocab_api=self.use_vocab_api)

    def post_request_authenticated(self, url_endpoint, data):
        return post_authenticated(self.base_url, url_endpoint, self.api_key, data, use_vocab_api=self.use_vocab_api, return_json=True)
    
    def post_request_authenticated_audio(self, url_endpoint, data):
        return post_authenticated(self.base_url, url_endpoint, self.api_key, data, use_vocab_api=self.use_vocab_api, return_json=False)

    def get_url(self, path):
        if self.use_vocab_api:
            overrides = {
                '_version': 'version'
            }
            path = overrides.get(path, path)
            return f'{self.base_url}/languagetools-api/v2/{path}'
        else:
            return f'{self.base_url}/{path}'


    def get_language_data(self):
        url_endpoint = 'language_data'
        if not self.use_vocab_api:
            url_endpoint = 'language_data_v1'
        return self.get_request_authenticated(url_endpoint)

    def test_expected_version(self):
        # pytest manual_test_postdeploy.py -rPP -s -k test_expected_version
        EXPECTED_VERSION=os.environ['CLOUDLANGUAGETOOLS_EXPECTED_VERSION']
        
        response = requests.get(self.get_url('_version'))
        response.raise_for_status()
        data = response.json()
        self.assertEqual(data['version'], EXPECTED_VERSION)

    def test_verify_api_key(self):
        # pytest manual_test_postdeploy.py -rPP -s -k test_verify_api_key

        if self.use_vocab_api:
            # skip, api endpoint not implemented
            raise unittest.SkipTest(f'Verify API key not implemented on vocabai')

        response = requests.post(self.get_url('verify_api_key'), json={'api_key': self.api_key})
        data = response.json()

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
            response = requests.get(self.get_url('translation_language_list'))
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
            response = requests.get(self.get_url('transliteration_language_list'))
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
        language_data = self.get_language_data()
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
        # pytest manual_test_postdeploy.py -capture=no --log-cli-level=INFO -k test_translate_error

        source_text = 'Je ne suis pas intéressé.'

        translate_url = self.get_url('translate')
        logger.info(f'translate_url: {translate_url}')
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


    def get_transliteration_options(self):
        if self.use_vocab_api:
            # on vocabai API, only the language_data endpoint is supported
            language_data = self.get_request_authenticated('language_data')
            transliteration_language_list = language_data['transliteration_options']
        else:
            response = requests.get(self.get_url('transliteration_language_list'))
            transliteration_language_list = response.json()

        return transliteration_language_list

    @unittest.skip("2024/12: skip as azure removed the pinyin transliteration")
    def test_transliteration(self):
        transliteration_language_list = self.get_transliteration_options()

        service = 'Azure'
        source_text = '成本很低'
        from_language = 'zh_cn'
        transliteration_candidates = [x for x in transliteration_language_list if x['language_code'] == from_language and x['service'] == service]
        self.assertTrue(len(transliteration_candidates) == 1) # once more services are introduced, change this
        transliteration_option = transliteration_candidates[0]
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']

        data = self.post_request_authenticated('transliterate', {
            'text': source_text,
            'service': service,
            'transliteration_key': transliteration_key
        })
        self.assertEqual({'transliterated_text': 'chéngběn hěndī'}, data)

    def test_transliteration_mandarin_cantonese(self):
        # pytest manual_test_postdeploy.py -capture=no --log-cli-level=INFO -k test_transliteration_mandarin_cantonese
        transliteration_language_list = self.get_transliteration_options()

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
        logger.info(pprint.pformat(transliteration_key))

        data = self.post_request_authenticated('transliterate', {
            'text': source_text,
            'service': service,
            'transliteration_key': transliteration_key
        })
        self.assertEqual({'transliterated_text': 'chéngběn hěn dī'}, data)

    def test_transliteration_mandarin_cantonese_2(self):
        transliteration_language_list = self.get_transliteration_options()

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

        data = self.post_request_authenticated('transliterate', {
            'text': source_text,
            'service': service,
            'transliteration_key': transliteration_key
        })

        self.assertEqual({'transliterated_text': 'hóudō jě jîu gáau'}, data)


    def test_detection(self):

        source_list = [
            'Pouvez-vous me faire le change ?',
            'Pouvez-vous débarrasser la table, s\'il vous plaît?'
        ]

        data = self.post_request_authenticated('detect', {
            'text_list': source_list
        })

        self.assertEqual(data['detected_language'], 'fr')


    def test_audio(self):
        # pytest manual_test_postdeploy.py -k test_audio
        # pytest manual_test_postdeploy.py -capture=no --log-cli-level=INFO -k test_audio
        # get one azure voice for french

        if self.use_vocab_api:
            # skip
            raise unittest.SkipTest(f'Vocab API not enabled, skipping, only v2 endpoint enabled')

        service = 'Azure'
        french_voices = [x for x in self.voice_list if x['language_code'] == 'fr' and x['service'] == service]
        first_voice = french_voices[0]


        content = self.post_request_authenticated_audio('audio', {
            'text': 'Je ne suis pas intéressé.',
            'service': service,
            'voice_key': first_voice['voice_key'],
            'options': {}
        })

        output_temp_file = tempfile.NamedTemporaryFile()
        with open(output_temp_file.name, 'wb') as f:
            f.write(content)
        f.close()

        # verify file type
        filetype = magic.from_file(output_temp_file.name)
        # should be an MP3 file
        expected_filetype = 'MPEG ADTS, layer III'

        self.assertTrue(expected_filetype in filetype)

    def test_audio_v2(self):
        # pytest test_api.py -k test_audio_v2
        # pytest manual_test_postdeploy.py -capture=no --log-cli-level=INFO -k test_audio_v2


        source_text_french = 'Je ne suis pas intéressé.'
        source_text_japanese = 'おはようございます'

        # get one azure voice for french

        service = 'Azure'
        french_voices = [x for x in self.voice_list if x['language_code'] == 'fr' and x['service'] == service]
        first_voice = french_voices[0]
        url_endpoint = 'audio'
        if not self.use_vocab_api:
            url_endpoint = 'audio_v2'

        content = self.post_request_authenticated_audio(url_endpoint, {
            'text': source_text_french,
            'service': service,
            'deck_name': 'french_deck_1',
            'request_mode': 'batch',
            'language_code': first_voice['language_code'],
            'voice_key': first_voice['voice_key'],
            'options': {}
        })

        # retrieve file
        output_temp_file = tempfile.NamedTemporaryFile()
        with open(output_temp_file.name, 'wb') as f:
            f.write(content)
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

        url_endpoint = 'audio'
        if not self.use_vocab_api:
            url_endpoint = 'audio_v2'

        content = self.post_request_authenticated_audio(url_endpoint, {
            'text': source_text_english,
            'service': service,
            'request_mode': 'batch',
            'language_code': selected_voice['language_code'],
            'voice_key': selected_voice['voice_key'],
            'options': {}
        })

        # retrieve file
        output_temp_file = tempfile.NamedTemporaryFile()
        with open(output_temp_file.name, 'wb') as f:
            f.write(content)
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



    @pytest.mark.skip(reason="yomichan not working in vocabai api")
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
        data = self.get_request_authenticated('account')
        # self.assertEqual(data['type'], '250,000 characters')
        self.assertTrue(len(data['email']) > 0)

    def test_account_wrong_api_key(self):
        # pytest manual_test_postdeploy.py -rPP -k test_account_wrong_api_key

        if not self.use_vocab_api:
            # skip
            raise unittest.SkipTest(f'only test this on vocabai')

        fake_api_key = 'FAKENONEXISTENTAPIKEY'
        response = requests.get(self.get_url('account'), headers={
            'Content-Type': 'application/json',
            'Authorization': f'Api-Key {fake_api_key}'})
        self.assertEqual(response.status_code, 403)

    def test_spacy_tokenization(self):
        # pytest manual_test_postdeploy.py -rPP -k test_spacy_tokenization

        if self.use_vocab_api:
            # skip
            raise unittest.SkipTest(f'tokenize_v1 not implemented on vocabai')

        service = 'Spacy'

        # english
        source_text = "I was reading today's paper."
        from_language = 'en'
        tokenization_key = {
            'model_name': 'en'
        }

        url = self.get_url('tokenize_v1')
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

        url = self.get_url('tokenize_v1')
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

        url = self.get_url('tokenize_v1')
        response = requests.post(url, json={
            'text': source_text,
            'service': service,
            'tokenization_key': tokenization_key
        }, headers={'api_key': self.api_key})

        self.assertEqual(response.status_code, 200)

    def test_breakdown(self):
        text = "I was reading today's paper."
        source_language = 'en'
        target_language = 'fr'

        language_data = self.get_language_data()

        # choose breakdown
        tokenization_service = 'Spacy'
        tokenization_candidates = [x for x in language_data['tokenization_options'] if x['language_code'] == source_language and x['service'] == tokenization_service]
        self.assertEqual(len(tokenization_candidates), 1)
        tokenization_option = tokenization_candidates[0]

        # choose transliteration
        transliteration_service = 'Epitran'
        transliteration_candidates = [x for x in language_data['transliteration_options'] if x['language_code'] == source_language and x['service'] == transliteration_service]
        transliteration_option = transliteration_candidates[0]

        # choose translation
        translation_service = 'Azure'
        source_language_id = [x for x in language_data['translation_options'] if x['language_code'] == source_language and x['service'] == translation_service][0]['language_id']
        target_language_id = [x for x in language_data['translation_options'] if x['language_code'] == target_language and x['service'] == translation_service][0]['language_id']
        translation_option = {
            'service': translation_service,
            'source_language_id': source_language_id,
            'target_language_id': target_language_id
        }

        # run the breakdown
        url_endpoint = 'breakdown'
        if not self.use_vocab_api:
            url_endpoint = 'breakdown_v1'
        breakdown_result = self.post_request_authenticated(url_endpoint, {
            'text': text,
            'tokenization_option': tokenization_option,
            'translation_option': translation_option,
            'transliteration_option': transliteration_option
        })

        pprint.pprint(breakdown_result)

        expected_output = [{'lemma': 'I',
        'pos_description': 'pronoun, personal',
        'token': 'I',
        'translation': 'Je',
        'transliteration': 'aj'},
        {'lemma': 'be',
        'pos_description': 'verb, past tense',
        'token': 'was',
        'translation': 'être',
        'transliteration': 'wɑz'},
        {'lemma': 'read',
        'pos_description': 'verb, gerund or present participle',
        'token': 'reading',
        'translation': 'lire',
        'transliteration': 'ɹɛdɪŋ'},
        {'lemma': 'today',
        'pos_description': 'noun, singular or mass',
        'token': 'today',
        'translation': 'Aujourd’hui',
        'transliteration': 'tədej'},
        {'lemma': "'s", 'pos_description': 'possessive ending', 'token': "'s"},
        {'lemma': 'paper',
        'pos_description': 'noun, singular or mass',
        'token': 'paper',
        'translation': 'papier',
        'transliteration': 'pejpɹ̩'},
        {'lemma': '.',
        'pos_description': 'punctuation mark, sentence closer',
        'token': '.'}]

        self.assertEqual(breakdown_result['breakdown'], expected_output)



if __name__ == '__main__':
    # how to run with logging on: pytest test_api.py -s -p no:logging -k test_translate
    unittest.main()  
