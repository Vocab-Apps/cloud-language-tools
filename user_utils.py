import pandas
import logging
import datetime
import argparse
import json
import pprint
import re

import clt_secrets as secrets
import quotas
import redisdb
import airtable_utils
import patreon_utils
import getcheddar_utils
import convertkit
import redisdb
import cloudlanguagetools.constants
import cloudlanguagetools.languages

logger = logging.getLogger(__name__)

class UserUtils():
    def __init__(self):
        self.airtable_utils = airtable_utils.AirtableUtils()
        if secrets.config['patreon']['enable']:
            self.patreon_utils = patreon_utils.PatreonUtils()
        self.convertkit_client = convertkit.ConvertKit()
        self.redis_connection = redisdb.RedisDb()
        self.getcheddar_utils = getcheddar_utils.GetCheddarUtils()

    def get_full_api_key_list(self):
        logger.info('getting full API key list')
        api_key_list = self.redis_connection.list_api_keys()
        return api_key_list        


    def get_api_key_list_df(self, api_key_list, key_type):

        records = []
        for api_key_entry in api_key_list:
            api_key = api_key_entry['api_key']
            key_data = api_key_entry['key_data']
            if key_data['type'] == key_type:
                data = {
                    'api_key': api_key
                }
                data.update(key_data)
                records.append(data)

        data_df = pandas.DataFrame(records)
        if 'expiration' in data_df:
            data_df['expiration_dt'] = pandas.to_datetime(data_df['expiration'], unit='s')
            data_df['expiration_str'] = data_df['expiration_dt'].dt.strftime('%Y-%m-%d')
            data_df['key_valid'] = data_df['expiration_dt'] > datetime.datetime.now()
            data_df = data_df.rename(columns={'user_id': 'patreon_user_id', 'expiration_str': 'api_key_expiration', 'key_valid': 'api_key_valid'})

        field_list_map = {
            'patreon': ['api_key', 'email', 'patreon_user_id', 'api_key_valid', 'api_key_expiration'],
            'trial': ['api_key', 'email', 'api_key_valid', 'api_key_expiration'],
            'getcheddar': ['api_key', 'email', 'code']
        }

        data_df['email'] = data_df['email'].str.lower()

        return data_df[field_list_map[key_type]]

    

    def get_patreon_users_df(self):
        logger.info(f'getting patreon user data')
        user_list = self.patreon_utils.get_patreon_user_ids()
        user_list_df = pandas.DataFrame(user_list)
        user_list_df = user_list_df.rename(columns={'user_id': 'patreon_user_id'})
        return user_list_df

    # get monthly usage data per user
    # -------------------------------

    def get_monthly_usage_data(self):
        logger.info('getting current month usage data')
        pattern = 'usage:user:monthly:' + datetime.datetime.now().strftime("%Y%m")
        return self.get_usage_data(pattern, 'monthly_cost', 'monthly_chars')

    def get_prev_monthly_usage_data(self):
        logger.info('getting previous month usage data')
        prev_month_datetime = datetime.datetime.now() + datetime.timedelta(days=-31)
        pattern = 'usage:user:monthly:' + prev_month_datetime.strftime("%Y%m")
        return self.get_usage_data(pattern, 'prev_monthly_cost', 'prev_monthly_chars')

    # get global monthly usage data
    # -----------------------------

    def get_global_monthly_usage_data(self):
        logger.info('getting current global month usage data')
        pattern = 'usage:global:monthly'
        return self.get_global_usage_data(pattern)

    # get global daily usage data
    # ---------------------------

    def get_global_daily_usage_data(self):
        logger.info('getting previous global daily usage data')
        pattern = 'usage:global:daily'
        return self.get_global_usage_data(pattern)

    def get_daily_usage_data(self):
        pattern = 'usage:user:daily:' + datetime.datetime.now().strftime("%Y%m%d")
        return self.get_usage_data(pattern, 'daily_cost', 'daily_chars')

    def get_usage_data(self, usage_key_pattern, cost_field_name, characters_field_name):
        usage_entries = self.redis_connection.list_usage(usage_key_pattern)
        # clt:usage:user:monthly:202103:Amazon:translation:2m0xzH92tgxb0pk9
        records = []
        for entry in usage_entries:
            usage_key = entry['usage_key']
            components = usage_key.split(':')
            api_key = components[-1]
            service = components[5]
            request_type = components[6]
            records.append({
                'api_key': api_key,
                'service': service,
                'request_type': request_type,
                'characters': int(entry['characters'])
            })

        if len(records) == 0:
            return pandas.DataFrame()

        records_df = pandas.DataFrame(records)

        cost_table_df = pandas.DataFrame(quotas.COST_TABLE)

        combined_df = pandas.merge(records_df, cost_table_df, how='left', on=['service', 'request_type'])
        combined_df[cost_field_name] = combined_df['character_cost'] * combined_df['characters']
        combined_df = combined_df.rename(columns={'characters': characters_field_name})

        grouped_df = combined_df.groupby('api_key').agg({cost_field_name: 'sum', characters_field_name: 'sum'}).reset_index()
        return grouped_df

    def get_global_usage_data(self, usage_key_pattern):
        usage_entries = self.redis_connection.list_usage(usage_key_pattern)
        # print(usage_entries)
        # clt:usage:global:monthly:202103:Amazon:translation
        records = []
        for entry in usage_entries:
            usage_key = entry['usage_key']
            components = usage_key.split(':')
            period = components[4]
            service = components[5]
            request_type = components[6]
            records.append({
                'period': period,
                'service': service,
                'request_type': request_type,
                'characters': int(entry['characters']),
                'requests': int(entry['requests'])
            })

        records_df = pandas.DataFrame(records)
        # print(records_df)

        cost_table_df = pandas.DataFrame(quotas.COST_TABLE)

        combined_df = pandas.merge(records_df, cost_table_df, how='left', on=['service', 'request_type'])
        combined_df['cost'] = combined_df['character_cost'] * combined_df['characters']

        # retain certain columns
        combined_df = combined_df[['period', 'service', 'request_type', 'cost', 'characters',  'requests']]

        return combined_df

    def get_user_tracking_data(self, api_key_list):
        logger.info('getting user tracking data')

        def process_languages(hash_data):
            language_list = hash_data.keys()
            language_name_list = [cloudlanguagetools.languages.Language[x].lang_name for x in language_list]            
            return language_name_list

        def process_languages_enum(hash_data):
            language_list = hash_data.keys()
            return language_list


        def process_tag(hash_data):
            return list(hash_data.keys())

        processing_map = {
            redisdb.KEY_TYPE_USER_AUDIO_LANGUAGE: process_languages,
            redisdb.KEY_TYPE_USER_SERVICE: process_tag,
            redisdb.KEY_TYPE_USER_CLIENT: process_tag,
            redisdb.KEY_TYPE_USER_CLIENT_VERSION: process_tag
        }

        field_name_map = {
            redisdb.KEY_TYPE_USER_AUDIO_LANGUAGE: 'detected_languages',
            redisdb.KEY_TYPE_USER_SERVICE: 'services',
            redisdb.KEY_TYPE_USER_CLIENT: 'clients',
            redisdb.KEY_TYPE_USER_CLIENT_VERSION: 'versions',
        }

        record_lists = self.redis_connection.list_user_tracking_data(api_key_list)
        processed_records_dict = {}

        for key, records in record_lists.items():
            field_name = field_name_map[key]
            processing_fn = processing_map[key]
            for record in records:
                api_key = record['api_key']
                if api_key not in processed_records_dict:
                    processed_records_dict[api_key] = {
                        'api_key': api_key
                    }
                processed_records_dict[api_key][field_name] = processing_fn(record['data'])
                if key == redisdb.KEY_TYPE_USER_AUDIO_LANGUAGE:
                    # add the enum as a string
                    processed_records_dict[api_key]['audio_language_enum'] = process_languages_enum(record['data'])

        record_list = list(processed_records_dict.values())
        return pandas.DataFrame(record_list)

    def build_user_data_patreon(self, tag_data_df, readonly=False):
        # api keys
        api_key_list = self.get_full_api_key_list()

        api_key_list_df = self.get_api_key_list_df(api_key_list, 'patreon')
        # print(api_key_list_df)
        
        # get user tracking data
        tracking_data_df = self.get_user_tracking_data(api_key_list)

        # patreon data
        patreon_user_df = self.get_patreon_users_df()
        # print(patreon_user_df)

        # get tag data from convertkit
        convertkit_users_df = self.get_convertkit_patreon_users()
        convertkit_data_df = pandas.merge(convertkit_users_df, tag_data_df, how='left', on='subscriber_id')

        # usage data
        monthly_usage_data_df = self.get_monthly_usage_data()
        prev_monthly_usage_data_df = self.get_prev_monthly_usage_data()

        combined_df = pandas.merge(api_key_list_df, patreon_user_df, how='outer', on='patreon_user_id')
        combined_df = pandas.merge(combined_df, convertkit_data_df, how='left', on='email')
        # locate missed joins, keeping in mind that not every patreon user has requested an api_key
        convertkit_missed_joins_df = combined_df[(combined_df['subscriber_id'].isnull()) & (combined_df['email'].notnull())]
        for index, row in convertkit_missed_joins_df.iterrows():
            email = row['email']
            patreon_user_id = row['patreon_user_id']
            api_key = row['api_key']
            logger.warning(f'could not locate patreon customer on convertkit email: {email} patreon_user_id: {patreon_user_id} api_key: {api_key}')

        combined_df = pandas.merge(combined_df, monthly_usage_data_df, how='left', on='api_key')
        combined_df = pandas.merge(combined_df, prev_monthly_usage_data_df, how='left', on='api_key')
        combined_df = pandas.merge(combined_df, tracking_data_df, how='left', on='api_key')

        if not readonly:
            self.update_tags_convertkit_users(combined_df)

            # update tags specific to patreon on convertkit
            self.update_tags_convertkit_patreon_users(combined_df)

        return combined_df

    def build_global_usage_data(self):
        monthly_usage_data_df = self.get_global_monthly_usage_data()
        return monthly_usage_data_df

    def build_global_daily_usage_data(self):
        usage_df = self.get_global_daily_usage_data()
        return usage_df

    def get_convertkit_trial_users(self):
        subscribers = self.convertkit_client.list_trial_users()
        return self.get_dataframe_from_subscriber_list(subscribers)

    def get_convertkit_patreon_users(self):
        logger.info(f'getting list of patreon users from convertkit')
        subscribers = self.convertkit_client.list_patreon_users()
        return self.get_dataframe_from_subscriber_list(subscribers)

    def get_convertkit_getcheddar_users(self):
        logger.info(f'getting list of getcheddar users from convertkit')
        subscribers = self.convertkit_client.list_getcheddar_users()
        return self.get_dataframe_from_subscriber_list(subscribers)

    def get_convertkit_canceled_users(self):
        canceled_list = self.convertkit_client.list_canceled()
        canceled_df = self.get_dataframe_from_subscriber_list(canceled_list)
        canceled_df['canceled'] = True
        canceled_df = canceled_df[['subscriber_id', 'canceled']]
        return canceled_df

    def get_dataframe_from_subscriber_list(self, subscribers):
        def get_int_field(subscriber, field_name):
            field_value = 0
            if subscriber['fields'][field_name] != None:
                field_value = int(subscriber['fields'][field_name])
            return field_value

        users = []
        for subscriber in subscribers:
            users.append({
                'subscriber_id': subscriber['id'],
                'email': subscriber['email_address'],
                'subscription_date': subscriber['created_at'],
                'trial_quota_usage': get_int_field(subscriber, 'trial_quota_usage')
            })
        users_df = pandas.DataFrame(users)
        # lowercase email so that merges don't fail
        users_df['email'] = users_df['email'].str.lower()
        return users_df

    def get_convertkit_dataframe_for_tag(self, tag_id, tag_name):
        logger.info(f'getting dataframe for tag {tag_name}')
        subscribers = self.convertkit_client.list_subscribers_tag(tag_id)
        if len(subscribers) == 0:
            return pandas.DataFrame()
        data_df = self.get_dataframe_from_subscriber_list(subscribers)
        data_df[tag_name] = tag_name
        data_df = data_df[['subscriber_id', tag_name]]
        return data_df

    def get_convertkit_tag_data(self, tag_ignore_list):
        logger.info(f'getting convertkit tag data, tag_ignore_list: {tag_ignore_list}')
        self.convertkit_client.populate_tag_map()

        tag_id_map = {tag_name:tag_id for tag_name, tag_id in self.convertkit_client.full_tag_id_map.items() if tag_name not in tag_ignore_list}
        present_tags = []

        dataframe_list = []
        for tag_name, tag_id in tag_id_map.items():
            data_df = self.get_convertkit_dataframe_for_tag(tag_id, tag_name)
            if len(data_df) > 0:
                dataframe_list.append(data_df)
                present_tags.append(tag_name)

        first_dataframe = dataframe_list[0]
        other_dataframes = dataframe_list[1:]
        combined_df = first_dataframe
        for data_df in other_dataframes:
            combined_df = pandas.merge(combined_df, data_df, how='outer', on='subscriber_id')
        combined_df = combined_df.fillna('')

        combined_records = []

        def get_row_tag_array(row, present_tags):
            result = []
            for tag_name in present_tags:
                result.append(row[tag_name])
            return result

        for index, row in combined_df.iterrows():
            tags = get_row_tag_array(row, present_tags)
            tags = [x for x in tags if len(x) > 0]
            combined_records.append({
                'subscriber_id': row['subscriber_id'],
                'tags': tags
            })

        final_df = pandas.DataFrame(combined_records)

        return final_df

    def build_user_data_trial(self, api_key_list, tag_data_df, readonly=False):
        # api keys
        flat_api_key_list = [x['api_key'] for x in api_key_list]

        api_key_list_df = self.get_api_key_list_df(api_key_list, 'trial')


        # get convertkit subscriber ids
        logger.info('getting convertkit trial users')
        convertkit_trial_users_df = self.get_convertkit_trial_users()

        # get convertkit canceled users
        logger.info('getting convertkit canceled users')
        canceled_df = self.get_convertkit_canceled_users()

        # get user tracking data
        logger.info('getting user tracking data')
        tracking_data_df = self.get_user_tracking_data(api_key_list)
        
        # get character entitlement
        logger.info('getting trial user entitlement')
        entitlement = self.redis_connection.get_trial_user_entitlement(flat_api_key_list)
        entitlement_df = pandas.DataFrame(entitlement)
        # get usage
        logger.info('getting trial user usage')
        api_key_usage = self.redis_connection.get_trial_user_usage(flat_api_key_list)
        api_key_usage_df = pandas.DataFrame(api_key_usage)

        # monthly usage data
        logger.info('getting monthly usage')
        monthly_usage_data_df = self.get_monthly_usage_data()
        prev_monthly_usage_data_df = self.get_prev_monthly_usage_data()

        # join data together
        logger.info('joining data')
        combined_df = pandas.merge(api_key_list_df, tracking_data_df, how='left', on='api_key')
        combined_df = pandas.merge(combined_df, convertkit_trial_users_df, how='left', on='email')
        # locate missed joins
        convertkit_missed_joins_df = combined_df[combined_df['subscriber_id'].isnull()]
        for index, row in convertkit_missed_joins_df.iterrows():
            email = row['email']
            api_key = row['api_key']
            logger.warning(f'could not locate trial customer on convertkit email: {email} api_key: {api_key}')

        combined_df = pandas.merge(combined_df, canceled_df, how='left', on='subscriber_id')
        combined_df = pandas.merge(combined_df, tag_data_df, how='left', on='subscriber_id')
        combined_df = pandas.merge(combined_df, api_key_usage_df, how='left', on='api_key')
        combined_df = pandas.merge(combined_df, entitlement_df, how='left', on='api_key')

        if len(monthly_usage_data_df) > 0:
            combined_df = pandas.merge(combined_df, monthly_usage_data_df, how='left', on='api_key')
        if len(prev_monthly_usage_data_df) > 0:
            combined_df = pandas.merge(combined_df, prev_monthly_usage_data_df, how='left', on='api_key')

        combined_df['canceled'] = combined_df['canceled'].fillna(False)

        combined_df['characters'] = combined_df['characters'].fillna(0)
        combined_df['character_limit'] = combined_df['character_limit'].fillna(0)

        combined_df['characters'] =  combined_df['characters'].astype(int)
        combined_df['character_limit'] = combined_df['character_limit'].astype(int)

        if not readonly:
            logger.info('update and tag convertkit users')
            self.update_tags_convertkit_users(combined_df)
            logger.info('update usage for convertkit trial users')
            self.update_usage_convertkit_trial_users(combined_df)

        return combined_df

    def cleanup_user_data_trial(self, api_key_list):
        logger.info('cleaning up trial users')

        api_key_list_df = self.get_api_key_list_df(api_key_list, 'trial')
        api_key_list_df = api_key_list_df[['api_key', 'email']]
        api_key_list_df['api_key_present'] = True

        # get convertkit subscriber ids
        convertkit_trial_users_df = self.get_convertkit_trial_users()
        convertkit_trial_users_df['convertkit_trial_user'] = True

        # get convertkit canceled users
        canceled_df = self.get_convertkit_canceled_users()

        # get airtable records
        airtable_trial_df = self.airtable_utils.get_trial_users()
        airtable_trial_df = airtable_trial_df[['record_id', 'email']]
        airtable_trial_df['airtable_record'] = True

        combined_df = pandas.merge(api_key_list_df, convertkit_trial_users_df, how='outer', on='email')
        combined_df = pandas.merge(combined_df, canceled_df, how='outer', on='subscriber_id')
        combined_df = pandas.merge(airtable_trial_df, combined_df, how='outer', on='email')

        combined_df['convertkit_trial_user'] = combined_df['convertkit_trial_user'].fillna(False)
        combined_df['canceled'] = combined_df['canceled'].fillna(False)
        combined_df['airtable_record'] = combined_df['airtable_record'].fillna(False)
        combined_df['api_key_present'] = combined_df['api_key_present'].fillna(False)

        # print(combined_df)
        pandas.set_option('display.max_rows', 500)

        # identify api key which are in redis but not a convertkit trial user
        remove_api_keys_df = combined_df[ (combined_df['api_key_present'] == True) & ((combined_df['convertkit_trial_user'] == False) | (combined_df['canceled'] == True))]
        logger.info(f'removing API keys for trial users')
        # print(remove_api_keys_df)
        for index, row in remove_api_keys_df.iterrows():
            email = row['email']
            api_key = row['api_key']
            # logger.info(f'removing api key for user: {row}')
            redis_trial_user_key = self.redis_connection.build_key(redisdb.KEY_TYPE_TRIAL_USER, email)
            redis_api_key = self.redis_connection.build_key(redisdb.KEY_TYPE_API_KEY, api_key)
            logger.info(f'need to delete redis keys: {redis_trial_user_key} and {redis_api_key}')
            self.redis_connection.remove_key(redis_trial_user_key, sleep=False)
            self.redis_connection.remove_key(redis_api_key, sleep=False)

        # identify airtable records which must be removed
        remove_airtable_records_df = combined_df[ (combined_df['airtable_record'] == True) & ((combined_df['convertkit_trial_user'] == False) | (combined_df['canceled'] == True))]
        logger.info(f'removing airtable records for trial users')
        # print(remove_airtable_records_df)
        record_ids = list(remove_airtable_records_df['record_id'])
        # remove duplicates
        record_ids = list(set(record_ids))
        self.airtable_utils.delete_trial_users(record_ids)

        # identify airtable records which must be added
        add_airtable_records_df = combined_df[ (combined_df['airtable_record'] == False) & (combined_df['convertkit_trial_user'] == True) & (combined_df['canceled'] == False)]
        if len(add_airtable_records_df) > 0:
            logger.info(f'the following records must be created on airtable trials table:')
            print(add_airtable_records_df)
            add_airtable_records_df = add_airtable_records_df[['email', 'subscription_date']]
            self.airtable_utils.add_trial_users(add_airtable_records_df)

    def get_getcheddar_all_customers(self):
        customer_data_list = self.getcheddar_utils.get_all_customers()
        customer_data_df = pandas.DataFrame(customer_data_list)
        customer_data_df = customer_data_df.rename(columns={'thousand_char_quota': 'plan', 'thousand_char_used': 'plan_usage'})
        customer_data_df = customer_data_df[['code', 'plan', 'plan_usage', 'status']]
        return customer_data_df

    def build_user_data_getcheddar(self, tag_data_df, readonly=False):
        # api keys
        api_key_list = self.get_full_api_key_list()
        flat_api_key_list = [x['api_key'] for x in api_key_list]

        api_key_list_df = self.get_api_key_list_df(api_key_list, cloudlanguagetools.constants.ApiKeyType.getcheddar.name)

        getcheddar_customer_data_df = self.get_getcheddar_all_customers()
        getcheddar_customer_data_df['plan_percent_used'] = getcheddar_customer_data_df['plan_usage'] / getcheddar_customer_data_df['plan']

        # get user tracking data
        tracking_data_df = self.get_user_tracking_data(api_key_list)

        # get tag data from convertkit
        convertkit_users_df = self.get_convertkit_getcheddar_users()
        convertkit_data_df = pandas.merge(convertkit_users_df, tag_data_df, how='left', on='subscriber_id')

        # usage data
        monthly_usage_data_df = self.get_monthly_usage_data()
        prev_monthly_usage_data_df = self.get_prev_monthly_usage_data()

        combined_df = pandas.merge(api_key_list_df, tracking_data_df, how='left', on='api_key')
        combined_df = pandas.merge(combined_df, convertkit_data_df, how='left', on='email')
        # locate missed joins
        convertkit_missed_joins_df = combined_df[combined_df['subscriber_id'].isnull()]
        for index, row in convertkit_missed_joins_df.iterrows():
            email = row['email']
            code = row['code']
            logger.warning(f'could not locate getcheddar customer on convertkit email: {email} code: {code}')

        combined_df = pandas.merge(combined_df, getcheddar_customer_data_df, how='left', on='code')
        if len(monthly_usage_data_df) > 0:
            combined_df = pandas.merge(combined_df, monthly_usage_data_df, how='left', on='api_key')
        if len(prev_monthly_usage_data_df) > 0:
            combined_df = pandas.merge(combined_df, prev_monthly_usage_data_df, how='left', on='api_key')

        if not readonly:
            # do this when we're in production
            self.update_tags_convertkit_users(combined_df)

            # set tags specific to getcheddar users
            self.update_tags_convertkit_getcheddar_users(combined_df)

        return combined_df

    def update_usage_convertkit_trial_users(self, data_df):
        logger.info('update_usage_convertkit_trial_users')

        # we can't update those which don't have a subscriber ids, they probably got deleted from convertkit
        valid_subscribers_df = data_df[data_df['subscriber_id'].notnull()]

        required_usage_update_df = valid_subscribers_df[valid_subscribers_df['trial_quota_usage'] != valid_subscribers_df['characters']]
        required_usage_update_df['clients'] = required_usage_update_df['clients'].fillna("").apply(list)
        required_usage_update_df['audio_languages'] = required_usage_update_df['audio_language_enum'].fillna("").apply(list)
        required_usage_update_df['tags'] = required_usage_update_df['tags'].fillna("").apply(list)
        
        logger.info('the following records require an update:')

        for index, row in required_usage_update_df.iterrows():
            # user_set_fields
            email = row['email']
            subscriber_id = row['subscriber_id']
            api_key = row['api_key']
            existing_trial_quota_usage = row['trial_quota_usage']
            fields = {'trial_quota_usage': row['characters']}

            # can we update client name ?
            tags = row['tags']
            clients = row['clients']
            if 'hypertts' in clients:
                fields['client_name'] = 'HyperTTS Pro'
            elif 'languagetools' in clients:
                fields['client_name'] = 'Language Tools'
            elif 'awesometts' in clients:
                fields['client_name'] = 'AwesomeTTS Plus'
            fields['sale_purchase_url'] = 'https://www.vocab.ai/signup'

            # update languages
            languages = row['audio_languages']
            if len(languages) > 0:
                language_name_list = [re.sub('([^\s]+)\s*.*', '\\1', cloudlanguagetools.languages.Language[language].lang_name) for language in languages]
                language_name = ', '.join(language_name_list)
                fields['language_name'] = language_name

            logger.info(f'email: [{email}] subscriber_id: [{subscriber_id}] api_key: [{api_key}] updating convertkit trial usage from {existing_trial_quota_usage} to {fields}')
            self.convertkit_client.user_set_fields(email, subscriber_id, fields)

        # identify subscribers who have used up their trial quota
        trial_max_out_df = valid_subscribers_df[valid_subscribers_df['characters'] + 200 > valid_subscribers_df['character_limit']]
        for index, row in trial_max_out_df.iterrows():
            # user_set_fields
            email = row['email']
            tags = row['tags']

            # used up trial quota
            tag_name = 'trial_maxed_out'
            if tag_name in self.convertkit_client.full_tag_id_map:
                if tag_name not in tags:
                    logger.info(f'tagging {email} with {tag_name}')
                    tag_id = self.convertkit_client.full_tag_id_map[tag_name]
                    self.convertkit_client.tag_user(email, tag_id)                



    def update_tags_convertkit_users(self, data_df):
        # perform necessary taggings on convertkit
        
        # make the logic a bit easier by removing nans
        data_df['tags'] = data_df['tags'].fillna("").apply(list)
        data_df['clients'] = data_df['clients'].fillna("").apply(list)
        data_df['services'] = data_df['services'].fillna("").apply(list)
        data_df['audio_languages'] = data_df['audio_language_enum'].fillna("").apply(list)

        for index, row in data_df.iterrows():
            email = row['email']
            tags = row['tags']
            clients = row['clients']
            services = row['services']

            for client in clients:
                tag_name = f'client_{client}'
                if tag_name in self.convertkit_client.full_tag_id_map:
                    if tag_name not in tags:
                        logger.info(f'tagging {email} with {tag_name}')
                        tag_id = self.convertkit_client.full_tag_id_map[tag_name]
                        self.convertkit_client.tag_user(email, tag_id)

            for service in services:
                service = service.lower()
                tag_name = f'service_{service}'
                if tag_name in self.convertkit_client.full_tag_id_map:
                    if tag_name not in tags:
                        logger.info(f'tagging {email} with {tag_name}')
                        tag_id = self.convertkit_client.full_tag_id_map[tag_name]
                        self.convertkit_client.tag_user(email, tag_id)                        

            audio_languages = row['audio_languages']
            for audio_language in audio_languages:
                tag_name = f'language_{audio_language}'
                if tag_name in self.convertkit_client.full_tag_id_map:
                    if tag_name not in tags:
                        logger.info(f'tagging {email} with {tag_name}')
                        tag_id = self.convertkit_client.full_tag_id_map[tag_name]
                        self.convertkit_client.tag_user(email, tag_id)                

    def update_tags_convertkit_getcheddar_users(self, data_df):
        # perform necessary taggings on convertkit getcheddar users
        logger.info('performing tag updates for getcheddar users')
        
        # make the logic a bit easier by removing nans
        data_df['tags'] = data_df['tags'].fillna("").apply(list)
        # remove users which don't have a convertkit subscriber id
        data_df = data_df.dropna(subset=['subscriber_id'])
        data_df['subscriber_id'] = data_df['subscriber_id'].astype(int)

        tag_id_active = self.convertkit_client.full_tag_id_map['getcheddar_active']
        tag_id_cancel = self.convertkit_client.full_tag_id_map['getcheddar_canceled']
        tag_id_near_max = self.convertkit_client.full_tag_id_map['getcheddar_near_max']

        for index, row in data_df.iterrows():
            status = row['status']
            email = row['email']
            subscriber_id = row['subscriber_id']
            tags = row['tags']
            near_max = row['plan_percent_used'] > 0.75 # near maxed out

            logger.info(f'processing convertkit getcheddar tags for {email} subscriber_id {subscriber_id} {status}')

            if status == 'active':
                # if tag getcheddar_active is not set, we have to set it
                if 'getcheddar_active' not in tags:
                    self.convertkit_client.tag_user(email, tag_id_active)
                # if tag getcheddar_canceled is set, we have to unset it
                if 'getcheddar_canceled' in tags:
                    self.convertkit_client.untag_user(subscriber_id, tag_id_cancel)
            elif status == 'canceled':
                # if tag getcheddar_active is set, we have to unset it
                if 'getcheddar_active' in tags:
                    self.convertkit_client.untag_user(subscriber_id, tag_id_active)
                # if tag getcheddar_canceled is not set, we have to set it
                if 'getcheddar_canceled' not in tags:
                    self.convertkit_client.tag_user(email, tag_id_cancel)
            else:
                raise Exception(f'unknown getcheddar status: {status}, {row}')

            if near_max:
                if 'getcheddar_near_max' not in tags:
                    self.convertkit_client.tag_user(email, tag_id_near_max)
            else:
                if 'getcheddar_near_max' in tags:
                    self.convertkit_client.untag_user(subscriber_id, tag_id_near_max)


    def update_tags_convertkit_patreon_users(self, data_df):
        logger.info('performing tag updates for patreon users')
        
        # make the logic a bit easier by removing nans
        data_df['tags'] = data_df['tags'].fillna("").apply(list)
        # remove users which don't have a convertkit subscriber id
        data_df = data_df.dropna(subset=['subscriber_id'])
        data_df['subscriber_id'] = data_df['subscriber_id'].astype(int)

        tag_name_active = 'patreon_active'
        tag_name_cancel = 'patreon_canceled'
        tag_id_active = self.convertkit_client.full_tag_id_map[tag_name_active]
        tag_id_cancel = self.convertkit_client.full_tag_id_map[tag_name_cancel]

        for index, row in data_df.iterrows():
            entitled = row['entitled']
            email = row['email']
            subscriber_id = row['subscriber_id']
            tags = row['tags']

            logger.info(f'processing convertkit patreon tags for {email} subscriber_id {subscriber_id} {entitled}')

            if entitled == True:
                if tag_name_active not in tags:
                    self.convertkit_client.tag_user(email, tag_id_active)
                if tag_name_cancel in tags:
                    self.convertkit_client.untag_user(subscriber_id, tag_id_cancel)
            elif entitled == False:
                if tag_name_active in tags:
                    self.convertkit_client.untag_user(subscriber_id, tag_id_active)
                if tag_name_cancel not in tags:
                    self.convertkit_client.tag_user(email, tag_id_cancel)


    def perform_airtable_trial_tag_requests(self):
        airtable_records_df = self.airtable_utils.get_trial_tag_requests()
        logger.info(f'processing {len(airtable_records_df)} tag requests')

        airtable_update_records = []

        for index, row in airtable_records_df.iterrows():
            record_id = row['record_id']
            email = row['email']
            tag_request = row['tag_request']

            # all tag requests processed the same way now
            if tag_request in self.convertkit_client.full_tag_id_map:
                tag_id = self.convertkit_client.full_tag_id_map[tag_request]
                logger.info(f'tagging {email} with {tag_request} / {tag_id}')
                self.convertkit_client.tag_user(email, tag_id)
            else:
                logger.error(f'could not tag {email} with {tag_request}: unknown tag')

            # blank out tag_request field
            airtable_update_records.append({
                'record_id': record_id,
                'tag_request': None
            })
        
        if len(airtable_update_records) > 0:
            airtable_update_df = pandas.DataFrame(airtable_update_records)
            self.airtable_utils.update_trial_users(airtable_update_df)


    def update_airtable_patreon(self, tag_data_df):
        logger.info('updating airtable for patreon users')

        user_data_df = self.build_user_data_patreon(tag_data_df)

        # get airtable patreon users table
        airtable_patreon_df = self.airtable_utils.get_patreon_users()
        airtable_patreon_df = airtable_patreon_df[['record_id', 'User ID']]

        joined_df = pandas.merge(airtable_patreon_df, user_data_df, how='left', left_on='User ID', right_on='patreon_user_id')

        update_df = joined_df[['record_id', 'entitled', 'api_key', 'api_key_valid', 'api_key_expiration', 'monthly_cost', 'monthly_chars', 'prev_monthly_cost', 'prev_monthly_chars', 'detected_languages', 'services', 'clients', 'versions']]
        update_df = update_df.fillna({
            'api_key': '',
            'api_key_valid': False,
            'entitled': False
        })

        self.airtable_utils.update_patreon_users(update_df)

    def update_airtable_trial(self, tag_data_df):
        logger.info('updating airtable for trial users')
        
        logger.info('start getting trial API keys from redis')
        api_key_list = self.get_full_api_key_list()
        logger.info('done getting trial API keys from redis')

        self.cleanup_user_data_trial(api_key_list)

        self.perform_airtable_trial_tag_requests()

        user_data_df = self.build_user_data_trial(api_key_list, tag_data_df)
        
        # find duplicate emails in user_data_df
        duplicate_emails_df = user_data_df[user_data_df.duplicated(['email'], keep=False)]
        if len(duplicate_emails_df) > 0:
            logger.warning(f"found duplicate emails in user_data_df: {duplicate_emails_df[['email', 'api_key', 'api_key_expiration', 'subscriber_id']]}")
        # remove duplicate emails
        user_data_df = user_data_df.drop_duplicates(subset=['email'], keep='first')

        # get airtable trial users table
        airtable_trial_df = self.airtable_utils.get_trial_users()
        airtable_trial_df = airtable_trial_df[['record_id', 'email']]

        joined_df = pandas.merge(airtable_trial_df, user_data_df, how='left', left_on='email', right_on='email')

        update_df = joined_df[['record_id', 'api_key', 'api_key_valid', 'api_key_expiration', 
            'characters', 'character_limit', 'monthly_cost', 'monthly_chars', 'prev_monthly_cost', 
            'prev_monthly_chars', 'detected_languages', 'services', 'clients', 'versions', 'tags', 'subscriber_id']]
        update_df['subscriber_id'] = update_df['subscriber_id'].fillna(0)
        update_df['subscriber_id'] = update_df['subscriber_id'].astype(int)

        # print(update_df)
        logger.info(f'updating airtable trial users table with columns: {update_df.dtypes}')

        self.airtable_utils.update_trial_users(update_df)

    def update_airtable_getcheddar(self, tag_data_df):
        logger.info('updating airtable for getcheddar users')

        user_data_df = self.build_user_data_getcheddar(tag_data_df)

        # get airtable trial users table
        airtable_getcheddar_df = self.airtable_utils.get_getcheddar_users()
        airtable_getcheddar_df = airtable_getcheddar_df[['record_id', 'code']]

        joined_df = pandas.merge(airtable_getcheddar_df, user_data_df, how='left', left_on='code', right_on='code')


        update_df = joined_df[['record_id', 'api_key', 'plan', 'status', 'plan_usage', 'monthly_cost', 'monthly_chars', 'prev_monthly_cost', 'prev_monthly_chars', 'detected_languages', 'services', 'clients', 'versions']]
        update_df = update_df.fillna({
            'api_key': '',
        })

        # print(update_df)

        self.airtable_utils.update_getcheddar_users(update_df)

    def update_airtable_usage(self):
        usage_df = self.build_global_usage_data()
        self.airtable_utils.update_usage(usage_df)
        usage_df = self.build_global_daily_usage_data()
        self.airtable_utils.update_usage_daily(usage_df)

    def update_airtable_all(self):
        # get convertkit tag dataframe once at startup
        logger.info('start retrieving all convertkit tag dataframes')
        tag_data_df = self.get_convertkit_tag_data(self.convertkit_client.TAG_IGNORE_LIST_GLOBAL)
        logger.info('finished retrieving all convertkit tag dataframes')
        self.update_airtable_getcheddar(tag_data_df)
        self.update_airtable_patreon(tag_data_df)
        self.update_airtable_trial(tag_data_df)
        self.update_airtable_usage()
    
    def extend_patreon_key_validity(self):
        logger.info('extending patreon key validity')
        self.patreon_utils.extend_user_key_validity()

    def extend_trial_expiration(self, api_key):
        expiration = self.redis_connection.get_api_key_expiration_timestamp_long()
        redis_api_key = self.redis_connection.build_key(redisdb.KEY_TYPE_API_KEY, api_key)
        self.redis_connection.r.hset(redis_api_key, 'expiration', expiration)
        logger.info(f'{redis_api_key}: setting expiration to {expiration}')

    def increase_trial_character_limit(self, api_key, character_limit):
        redis_api_key = self.redis_connection.build_key(redisdb.KEY_TYPE_API_KEY, api_key)
        self.redis_connection.r.hset(redis_api_key, 'character_limit', character_limit)
        logger.info(f'{redis_api_key}: setting character_limit to {character_limit}')

    def report_getcheddar_usage_all_users(self):
        api_key_list = self.redis_connection.list_getcheddar_api_keys()
        for api_key in api_key_list:
            self.report_getcheddar_user_usage(api_key)

    def report_getcheddar_user_usage(self, api_key):
        try:
            logger.info(f'reporting getcheddar usage for api key {api_key}')
            user_data = self.redis_connection.get_api_key_data(api_key)

            # retrieve getcheddar customer info
            customer_info = self.getcheddar_utils.get_customer(user_data['code'])
            if customer_info['status'] == 'canceled':
                logger.info(f'not reporting usage for api_key {api_key}, getcheddar status is canceled')
                return

            # retrieve the accumulated usage
            usage_slice = self.redis_connection.get_getcheddar_usage_slice(api_key)
            usage = self.redis_connection.get_usage_slice_data(usage_slice)
            characters = usage['characters']
            thousand_char_quantity = characters / quotas.GETCHEDDAR_CHAR_MULTIPLIER
            
            # are we very close to the max ?
            if user_data['thousand_char_overage_allowed'] != True:
                user_quota = user_data['thousand_char_quota']
                max_reportable_quantity = user_data['thousand_char_quota'] - user_data['thousand_char_used'] - 0.001
                thousand_char_quantity = max(0.0, min(max_reportable_quantity, thousand_char_quantity))

            logger.info(f'reporting usage for {api_key} ({user_data}): {thousand_char_quantity}')
            updated_user_data = self.getcheddar_utils.report_customer_usage(user_data['code'], thousand_char_quantity)
            # this will update the usage on the api_key_data
            self.redis_connection.get_update_getcheddar_user_key(updated_user_data)
            # reset the usage slice
            self.redis_connection.reset_getcheddar_usage_slice(api_key)
        except:
            logger.exception(f'could not report getcheddar usage for {api_key}')
        

    def download_audio_requests(self):
        audio_request_list = self.redis_connection.retrieve_audio_requests()
        audio_requests = [json.loads(x) for x in audio_request_list]
        # voice_key should be a string
        for request in audio_requests:
            request['voice'] = json.dumps(request['voice_key'])

        audio_requests_df = pandas.DataFrame(audio_requests)
        filename = 'temp_data_files/audio_requests.csv'
        audio_requests_df.to_csv(filename)

        logger.info(f'wrote audio requests to {filename}')
        return

        # print(audio_requests_df)

        # find duplicate requests
        # duplicate_df = audio_requests_df[audio_requests_df.duplicated(['text'])]
        # print(duplicate_df)

        # grouped_df = duplicate_df.groupby(['text']).agg({'language_code': 'count'}).reset_index()
        # print(grouped_df)

        grouped_df = audio_requests_df.groupby(['text', 'language_code', 'service', 'voice', 'api_key']).agg({'request_mode':'count'}).reset_index()
        grouped_df = grouped_df.sort_values(by='request_mode', ascending=False)
        print(grouped_df.head(50))

        if False:
            grouped_df = audio_requests_df.groupby(['text', 'language_code']).agg({'request_mode':'count'}).reset_index()
            grouped_df = grouped_df.sort_values(by='request_mode', ascending=False)
            print(grouped_df.head(50))        

    def custom_action(self):
        # custom action
        api_key = 'INSERT_API_KEY_HERE'
        redis_key = f'clt:usage:user:patreon_monthly:202308:{api_key}'
        # redis_key = f'clt:usage:user:recurring:{api_key}'
        logger.info(f'custom action on {redis_key}') 
        user_utils.redis_connection.r.hset(redis_key, 'characters', 0)
        user_utils.redis_connection.r.hset(redis_key, 'requests', 0)



if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', 
                        datefmt='%Y%m%d-%H:%M:%S',
                        level=logging.INFO)
    user_utils = UserUtils()

    parser = argparse.ArgumentParser(description='User Utils')
    choices = [
        'update_airtable_all',
        'update_airtable_patreon',
        'update_airtable_getcheddar',
        'update_airtable_trial',
        'update_airtable_usage',
        'show_getcheddar_user_data',
        'show_getcheddar_customers',
        'extend_patreon_key_validity',
        'oneoff_action',
        'extend_trial_expiration',
        'increase_trial_character_limit',
        'usage_data',
        'report_getcheddar_usage_all_users',
        'report_getcheddar_user_usage',
        'show_patreon_user_data',
        'show_trial_user_data',
        'cleanup_trial_user_data',
        'download_audio_requests'
    ]
    parser.add_argument('--action', choices=choices, help='Indicate what to do', required=True)
    parser.add_argument('--usage_service', help='for usage data, only report this service')
    parser.add_argument('--usage_period_start', type=int, help='for usage data, start of period')
    parser.add_argument('--usage_period_end', type=int, help='for usage data, start of period')
    parser.add_argument('--api_key', help='Pass in API key to check validity')
    parser.add_argument('--trial_character_limit', type=int, help='Pass in custom trial character limit')
    parser.add_argument('--email', type=str, help='if set, show details for this particular user')
    args = parser.parse_args()

    if args.action == 'update_airtable_all':
        user_utils.update_airtable_all()
    elif args.action == 'oneoff_action':
        user_utils.custom_action()
    elif args.action == 'update_airtable_patreon':
        user_utils.update_airtable_patreon()
    elif args.action == 'update_airtable_getcheddar':
        user_utils.update_airtable_getcheddar()        
    if args.action == 'update_airtable_trial':
        user_utils.update_airtable_trial()
    if args.action == 'update_airtable_usage':
        user_utils.update_airtable_usage()
    elif args.action == 'show_patreon_user_data':
        user_data_df = user_utils.build_user_data_patreon(readonly=True)
        print(user_data_df)
    elif args.action == 'show_trial_user_data':
        user_data_df = user_utils.build_user_data_trial(readonly=True)
        print(user_data_df)
        print(user_data_df.dtypes)
    elif args.action == 'cleanup_trial_user_data':
        user_utils.cleanup_user_data_trial()
    elif args.action == 'show_getcheddar_customers':
        customers_df = user_utils.get_getcheddar_all_customers()
        print(customers_df)
    elif args.action == 'show_getcheddar_user_data':
        user_data_df = user_utils.build_user_data_getcheddar(readonly=True)
        print(user_data_df)        
        print(user_data_df.dtypes)
        if args.email != None:
            pprint.pprint(user_data_df[user_data_df['email'] == args.email].to_dict(orient='records'))
    elif args.action == 'extend_patreon_key_validity':
        user_utils.extend_patreon_key_validity()    
    elif args.action == 'extend_trial_expiration':
        # python user_utils.py --action extend_trial_expiration --api_key <api_key>
        api_key = args.api_key
        user_utils.extend_trial_expiration(api_key)
    elif args.action == 'increase_trial_character_limit':
        # python user_utils.py --action extend_trial_expiration --api_key <api_key>
        api_key = args.api_key
        character_limit = args.trial_character_limit
        user_utils.increase_trial_character_limit(api_key, character_limit)
    elif args.action == 'usage_data':
        pandas.set_option('display.max_rows', 999)
        # user_utils.build_global_usage_data()
        data_df = user_utils.build_global_daily_usage_data()
        data_df['period'] = data_df['period'].astype(int)
        data_df = data_df.sort_values('period', ascending=True)
        if args.usage_service != None:
            data_df = data_df[data_df['service'] == args.usage_service]
        if args.usage_period_start != None:
            data_df = data_df[data_df['period'] >= args.usage_period_start]
        if args.usage_period_end != None:
            data_df = data_df[data_df['period'] <= args.usage_period_end]
        print(data_df)
    elif args.action == 'report_getcheddar_usage_all_users':
        user_utils.report_getcheddar_usage_all_users()
    elif args.action == 'report_getcheddar_user_usage':
        api_key = args.api_key
        user_utils.report_getcheddar_user_usage(api_key)        
    elif args.action == 'download_audio_requests':
        user_utils.download_audio_requests()
