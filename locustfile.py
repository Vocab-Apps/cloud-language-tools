import os
import logging

from locust import HttpUser, task

logger = logging.getLogger(__name__)

CLIENT_VERSION='v0.01'
CLIENT_NAME='performance_test'

class CltPerformanceTest(HttpUser):
    def __init__(self, config):
        # call base constructor
        super().__init__(config)
        logger.info('initializing benchmark')
        self.base_url = os.environ['ANKI_LANGUAGE_TOOLS_BASE_URL']
        self.api_key=os.environ['ANKI_LANGUAGE_TOOLS_API_KEY']
        self.use_vocab_api = int(os.environ.get('ANKI_LANGUAGE_TOOLS_API_VOCAB', 0)) == 1
        self.client_version = CLIENT_VERSION

        voice_list = self.get_authenticated(self.base_url, 'voice_list', self.api_key, use_vocab_api=self.use_vocab_api)

        self.service = 'Azure'
        french_voices = [x for x in voice_list if x['language_code'] == 'fr' and x['service'] == self.service]
        self.selected_voice = french_voices[0]    

    def get_authenticated(self, base_url, url_endpoint, api_key, use_vocab_api=False):
        if use_vocab_api:
            url = f'/languagetools-api/v2/{url_endpoint}'
            response = self.client.get(url, headers={
                'Content-Type': 'application/json', 
                'Authorization': f'Api-Key {api_key}'})
        else:
            url = f'/{url_endpoint}'
            response = self.client.get(url, headers={'Content-Type': 'application/json', 'api_key': api_key})
        response.raise_for_status()    
        return response.json()

    def post_authenticated(self, base_url, url_endpoint, api_key, data, use_vocab_api=False, return_json=True):
        if use_vocab_api:
            url = f'/languagetools-api/v2/{url_endpoint}'
            logger.info(f'post request on url {url}')
            headers = {
                'Content-Type': 'application/json', 
                'Authorization': f'Api-Key {api_key}'
            }
            response = self.client.post(url, json=data, headers=headers)
        else:
            url = f'/{url_endpoint}'
            headers = headers={
                'Content-Type': 'application/json', 
                'api_key': api_key,
                'client': CLIENT_NAME, 
                'client_version': CLIENT_VERSION
            }
            response = self.client.post(url, json=data, headers=headers)
        if response.status_code != 200:
            logger.error(f'Error in post_authenticated, url: {url}, status_code: {response.status_code}, response: {response.text}, data: {data}')
        response.raise_for_status()    
        if return_json:
            return response.json()
        else:
            return response.content

    def post_request_authenticated(self, url_endpoint, data):
        return self.post_authenticated(self.base_url, url_endpoint, self.api_key, data, use_vocab_api=self.use_vocab_api, return_json=True)

    def post_request_authenticated_audio(self, url_endpoint, data):
        return self.post_authenticated(self.base_url, url_endpoint, self.api_key, data, use_vocab_api=self.use_vocab_api, return_json=False)

    def get_language_data(self):
        url_endpoint = 'language_data'
        if not self.use_vocab_api:
            url_endpoint = 'language_data_v1'
        return self.get_request_authenticated(url_endpoint)

    def get_voice_key():
        pass

    @task
    def run_request(self):
        self.post_request_authenticated_audio('audio', {
            'text': 'Je ne suis pas intéressé.',
            'service': self.service,
            'voice_key': self.selected_voice['voice_key'],
            'options': {}
        })

