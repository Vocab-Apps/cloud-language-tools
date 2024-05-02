import os
import requests
import logging
import time
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

CLIENT_VERSION='v0.01'
CLIENT_NAME='performance_test'

class CltBenchmark:

    def __init__(self):
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
            url = f'{base_url}/languagetools-api/v2/{url_endpoint}'
            response = requests.get(url, headers={
                'Content-Type': 'application/json', 
                'Authorization': f'Api-Key {api_key}'})
        else:
            url = f'{base_url}/{url_endpoint}'
            response = requests.get(url, headers={'Content-Type': 'application/json', 'api_key': api_key})
        response.raise_for_status()    
        return response.json()

    def post_authenticated(self, base_url, url_endpoint, api_key, data, use_vocab_api=False, return_json=True):
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
            headers = headers={
                'Content-Type': 'application/json', 
                'api_key': api_key,
                'client': CLIENT_NAME, 
                'client_version': CLIENT_VERSION
            }
            response = requests.post(url, json=data, headers=headers)
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

    def get_voice_key():
        pass

    def run_request(self):
        start_time = time.time()

        content = self.post_request_authenticated_audio('audio', {
            'text': 'Je ne suis pas intéressé.',
            'service': self.service,
            'voice_key': self.selected_voice['voice_key'],
            'options': {}
        })

        end_time = time.time()
        execution_time = end_time - start_time

        return execution_time

def run_benchmark_suite(benchmark, num_workers, num_runs):
    logger.info(f'running benchmark suite with {num_workers} workers and {num_runs} runs')

    # Create a ThreadPoolExecutor
    execution_times = []
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Start time
        start_time = time.time()

        # Run benchmark.run_request() 100 times
        futures = [executor.submit(benchmark.run_request) for _ in range(num_runs)]

        # Wait for all futures to complete
        for future in concurrent.futures.as_completed(futures):
            # If there was an exception, it will be raised when result is called
            try:
                result = future.result()
                execution_times.append(result)
            except Exception as exc:
                print(f'Generated an exception: {exc}')

        # End time
        end_time = time.time()

        # Compute the average execution time
        average_execution_time = (end_time - start_time) / 100

        # compute stats on the times in the execution_times array, including std dev
        min_time = min(execution_times)
        max_time = max(execution_times)
        average_time = sum(execution_times) / len(execution_times)
        std_dev = (sum([(x - average_time) ** 2 for x in execution_times]) / len(execution_times)) ** 0.5

        logger.info(f'average_time: {average_time}, min_time: {min_time}, max_time: {max_time}, std_dev: {std_dev}')

def run_test():
    # setup default basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    benchmark = CltBenchmark()
    # execution_time = benchmark.run_request()
    # logger.info(f'execution_time: {execution_time} seconds')
    run_benchmark_suite(benchmark, 10, 10)




if __name__ == '__main__':
    run_test()