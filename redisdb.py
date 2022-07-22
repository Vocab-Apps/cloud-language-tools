import os
import time
import datetime
import redis
import json
import string
import random
import logging
import cloudlanguagetools.constants
import cloudlanguagetools.errors
import quotas
import clt_secrets as secrets

KEY_TYPE_API_KEY = 'api_key'
KEY_TYPE_PATREON_USER ='patreon_user'
KEY_TYPE_TRIAL_USER = 'trial_user'
KEY_TYPE_GETCHEDDAR_USER = 'getcheddar_user'
KEY_TYPE_USAGE ='usage'
KEY_TYPE_USER_CLIENT ='user_client'
KEY_TYPE_USER_CLIENT_VERSION ='user_client_version'
KEY_TYPE_USER_REQUEST_MODE ='user_request_mode'
KEY_TYPE_USER_SERVICE ='user_service'
KEY_TYPE_USER_AUDIO_LANGUAGE ='user_audio_language'
KEY_TYPE_AUDIO_LOG ='audio_log'

KEY_PREFIX = 'clt'

LANGUAGE_DATA_KEY = 'language_data_v1'

class RedisDb():
    def __init__(self):
        self.connect()

    def connect(self, db_num=0):
        redis_url = secrets.config['redis_url']
        logging.info(f'connecting to redis url: {redis_url}, db_num: {db_num}')

        self.r = redis.from_url(redis_url, db=db_num, decode_responses=True)

    def build_key(self, key_type, key):
        return f'{KEY_PREFIX}:{key_type}:{key}'

    def build_global_key(self, key):
        return f'{KEY_PREFIX}:{key}'

    def store_language_data(self, language_data):
        redis_key = self.build_global_key(LANGUAGE_DATA_KEY)
        logging.info(f'storing language_data into {redis_key}')
        self.r.set(redis_key, json.dumps(language_data))

    def get_language_data(self):
        redis_key = self.build_global_key(LANGUAGE_DATA_KEY)
        return json.loads(self.r.get(redis_key))


    def build_monthly_user_key(self, key_type, api_key, prev_month=False):
        if prev_month:
            date = datetime.datetime.now() + datetime.timedelta(days=-28)
        else:
            date = datetime.datetime.now()
        date_str = date.strftime('%Y%m')
        redis_key = self.build_key(key_type, f'{date_str}:{api_key}')
        return redis_key

    def get_specific_api_key_expiration_timestamp(self, delta_days):
        expiration_date = datetime.datetime.now() + datetime.timedelta(days=delta_days)
        key_expiration_timestamp = int(expiration_date.timestamp())
        return key_expiration_timestamp    

    def get_api_key_expiration_timestamp(self):
        expiration_date = datetime.datetime.now() + datetime.timedelta(days=45)
        key_expiration_timestamp = int(expiration_date.timestamp())
        return key_expiration_timestamp

    def get_api_key_expiration_timestamp_medium(self):
        return self.get_specific_api_key_expiration_timestamp(90)

    def get_api_key_expiration_timestamp_long(self):
        return self.get_specific_api_key_expiration_timestamp(180)

    def add_test_api_key(self, api_key):
        redis_key = self.build_key(KEY_TYPE_API_KEY, api_key)
        hash_value = {
            'expiration': self.get_api_key_expiration_timestamp(),
            'type': cloudlanguagetools.constants.ApiKeyType.test.name
        }
        self.r.hset(redis_key, mapping=hash_value)
        logging.info(f'added {redis_key}: {hash_value}')

    # prod workflow (app.py/patreon_key)
    def add_patreon_api_key(self, api_key, user_id, email):
        redis_key = self.build_key(KEY_TYPE_API_KEY, api_key)
        hash_value = {
            'user_id': user_id,
            'email': email,
            'expiration': self.get_api_key_expiration_timestamp(),
            'type': cloudlanguagetools.constants.ApiKeyType.patreon.name
        }
        self.r.hset(redis_key, mapping=hash_value)
        logging.info(f'added {redis_key}: {hash_value}')

    def add_trial_api_key(self, api_key, email, character_limit):
        redis_key = self.build_key(KEY_TYPE_API_KEY, api_key)
        hash_value = {
            'email': email,
            'expiration': self.get_api_key_expiration_timestamp_medium(),
            'type': cloudlanguagetools.constants.ApiKeyType.trial.name,
            'character_limit': character_limit
        }
        self.r.hset(redis_key, mapping=hash_value)
        logging.info(f'added {redis_key}: {hash_value}')        
        
    # prod workflow
    def normalize_trial_email(self, email):
        return email.lower()

    def trial_user_key_exists(self, email):
        email = self.normalize_trial_email(email)
        redis_trial_user_key = self.build_key(KEY_TYPE_TRIAL_USER, email)
        if self.r.exists(redis_trial_user_key):
            return True
        return False
        
    def get_trial_user_key(self, email):
        email = self.normalize_trial_email(email)
        redis_trial_user_key = self.build_key(KEY_TYPE_TRIAL_USER, email)
        if self.r.exists(redis_trial_user_key):
            # user already requested a key
            api_key = self.r.get(redis_trial_user_key)
            redis_api_key = self.build_key(KEY_TYPE_API_KEY, api_key)
            if not self.r.exists(redis_api_key):
                # add the key back in
                self.add_trial_api_key(api_key, email, quotas.TRIAL_USER_CHARACTER_LIMIT)
            return api_key
        
        # need to create a new key
        api_key = self.password_generator()
        self.add_trial_api_key(api_key, email, quotas.TRIAL_USER_CHARACTER_LIMIT)

        # map to the patreon user
        self.r.set(redis_trial_user_key, api_key)
        logging.info(f'added mapping: trial user: email: {email} ({redis_trial_user_key})')

        return api_key
    
    def increase_trial_key_limit(self, email, character_limit):
        redis_trial_user_key = self.build_key(KEY_TYPE_TRIAL_USER, email)
        if self.r.exists(redis_trial_user_key):
            api_key = self.r.get(redis_trial_user_key)
            redis_api_key = self.build_key(KEY_TYPE_API_KEY, api_key)

            # set character limit
            self.r.hset(redis_api_key, 'character_limit', character_limit)

            expiration = self.get_api_key_expiration_timestamp_long()
            self.r.hset(redis_api_key, 'expiration', expiration)

            logging.info(f'increased character limit to {character_limit} for {email} {api_key} and set expiration to {expiration}')


    # prod workflow (app.py/patreon_key)
    def get_patreon_user_key(self, user_id, email):
        logging.info(f'patreon user: {user_id}, email: {email}')

        redis_patreon_user_key = self.build_key(KEY_TYPE_PATREON_USER, user_id)
        if self.r.exists(redis_patreon_user_key):
            logging.info(f'mapping exists: patreon user: {user_id}, email: {email} mapping: {redis_patreon_user_key}')
            
            # user already requested a key
            api_key = self.r.get(redis_patreon_user_key)
            redis_api_key = self.build_key(KEY_TYPE_API_KEY, api_key)
            if self.r.exists(redis_api_key):
                # update expiry time
                expiration_timestamp = self.get_api_key_expiration_timestamp()
                logging.info(f'refreshing expiration date of api key: patreon user: {user_id}, email: {email} updating key removal time ({redis_api_key} / {expiration_timestamp})')
                self.r.hset(redis_api_key, 'expiration', expiration_timestamp)
            else:
                # add the key back in
                self.add_patreon_api_key(api_key, user_id, email)
            return api_key
        
        # need to create a new key
        api_key = self.password_generator()
        self.add_patreon_api_key(api_key, user_id, email)

        # map to the patreon user
        self.r.set(redis_patreon_user_key, api_key)
        logging.info(f'added mapping: patreon user: {user_id}, email: {email} ({redis_patreon_user_key})')

        return api_key

    # prod workflow (app.py/patreon_key)
    def get_update_getcheddar_user_key(self, user_data):
        user_code = user_data['code']
        email = user_data['email']
        logging.info(f'getcheddar user: {user_code}, email: {email}')

        # do we need to create the API key mapping ?
        redis_getcheddar_user_key = self.build_key(KEY_TYPE_GETCHEDDAR_USER, user_code)
        if not self.r.exists(redis_getcheddar_user_key):
            # create new API key
            api_key = self.password_generator()
            logging.info(f'created new api_key {api_key} for {user_code}')
            self.r.set(redis_getcheddar_user_key, api_key)
        else:
            api_key = self.r.get(redis_getcheddar_user_key)
            logging.info(f'api_key is {api_key} for {user_code}')

        # update user data
        redis_key = self.build_key(KEY_TYPE_API_KEY, api_key)
        user_data['type'] = cloudlanguagetools.constants.ApiKeyType.getcheddar.name
        logging.info(f'setting user_data {user_data} on {redis_key}')
        self.r.hset(redis_key, mapping=user_data)

        # return api key so it can be used to communicate to the user
        return api_key
    
    def get_getcheddar_user_data(self, user_code):
        redis_getcheddar_user_key = self.build_key(KEY_TYPE_GETCHEDDAR_USER, user_code)
        api_key = self.r.get(redis_getcheddar_user_key)
        return self.get_api_key_data(api_key)

    def delete_getcheddar_user(self, user_code):
        logging.warning(f'deleting getcheddar user {user_code}')
        redis_getcheddar_user_key = self.build_key(KEY_TYPE_GETCHEDDAR_USER, user_code)
        api_key = self.r.get(redis_getcheddar_user_key)
        redis_api_key = self.build_key(KEY_TYPE_API_KEY, api_key)

        # delete both
        self.r.delete(redis_getcheddar_user_key)
        self.r.delete(redis_api_key)



    def list_getcheddar_api_keys(self):
        pattern = self.build_key(KEY_TYPE_GETCHEDDAR_USER, '*')
        customer_api_key_map_list = []

        logging.info('scanning list of getcheddar users from redis')
        cursor = '0'
        while cursor != 0:
            cursor, keys = self.r.scan(cursor=cursor, match=pattern, count=100)
            for key in keys:
                customer_api_key_map_list.append(key)

        logging.info('getting API key list')
        pipe = self.r.pipeline()
        for redis_key in customer_api_key_map_list:
            pipe.get(redis_key)
        api_key_list = pipe.execute()

        return api_key_list


    def password_generator(self):

        LETTERS = string.ascii_letters
        NUMBERS = string.digits  
        
        # create alphanumerical from string constants
        printable = f'{LETTERS}{NUMBERS}'

        # convert printable from string to list and shuffle
        printable = list(printable)
        random.shuffle(printable)

        # generate random password and convert to string
        random_password = random.choices(printable, k=16)
        random_password = ''.join(random_password)
        return random_password

    def show_key_data(self, api_key):
        redis_key = self.build_key(KEY_TYPE_API_KEY, api_key)
        key_data = self.r.hgetall(redis_key)
        logging.info(key_data)

    def transform_api_key_data_test(self, api_key_data):
        api_key_data['expiration'] = int(api_key_data['expiration'])
        return api_key_data

    def transform_api_key_data_patreon(self, api_key_data):
        api_key_data['expiration'] = int(api_key_data['expiration'])
        return api_key_data

    def transform_api_key_data_trial(self, api_key_data):
        api_key_data['expiration'] = int(api_key_data['expiration'])
        api_key_data['character_limit'] = int(api_key_data['character_limit'])
        return api_key_data

    def transform_api_key_data_getcheddar(self, api_key_data):
        api_key_data['thousand_char_quota'] = int(api_key_data['thousand_char_quota'])
        api_key_data['thousand_char_overage_allowed'] = int(api_key_data['thousand_char_overage_allowed'])
        api_key_data['thousand_char_used'] = float(api_key_data['thousand_char_used'])        
        return api_key_data

    def get_api_key_data(self, api_key):
        redis_key = self.build_key(KEY_TYPE_API_KEY, api_key)
        api_key_data = self.r.hgetall(redis_key)
        if len(api_key_data) == 0:
            raise cloudlanguagetools.errors.ApiKeyNotFoundError()

        transform_map = {
            cloudlanguagetools.constants.ApiKeyType.test.name: self.transform_api_key_data_test,
            cloudlanguagetools.constants.ApiKeyType.patreon.name: self.transform_api_key_data_patreon,
            cloudlanguagetools.constants.ApiKeyType.trial.name: self.transform_api_key_data_trial,
            cloudlanguagetools.constants.ApiKeyType.getcheddar.name: self.transform_api_key_data_getcheddar
        }
        
        return transform_map[api_key_data['type']](api_key_data)

    def get_account_data(self, api_key):
        try:
            api_key_data = self.get_api_key_data(api_key)

            if api_key_data['type'] == cloudlanguagetools.constants.ApiKeyType.test.name:
                return {'type': 'test'}

            if api_key_data['type'] == cloudlanguagetools.constants.ApiKeyType.trial.name:
                usage_slice = quotas.UsageSlice(None, 
                                cloudlanguagetools.constants.UsageScope.User, 
                                cloudlanguagetools.constants.UsagePeriod.lifetime, 
                                None, 
                                api_key,
                                api_key_data['type'],
                                api_key_data)
                usage_data = self.get_usage_slice_data(usage_slice)
                characters_str = f"""{usage_data['characters']:,}"""
                return {
                    'email': api_key_data['email'],
                    'type': 'Trial',
                    'usage': f'{characters_str} characters'
                }

            if api_key_data['type'] == cloudlanguagetools.constants.ApiKeyType.patreon.name:
                usage_slice = quotas.UsageSlice(None, 
                                cloudlanguagetools.constants.UsageScope.User, 
                                cloudlanguagetools.constants.UsagePeriod.patreon_monthly, 
                                None, 
                                api_key,
                                api_key_data['type'],
                                api_key_data)
                usage_data = self.get_usage_slice_data(usage_slice)
                characters_str = f"""{usage_data['characters']:,}"""                              
                return {
                    'email': api_key_data['email'],
                    'type': 'Patreon',
                    'usage': f'{characters_str} characters'
                }

            if api_key_data['type'] == cloudlanguagetools.constants.ApiKeyType.getcheddar.name:
                account_type = f"""{api_key_data['thousand_char_quota']},000 characters"""

                usage_slice = quotas.UsageSlice(None, 
                                cloudlanguagetools.constants.UsageScope.User, 
                                cloudlanguagetools.constants.UsagePeriod.recurring, 
                                None, 
                                api_key,
                                api_key_data['type'],
                                api_key_data)
                usage_data = self.get_usage_slice_data(usage_slice)

                reported_usage = int(api_key_data['thousand_char_used'] * quotas.GETCHEDDAR_CHAR_MULTIPLIER)
                total_usage = usage_data['characters'] + reported_usage

                characters_str = f"""{total_usage:,}"""

                return {
                    'email': api_key_data['email'],
                    'type': account_type,
                    'usage': f'{characters_str} characters',
                    'update_url': api_key_data.get('update_url', None),
                    'cancel_url': api_key_data.get('cancel_url', None)
                }

            raise Exception(f"""unsupported api key type: {api_key_data['type']}""")
        except cloudlanguagetools.errors.ApiKeyNotFoundError:
            return {
                'error': 'API Key not found'
            }



    def api_key_valid(self, api_key):
        redis_key = self.build_key(KEY_TYPE_API_KEY, api_key)
        if self.r.exists(redis_key) == 0:
            return {'key_valid': False, 'msg': 'API Key not valid'}
        key_data = self.r.hgetall(redis_key)

        if key_data['type'] == cloudlanguagetools.constants.ApiKeyType.getcheddar.name:
            # no expiration
            return {'key_valid': True, 'msg': f'API Key is valid'}

        expiration = self.r.hget(redis_key, 'expiration')
        expiration_timestamp = int(self.r.hget(redis_key, 'expiration'))
        current_dt = datetime.datetime.now()
        current_timestamp = int(current_dt.timestamp())
        expiration_dt = datetime.datetime.fromtimestamp(expiration_timestamp)
        if expiration_timestamp > current_timestamp:
            expire_time_delta = expiration_dt - current_dt
            return {'key_valid': True, 'msg': f'API Key is valid'}
        return {'key_valid': False, 'msg':f'API Key expired'}
        
    def list_api_keys(self):
        result = []
        pattern = self.build_key(KEY_TYPE_API_KEY, '*')
        redis_api_key_list = []

        logging.info('scanning list of API keys from redis')
        cursor = '0'
        while cursor != 0:
            cursor, keys = self.r.scan(cursor=cursor, match=pattern, count=100)
            for key in keys:
                redis_api_key_list.append(key)

        # get key data for all keys
        logging.info('getting data for all API keys')
        pipe = self.r.pipeline()
        for redis_api_key in redis_api_key_list:
            pipe.hgetall(redis_api_key)
        hashes = pipe.execute()
        for redis_api_key, value in zip(redis_api_key_list, hashes):
            api_key = redis_api_key.split(':')[-1]
            result.append({
                'api_key': api_key,
                'key_data': value
            })

        return result

    def list_all_keys(self):
        for key in self.r.scan_iter(count=100):
            print(f'key: [{key}]')
            # key_ttl = self.r.ttl(key)
            # expiration = 'permanent'
            # if key_ttl != -1:
            #     # note: the digital ocean redis DB seems to return a ttl in number of seconds
            #     expire_distance = datetime.timedelta(seconds=key_ttl)
            #     expiration = f'expire: {expire_distance.days} days ({expire_distance.seconds} seconds) [ttl: {key_ttl}]' 
            # print(f'key: [{key}] ({expiration})')

    # default expire time for usage-style keys
    def get_expire_time_usage(self):
        expire_time_seconds = 30*3*24*3600 # 3 months
        return expire_time_seconds

    def log_audio_request(self, api_key, data):
        date_str = datetime.datetime.today().strftime('%Y%m')
        redis_key = self.build_key(KEY_TYPE_AUDIO_LOG, date_str)
        data['api_key'] = api_key
        data['timestamp'] = int(datetime.datetime.now().timestamp())
        value_str = json.dumps(data)
        self.r.rpush(redis_key, value_str)
        self.r.expire(redis_key, self.get_expire_time_usage())

    def track_audio_language(self, api_key, language_code):
        redis_key = self.build_monthly_user_key(KEY_TYPE_USER_AUDIO_LANGUAGE, api_key)
        self.r.hincrby(redis_key, language_code.name, 1)
        self.r.expire(redis_key, self.get_expire_time_usage())

    def track_service(self, api_key, service):
        redis_key = self.build_monthly_user_key(KEY_TYPE_USER_SERVICE, api_key)
        self.r.hincrby(redis_key, service.name, 1)
        self.r.expire(redis_key, self.get_expire_time_usage())        

    def track_client(self, api_key, client_str, version):
        # keep track of the client used
        client = cloudlanguagetools.constants.Client[client_str]
        redis_key = self.build_monthly_user_key(KEY_TYPE_USER_CLIENT, api_key)
        self.r.hincrby(redis_key, client.name, 1)
        self.r.expire(redis_key, self.get_expire_time_usage())
        # keep track of version used
        client_version = f'{client_str}_{version}'
        redis_key = self.build_monthly_user_key(KEY_TYPE_USER_CLIENT_VERSION, api_key)
        self.r.hincrby(redis_key, client_version, 1)
        self.r.expire(redis_key, self.get_expire_time_usage())

    def track_request_mode(self, api_key, request_mode):
        # keep track of the client used
        redis_key = self.build_monthly_user_key(KEY_TYPE_USER_REQUEST_MODE, api_key)
        self.r.hincrby(redis_key, request_mode.name, 1)
        self.r.expire(redis_key, self.get_expire_time_usage())    

    def get_usage_slice_data(self, usage_slice):
        key = self.build_key(KEY_TYPE_USAGE, usage_slice.build_key_suffix())

        def convert_usage(usage_output):
            if usage_output == None:
                return 0
            return int(usage_output)

        return {
            'characters': convert_usage(self.r.hget(key, 'characters')),
            'requests': convert_usage(self.r.hget(key, 'requests'))
        }


    def get_getcheddar_usage_slice(self, api_key):
        api_key_data = self.get_api_key_data(api_key)
        usage_slice = quotas.UsageSlice(None, 
                        cloudlanguagetools.constants.UsageScope.User, 
                        cloudlanguagetools.constants.UsagePeriod.recurring, 
                        None, 
                        api_key,
                        cloudlanguagetools.constants.ApiKeyType.getcheddar,
                        api_key_data)
        return usage_slice

    def reset_getcheddar_usage_slice(self, api_key):
        usage_slice = self.get_getcheddar_usage_slice(api_key)
        redis_key = self.build_key(KEY_TYPE_USAGE, usage_slice.build_key_suffix())
        self.r.hset(redis_key, mapping={
            'characters': 0,
            'requests': 0
        })


    def track_usage(self, api_key, service, request_type, characters: int, language_code=None):
        expire_time_seconds = 30*3*24*3600 # 3 months

        if language_code != None:
            # azure has special character counting based on language
            characters = quotas.adjust_character_count(service, request_type, language_code, characters)

        redis_api_key = self.build_key(KEY_TYPE_API_KEY, api_key)
        key_type_str = self.r.hget(redis_api_key, 'type')
        key_type = cloudlanguagetools.constants.ApiKeyType[key_type_str]

        api_key_data = self.get_api_key_data(api_key)


        usage_slice_list = [
            quotas.UsageSlice(request_type, 
                              cloudlanguagetools.constants.UsageScope.User, 
                              cloudlanguagetools.constants.UsagePeriod.daily, 
                              service, 
                              api_key,
                              key_type,
                              api_key_data),
            quotas.UsageSlice(request_type, 
                              cloudlanguagetools.constants.UsageScope.User, 
                              cloudlanguagetools.constants.UsagePeriod.monthly, 
                              service, 
                              api_key,
                              key_type,
                              api_key_data),
            quotas.UsageSlice(request_type, 
                              cloudlanguagetools.constants.UsageScope.User, 
                              cloudlanguagetools.constants.UsagePeriod.lifetime, 
                              service, 
                              api_key,
                              key_type,
                              api_key_data),                              
            quotas.UsageSlice(request_type, 
                              cloudlanguagetools.constants.UsageScope.Global, 
                              cloudlanguagetools.constants.UsagePeriod.daily, 
                              service, 
                              api_key,
                              key_type,
                              api_key_data),
            quotas.UsageSlice(request_type, 
                              cloudlanguagetools.constants.UsageScope.Global, 
                              cloudlanguagetools.constants.UsagePeriod.monthly, 
                              service, 
                              api_key,
                              key_type,
                              api_key_data),
        ]

        if key_type == cloudlanguagetools.constants.ApiKeyType.getcheddar:
            # track the recurring usage for getcheddar users
            # this is also the only usage slice which will block for getchedar users
            usage_slice_list.append(
                quotas.UsageSlice(request_type, 
                                cloudlanguagetools.constants.UsageScope.User, 
                                cloudlanguagetools.constants.UsagePeriod.recurring, 
                                service, 
                                api_key,
                                key_type,
                                api_key_data))

        if key_type == cloudlanguagetools.constants.ApiKeyType.patreon:
            # for now track only, and after 2021/06, this can be blocking
            usage_slice_list.append(
                quotas.UsageSlice(request_type, 
                                cloudlanguagetools.constants.UsageScope.User, 
                                cloudlanguagetools.constants.UsagePeriod.patreon_monthly, 
                                service, 
                                api_key,
                                key_type,
                                api_key_data))

        def convert_usage(usage_output):
            if usage_output == None:
                return 0
            return int(usage_output)

        # do a pre check to see whether the current request would put us over the quota
        for usage_slice in usage_slice_list:
            key = self.build_key(KEY_TYPE_USAGE, usage_slice.build_key_suffix())
            current_quota_characters = convert_usage(self.r.hget(key, 'characters'))
            current_quota_requests = convert_usage(self.r.hget(key, 'requests'))
            
            if usage_slice.over_quota(current_quota_characters + characters, current_quota_requests + 1):
                error_msg = f'Exceeded {usage_slice.usage_scope.name} {usage_slice.usage_period.name} quota)'
                raise cloudlanguagetools.errors.OverQuotaError(error_msg)        

        # track usage
        for usage_slice in usage_slice_list:
            key = self.build_key(KEY_TYPE_USAGE, usage_slice.build_key_suffix())
            self.r.hincrby(key, 'characters', characters)
            self.r.hincrby(key, 'requests', 1)
            self.r.expire(key, expire_time_seconds)

    def reset_trial_usage(self, api_key):
        logging.info(f'resetting trial usage for {api_key}')
        expire_time_seconds = 30*3*24*3600 # 3 months
        usage_slice = quotas.UsageSlice(None, 
                            cloudlanguagetools.constants.UsageScope.User, 
                            cloudlanguagetools.constants.UsagePeriod.lifetime, 
                            None, 
                            api_key,
                            cloudlanguagetools.constants.ApiKeyType.trial,
                            {})
        key = self.build_key(KEY_TYPE_USAGE, usage_slice.build_key_suffix())
        self.r.hset(key, 'characters', 0)
        self.r.hset(key, 'requests', 0)
        self.r.expire(key, expire_time_seconds)

    def retrieve_audio_requests_for_key(self, redis_key):
        total_count = self.r.llen(redis_key)
        logging.info(f'audio request list: {total_count}')

        batch_size = 1000

        continue_loop = True
        current_index = 0
        audio_requests = []
        while continue_loop:
            logging.info(f'retrieving from {current_index}, length {batch_size} continue: {continue_loop}')
            current_batch = self.r.lrange(redis_key, current_index, current_index + batch_size - 1)
            audio_requests.extend(current_batch)

            if len(current_batch) < batch_size:
                continue_loop = False
            
            current_index += batch_size

        logging.info(f'final count: {len(audio_requests)}')

        return audio_requests

    def retrieve_audio_requests(self):
        logging.info('retrieving current month audio requests')
        date_str = datetime.datetime.today().strftime('%Y%m')
        redis_key = self.build_key(KEY_TYPE_AUDIO_LOG, date_str)
        current_month_requests = self.retrieve_audio_requests_for_key(redis_key)

        logging.info('retrieving prev month audio requests')
        date_str = (datetime.datetime.now() + datetime.timedelta(days=-28)).strftime('%Y%m')
        redis_key = self.build_key(KEY_TYPE_AUDIO_LOG, date_str)
        prev_month_requests = self.retrieve_audio_requests_for_key(redis_key)        

        return current_month_requests + prev_month_requests



    def list_user_tracking_data(self, api_key_entry_list):

        # process api key list
        api_key_list = [x['api_key'] for x in api_key_entry_list]

        monthly_user_key_types = [
            KEY_TYPE_USER_AUDIO_LANGUAGE,
            KEY_TYPE_USER_SERVICE,
            KEY_TYPE_USER_CLIENT,
            KEY_TYPE_USER_CLIENT_VERSION
        ]

        record_lists = {}

        i = 0
        batch_size = 80
        total_length = len(api_key_list)
        while len(api_key_list) > 0:
            # logging.info(f'requesting batch {i} (total length {total_length})')
            split_len = min(len(api_key_list), batch_size)
            current_batch = api_key_list[:split_len]
            api_key_list = api_key_list[split_len:]

            for key_type in monthly_user_key_types:
                if key_type not in record_lists:
                    record_lists[key_type] = []
                pipe_1 = self.r.pipeline()
                pipe_2 = self.r.pipeline()
                for api_key in current_batch:
                    redis_key = self.build_monthly_user_key(key_type, api_key)
                    pipe_1.hgetall(redis_key)
                    redis_key = self.build_monthly_user_key(key_type, api_key, prev_month=True)
                    pipe_2.hgetall(redis_key)
                hashes_1 = pipe_1.execute()
                hashes_2 = pipe_2.execute()
                for key, hash_data_1, hash_data_2 in zip(current_batch, hashes_1, hashes_2):
                    user_hash_data = {}
                    user_hash_data.update(hash_data_1)
                    user_hash_data.update(hash_data_2)
                    if len(user_hash_data) > 0:
                        # logging.info(f'key: {key} hash_data: {hash_data}')
                        record_lists[key_type].append({
                            'api_key': key,
                            'data': user_hash_data
                        })
            i += 1
        
        return record_lists


    def list_usage(self, scan_pattern):
        # first, build list of keys
        if scan_pattern == None:
            pattern = self.build_key(KEY_TYPE_USAGE, '*')
        else:
            pattern = self.build_key(scan_pattern, '*')

        logging.info(f'listing usage with pattern {pattern}')
        
        key_list = []
        cursor = '0'
        while cursor != 0:
            cursor, keys = self.r.scan(cursor=cursor, match=pattern, count=100)
            key_list.extend(keys)
        pipe = self.r.pipeline()
        for key in key_list:
            pipe.hgetall(key)
        hashes = pipe.execute()
        usage_entries = []
        for key, hash_data in zip(key_list, hashes):
            usage_entry = {
                'usage_key': key
            }
            usage_entry.update(hash_data)
            usage_entries.append(usage_entry)
        return usage_entries
        
    def list_trial_users(self):
        pattern = self.build_key(KEY_TYPE_TRIAL_USER, '*')
        api_key_list = []
        cursor = '0'
        while cursor != 0:
            cursor, keys = self.r.scan(cursor=cursor, match=pattern, count=100)
            pipe = self.r.pipeline()
            for key in keys:
                pipe.get(key)
            key_values = pipe.execute()
            for key, value in zip(keys, key_values):
                api_key_list.append(value)

        # get trial user data
        pipe = self.r.pipeline()
        for api_key in api_key_list:
            redis_api_key = self.build_key(KEY_TYPE_API_KEY, api_key)
            pipe.hgetall(redis_api_key)
        user_data = pipe.execute()

        # get current usage
        pipe = self.r.pipeline()
        for api_key in api_key_list:
            redis_usage = self.build_key(KEY_TYPE_USAGE, f'user:lifetime:{api_key}')
            # print(redis_usage)
            pipe.hgetall(redis_usage)
        usage_data = pipe.execute()

        for api_key, user, usage in zip(api_key_list, user_data, usage_data):
            print(f'{api_key}: {user}, {usage}')

    def get_trial_user_entitlement(self, api_key_list):
        pipe = self.r.pipeline()
        for api_key in api_key_list:
            redis_usage = self.build_key(KEY_TYPE_API_KEY, api_key)
            pipe.hget(redis_usage, 'character_limit')
        usage_data = pipe.execute()
        entries = []
        for api_key, characters in zip(api_key_list, usage_data):
            entries.append({'api_key': api_key, 'character_limit': characters})
        return entries

    def get_trial_user_usage(self, api_key_list):
        pipe = self.r.pipeline()
        for api_key in api_key_list:
            redis_usage = self.build_key(KEY_TYPE_USAGE, f'user:lifetime:{api_key}')
            # print(redis_usage)
            pipe.hget(redis_usage, 'characters')
        usage_data = pipe.execute()
        entries = []
        for api_key, characters in zip(api_key_list, usage_data):
            # print(f'api_key: {api_key} characters: {characters}')
            entries.append({'api_key': api_key, 'characters': characters})
        return entries
    
    def show_hash_key(self, redis_key):
        hash_data = self.r.hgetall(redis_key)
        logging.info(f'{redis_key}: {hash_data}')

    def show_string_key(self, redis_key):
        str_data = self.r.get(redis_key)
        logging.info(f'{redis_key}: {str_data}')        

    def remove_key(self, redis_key, sleep=True):
        logging.warn(f'WARNING about to remove key: {redis_key}')
        if sleep:
            time.sleep(15)
        self.r.delete(redis_key)

    def full_db_dump(self):

        hash_key_list = []
        string_key_list = []

        key_list = []

        logging.info('obtaining full list of keys')
        cursor = '0'
        while cursor != 0:
            cursor, keys = self.r.scan(cursor=cursor, count=1000)
            key_list.extend(keys)
            logging.info(f'collected {len(key_list)} keys')
        logging.info('finished getting full list of keys')

        logging.info('getting key types')
        pipe = self.r.pipeline(transaction=False)
        for redis_key in key_list:
            pipe.type(redis_key)
        key_types = pipe.execute()
        for redis_key, key_type in zip(key_list, key_types):
            if key_type == 'hash':
                hash_key_list.append(redis_key)
            elif key_type == 'string':
                string_key_list.append(redis_key)
        logging.info('finished getting key types')

        logging.info(f'getting full key dump')

        full_key_map = {}

        # get hash keys
        logging.info('getting hash data')
        pipe = self.r.pipeline(transaction=False)
        for hash_key in hash_key_list:
            pipe.hgetall(hash_key)
        hash_values = pipe.execute()
        for hash_key, hash_value in zip(hash_key_list, hash_values):            
            full_key_map.update({hash_key: hash_value})

        logging.info('getting string data')
        pipe = self.r.pipeline(transaction=False)
        for string_key in string_key_list:
            pipe.get(string_key)
        string_values = pipe.execute()
        for string_key, string_value in zip(string_key_list, string_values):
            full_key_map.update({string_key: string_value})

        logging.info(f'finished getting full key dump')
        return full_key_map

    def restore_db_backup(self, json_file_path):
        if os.environ['ENV'] != 'local':
            raise Exception(f'only supported on ENV=local')
        logging.warn(f'WARNING! going to restore redis DB from file {json_file_path} in 10s')
        time.sleep(10)
        f = open (json_file_path, "r")
        data = json.loads(f.read())
        logging.info(f'number of keys: {len(data)}')
        for key, value in data.items():
            if isinstance(value, str):
                self.r.set(key, value)
            elif isinstance(value, dict):
                self.r.hset(key, mapping=value)
            else:
                raise Exception(f'value type not supported: {type(value)}')

    def clear_db(self, wait=True):
        if wait:
            print('WARNING! going to remove all keys after 30s')
            time.sleep(15)
            print('WARNING! going to remove all keys after 15s')
            time.sleep(15)
        self.r.flushdb()
