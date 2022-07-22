import os
import pandas
import logging
import requests
import urllib
import pprint
import clt_secrets as secrets

class AirtableUtils():
    def __init__(self):
        self.enable = secrets.config['airtable']['enable']
        if self.enable:
            self.airtable_api_key = secrets.config['airtable']['api_key']
            self.airtable_trial_users_url = secrets.config['airtable']['trial_users_url']
            self.airtable_patreon_users_url = secrets.config['airtable']['patreon_users_url']
            self.airtable_getcheddar_users_url = secrets.config['airtable']['getcheddar_users_url']
            self.airtable_usage_url = secrets.config['airtable']['usage_url']
            self.airtable_usage_daily_url = secrets.config['airtable']['usage_daily_url']

    def get_trial_users(self):
        return self.get_airtable_records(self.airtable_trial_users_url)

    def get_trial_tag_requests(self):
        url = f'{self.airtable_trial_users_url}?view=tag%20requests'
        response = requests.get(url, headers={'Authorization': f'Bearer {self.airtable_api_key}'})
        data = response.json()
        airtable_records = []
        for record in data['records']:
            airtable_records.append({'id': record['id'], 'email': record['fields']['email'], 'tag_request': record['fields']['tag_request']})
        airtable_records_df = pandas.DataFrame(airtable_records)
        return airtable_records_df

    def get_patreon_users(self):
        return self.get_airtable_records(self.airtable_patreon_users_url)

    def get_getcheddar_users(self):
        return self.get_airtable_records(self.airtable_getcheddar_users_url)

    def get_airtable_records(self, base_url):
        # first, list records
        data_available = True
        airtable_records = []
        offset = None
        while data_available:
            url = base_url
            if offset != None:
                url += '?offset=' + offset
            logging.info(f'querying airtable url {url}')
            response = requests.get(url, headers={'Authorization': f'Bearer {self.airtable_api_key}'})
            data = response.json()
            if 'offset' in data:
                offset = data['offset']
            else:
                data_available = False
            for record in data['records']:
                # print(record)
                full_record = {'record_id': record['id']}
                full_record.update(record['fields'])
                airtable_records.append(full_record)
        airtable_records_df = pandas.DataFrame(airtable_records)
        if 'email' in airtable_records_df.columns:
            airtable_records_df['email'] = airtable_records_df['email'].str.lower()
        return airtable_records_df

    def update_patreon_users(self, data_df):
        self.update_airtable_records(self.airtable_patreon_users_url, data_df)

    def add_trial_users(self, data_df):
        self.create_airtable_records(self.airtable_trial_users_url, data_df)

    def update_trial_users(self, data_df):
        self.update_airtable_records(self.airtable_trial_users_url, data_df)

    def delete_trial_users(self, record_ids):
        self.delete_airtable_records(self.airtable_trial_users_url, record_ids)

    def update_getcheddar_users(self, data_df):
        self.update_airtable_records(self.airtable_getcheddar_users_url, data_df)

    def update_usage(self, usage_df):
        # self.airtable_usage_url
        self.delete_all_airtable_records(self.airtable_usage_url)
        self.create_airtable_records(self.airtable_usage_url, usage_df)

    def update_usage_daily(self, usage_df):
        # self.airtable_usage_url
        usage_df = usage_df.sort_values('period', ascending=False)
        usage_df = usage_df.head(600)
        self.delete_all_airtable_records(self.airtable_usage_daily_url)
        self.create_airtable_records(self.airtable_usage_daily_url, usage_df)        

    def update_airtable_records(self, base_url, update_df):

        update_instructions = []
        column_list = update_df.columns.values.tolist()
        column_list.remove('record_id')

        for index, record in update_df.iterrows():
            update_instruction = {
                'id': record['record_id'],
                'fields': {}
            }
            for column in column_list:
                value = record[column]
                if isinstance(record[column], list):
                    pass # don't do anything
                elif pandas.isnull(value):
                    value = None
                update_instruction['fields'][column] = value
            update_instructions.append(update_instruction)

        logging.info(f'starting to update {base_url}')

        headers = {
            'Authorization': f'Bearer {self.airtable_api_key}',
            'Content-Type': 'application/json' }
        while len(update_instructions) > 0:
            slice_length = min(10, len(update_instructions))
            update_slice = update_instructions[0:slice_length]
            del update_instructions[0:slice_length]
            
            # pprint.pprint(update_slice)
            logging.info(f'updating records')
            response = requests.patch(base_url, json={
                'records': update_slice,
                'typecast': True
            }, headers=headers)
            if response.status_code != 200:
                logging.error(f'could not update airtable records for url {base_url}: {update_slice}, status_code: {response.status_code} ({response.content})')

    def delete_airtable_records(self, base_url, record_ids):
        logging.info(f'deleting records from {base_url} ({len(record_ids)} in total)')
        headers = {
            'Authorization': f'Bearer {self.airtable_api_key}',
            'Content-Type': 'application/json' }        

        while len(record_ids) > 0:
            subset_length = min(10, len(record_ids))
            record_selection = record_ids[0:subset_length]
            record_ids = record_ids[subset_length:]
            params = {'records[]': record_selection}
            # logging.info(f'deleting records {record_selection}')
            params_encoded = urllib.parse.urlencode(params, True)
            url = base_url + '?' + params_encoded
            logging.info(f'delete URL: {url}')
            response = requests.delete(url, headers=headers)
            if response.status_code != 200:
                logging.error(response.content)

    def delete_all_airtable_records(self, base_url):
        logging.info(f'deleting all records from {base_url}')
        records_df = self.get_airtable_records(base_url)
        record_ids = list(records_df['record_id'])
        headers = {
            'Authorization': f'Bearer {self.airtable_api_key}',
            'Content-Type': 'application/json' }        

        while len(record_ids) > 0:
            subset_length = min(10, len(record_ids))
            record_selection = record_ids[0:subset_length]
            record_ids = record_ids[subset_length:]
            params = {'records[]': record_selection}
            # logging.info(f'deleting records {record_selection}')
            params_encoded = urllib.parse.urlencode(params, True)
            url = base_url + '?' + params_encoded
            logging.info(f'delete URL: {url}')
            response = requests.delete(url, headers=headers)
            if response.status_code != 200:
                logging.error(response.content)
        

    def create_airtable_records(self, base_url, records_df):

        update_instructions = []
        column_list = records_df.columns.values.tolist()

        for index, record in records_df.iterrows():
            create_instruction = {
                'fields': {}
            }
            for column in column_list:
                value = record[column]
                if isinstance(record[column], list):
                    pass # don't do anything
                elif pandas.isnull(value):
                    value = None
                create_instruction['fields'][column] = value
            update_instructions.append(create_instruction)

        logging.info(f'starting to update {base_url}')

        headers = {
            'Authorization': f'Bearer {self.airtable_api_key}',
            'Content-Type': 'application/json' }
        while len(update_instructions) > 0:
            slice_length = min(10, len(update_instructions))
            update_slice = update_instructions[0:slice_length]
            del update_instructions[0:slice_length]
            
            # pprint.pprint(update_slice)
            logging.info(f'creating records')
            response = requests.post(base_url, json={
                'records': update_slice,
                'typecast': True
            }, headers=headers)
            if response.status_code != 200:
                logging.error(response.content)            