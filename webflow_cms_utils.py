import requests
import clt_secrets as secrets
import pprint
import time
import json
import logging

class WebflowCMSUtils():
    def __init__(self):
        self.api_key = secrets.config['webflow']['api_key']
        self.site_id = secrets.config['webflow']['site_id']
        self.audio_language_collection_id = secrets.config['webflow']['audio_language_collection_id']
        self.voice_collection_id = secrets.config['webflow']['voice_collection_id']

    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.api_key}',
            'accept-version': '1.0.0',
            'Content-Type': 'application/json'
        }

    def get_auth_info(self):
        url = 'https://api.webflow.com/info'
        response = requests.get(url,headers=self.get_headers())
        print(response.json())

    def list_sites(self):
        url = 'https://api.webflow.com/sites'
        response = requests.get(url, headers=self.get_headers())
        print(response.json())

    def list_collections(self):
        url = f'https://api.webflow.com/sites/{self.site_id}/collections'
        response = requests.get(url, headers=self.get_headers())
        pprint.pprint(response.json())

    def list_languages(self):
        logging.info('listing webflow languages')
        time.sleep(1.0)
        url = f'https://api.webflow.com/collections/{self.audio_language_collection_id}/items'
        response = requests.get(url, headers=self.get_headers())
        return response.json()['items']

    def list_voices(self):
        logging.info('listing webflow voices')
        total_count = -1
        url = f'https://api.webflow.com/collections/{self.voice_collection_id}/items'
        response = requests.get(url, headers=self.get_headers())
        # pprint.pprint(response.json())
        total_count = response.json()['total']
        items = response.json()['items']
        offset = len(items)
        while len(items) < total_count:
            url = f'https://api.webflow.com/collections/{self.voice_collection_id}/items?offset={offset}'
            logging.info(f'querying url {url}')            
            response = requests.get(url, headers=self.get_headers())
            items.extend(response.json()['items'])
            offset = len(items)
        logging.info(f'found {len(items)} voices on webflow')
        return items
        

    def add_language(self, language_data):
        logging.info(f'uploading language to webflow: {language_data}')
        time.sleep(1.0)
        url = f'https://api.webflow.com/collections/{self.audio_language_collection_id}/items'
        data = json.dumps({
            'fields': language_data
        })
        # pprint.pprint(data)
        response = requests.post(url, headers=self.get_headers(), data=data) 
        pprint.pprint(response.json())
        if response.status_code != 200:
            raise Exception(f'status_code: {response.status_code} {response.content}')

    def add_voice(self, voice_data):
        logging.info(f'uploading voice to webflow: {voice_data}')
        time.sleep(1.0)
        url = f'https://api.webflow.com//collections/{self.voice_collection_id}/items'
        data = json.dumps({
            'fields': voice_data
        })
        response = requests.post(url, headers=self.get_headers(), data=data) 
        if response.status_code != 200:
            response_json = response.json()
            pprint.pprint(response_json)
            raise Exception(f'status_code: {response.status_code} {response.content}')
            


if __name__ == '__main__':
    webflow_utils = WebflowCMSUtils()
    # webflow_utils.get_auth_info()
    # webflow_utils.list_sites()
    # webflow_utils.list_collections()
    # webflow_utils.list_languages()
    voice_list = webflow_utils.list_voices()
    pprint.pprint(voice_list)
