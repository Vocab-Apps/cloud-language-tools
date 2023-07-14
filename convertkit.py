import os
import requests
import logging
import pprint
import time
import clt_secrets as secrets
import cloudlanguagetools.constants

logger = logging.getLogger(__name__)

CONVERTKIT_THROTTLE_REQUESTS_SLEEP = 0.5

class ConvertKit():
    # ignore these tags when building user tag maps to update airtable
    TRIAL_SPECIFIC_TAG_LIST = [
        'trial_user',
        'trial_extended',
        'trial_user_inactive',
        'trial_end_reach_out',
        'trial_patreon_convert',
        'trial_api_key_ready',
        'trial_api_key_requested',
        'trial_vip',
        'trial_offer_hypertts',
        'trial_quota_50k',
        'trial_quota_increased',
        'trial_quota_increase_request',
        'manual_trial_offer_hypertts_followup',
    ]
    PATREON_SPECIFIC_TAG_LIST = [
        'patreon_user',
        'patreon_active',
        'patreon_canceled',        
        'patreon_api_key_ready',
    ]
    GETCHEDDAR_SPECIFIC_TAG_LIST = [
        'getcheddar_user',
        'getcheddar_active',
        'getcheddar_canceled',
        'getcheddar_near_max'
    ]
    TAG_IGNORE_LIST_GETCHEDDAR = TRIAL_SPECIFIC_TAG_LIST + PATREON_SPECIFIC_TAG_LIST
    TAG_IGNORE_LIST_TRIAL = ['trial_api_key_requested', 'trial_api_key_ready', 'trial_user'] # we still want to see which trial users migrated to getcheddar/patreon
    TAG_IGNORE_LIST_PATREON = TRIAL_SPECIFIC_TAG_LIST + GETCHEDDAR_SPECIFIC_TAG_LIST

    TAG_IGNORE_LIST_GLOBAL = []

    def __init__(self):
        self.enable = secrets.config['convertkit']['enable']
        if self.enable:
            self.api_key = secrets.config['convertkit']['CONVERTKIT_API_KEY']
            self.api_secret = secrets.config['convertkit']['CONVERTKIT_API_SECRET']

            self.tag_id_api_requested = int(secrets.config['convertkit']['CONVERTKIT_TRIAL_API_KEY_REQUESTED_TAG'])
            self.tag_id_api_ready = int(secrets.config['convertkit']['CONVERTKIT_TRIAL_API_KEY_READY_TAG'])
            self.tag_id_patreon_api_ready = int(secrets.config['convertkit']['CONVERTKIT_PATREON_API_KEY_READY_TAG'])
            self.tag_id_trial_extended = int(secrets.config['convertkit']['CONVERTKIT_TRIAL_EXTENDED_TAG'])
            self.tag_id_trial_inactive = int(secrets.config['convertkit']['CONVERTKIT_TRIAL_INACTIVE_TAG'])
            self.tag_id_trial_user = int(secrets.config['convertkit']['CONVERTKIT_TRIAL_USER_TAG'])
            self.tag_id_trial_end_reach_out = int(secrets.config['convertkit']['CONVERTKIT_TRIAL_END_REACH_OUT_TAG'])
            self.tag_id_trial_patreon_convert = int(secrets.config['convertkit']['CONVERTKIT_TRIAL_PATREON_CONVERT_TAG'])
            self.tag_id_patreon = int(secrets.config['convertkit']['CONVERTKIT_PATREON_USER_TAG'])

            self.getcheddar_user_form_id = secrets.config['convertkit']['getcheddar_user_form_id']
            self.tag_id_getcheddar_user = secrets.config['convertkit']['tag_ig_getchedar_user']
            self.tag_id_disposable_email = secrets.config['convertkit']['tag_id_disposable_email']
            self.tag_id_trial_vip = secrets.config['convertkit']['tag_id_trial_vip']
            self.tag_id_trial_quota_increased = secrets.config['convertkit']['tag_id_trial_quota_increased']
            self.tag_id_trial_user_instant = secrets.config['convertkit']['tag_id_trial_user_instant']

        self.enable_debounce = secrets.config['debounce']['enable']
        if self.enable_debounce:
            self.debounce_email = secrets.config['debounce']['email']
            self.debounce_api_key = secrets.config['debounce']['api_key']

        self.enable_verify_email = secrets.config['verify_email']['enable']
        if self.enable_verify_email:
            self.verify_email_api_key = secrets.config['verify_email']['api_key']

        self.full_tag_id_map = {} 

    # deprecated
    def email_valid(self, email):
        if not self.enable_debounce:
            return True
        try:
            url = "https://api.debounce.io/v1/"
            querystring = {'api': self.debounce_api_key, 'email': email}
            response = requests.get(url, params=querystring, timeout=cloudlanguagetools.constants.RequestTimeout)
            if response.status_code == 200:
                data = response.json()
                # logger.info(f'debounce.io result: {pprint.pformat(data)}')
                # print(data)
                if data['debounce']['result'] == 'Invalid' and data['debounce']['reason'] == 'Disposable':
                    logger.info(f'found disposable email: {email}')
                    return False
            else:
                logger.error(f'received error: {response.status_code}: {response.text}')
        except:
            logger.exception(f'could not perform debounce query to validate {email}')
        return True # true by default

    # verify that an email is good and return reason if not
    def check_email_valid(self, email):
        if not self.enable_debounce:
            return True, None
        try:
            # use debounce.io first
            # =====================

            url = "https://api.debounce.io/v1/"
            querystring = {'api': self.debounce_api_key, 'email': email}
            response = requests.get(url, params=querystring, timeout=cloudlanguagetools.constants.RequestTimeout)
            if response.status_code == 200:
                data = response.json()
                logger.debug(f'debounce.io result: {pprint.pformat(data)}')
                # print(data)
                result = data['debounce']['result']
                reason = data['debounce']['reason']
                if result != 'Safe to Send':
                    return False, f'email not valid: {result}, {reason}'
            else:
                logger.error(f'debounce.io: received error: {response.status_code}: {response.text}')

            # use verifyemail.io second
            # =========================

            if self.enable_verify_email:
                url = f'https://verifymail.io/api/{email}?key={self.verify_email_api_key}'
                response = requests.get(url, timeout=cloudlanguagetools.constants.RequestTimeout)
                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f'verifyemail response: {pprint.pformat(data)}')
                    if data['disposable'] == True:
                        return False, f'email not valid: disposable address'
            else:
                logger.error(f'verifyemail.io: received error: {response.status_code}: {response.text}')                    
                    
        except:
            logger.exception(f'could not perform debounce query to validate {email}')
        return True, None # true by default


    def register_getcheddar_user(self, email, api_key, update_url, cancel_url):
        if self.enable:
            logger.info(f'registering new getcheddar user on convertkit')
            url = f'https://api.convertkit.com/v3/forms/{self.getcheddar_user_form_id}/subscribe'
            response = requests.post(url, json={
                    "api_key": self.api_key,
                    "email": email,
                    'fields' : {
                        'getcheddar_api_key': api_key,
                        'getcheddar_update_url': update_url,
                        'getcheddar_cancel_url': cancel_url
                    }
            }, timeout=cloudlanguagetools.constants.RequestTimeout)
            if response.status_code != 200:
                logger.error(f'could not subscribe user to form: {response.content}')


    def tag_user_instant_trial(self, email, api_key, trial_quota):
        if self.enable:
            url = f'https://api.convertkit.com/v3/tags/{self.tag_id_trial_user_instant}/subscribe'
            response = requests.post(url, json={
                    "api_key": self.api_key,
                    "email": email,
                    'fields' : {
                        'trial_api_key': api_key,
                        'trial_quota': trial_quota
                    }
            }, timeout=cloudlanguagetools.constants.RequestTimeout)
            if response.status_code != 200:
                logger.error(f'could not tag user: {response.content}')

    def tag_user_api_ready(self, email, api_key, trial_quota):
        url = f'https://api.convertkit.com/v3/tags/{self.tag_id_api_ready}/subscribe'
        response = requests.post(url, json={
                "api_key": self.api_key,
                "email": email,
                'fields' : {
                    'trial_api_key': api_key,
                    'trial_quota': trial_quota
                }
        }, timeout=cloudlanguagetools.constants.RequestTimeout)
        if response.status_code != 200:
            logger.error(f'could not tag user: {response.content}')

    def tag_user_patreon_api_ready(self, email, api_key):
        url = f'https://api.convertkit.com/v3/tags/{self.tag_id_patreon_api_ready}/subscribe'
        response = requests.post(url, json={
                "api_key": self.api_key,
                "email": email,
                'fields' : {
                    'patreon_api_key': api_key
                }
        }, timeout=cloudlanguagetools.constants.RequestTimeout)
        if response.status_code != 200:
            logger.error(f'could not tag user: {response.content}')

    def tag_user_disposable_email(self, email):
        self.tag_user(email, self.tag_id_disposable_email)

    def tag_user(self, email, tag_id):
        logger.info(f'tagging {email} with {tag_id}')
        url = f'https://api.convertkit.com/v3/tags/{tag_id}/subscribe'
        response = requests.post(url, json={
                "api_key": self.api_key,
                "email": email
        }, timeout=cloudlanguagetools.constants.RequestTimeout)
        # throttle
        time.sleep(CONVERTKIT_THROTTLE_REQUESTS_SLEEP)
        if response.status_code != 200:
            logger.error(f'could not tag user email: [{email}]: response: {response.content}')
        else:
            logger.info(f'tagged user with tag_id {tag_id}: {email}')

    def untag_user(self, subscriber_id, tag_id):
        logger.info(f'untagging {subscriber_id} with {tag_id}')
        url = f'https://api.convertkit.com/v3/subscribers/{subscriber_id}/tags/{tag_id}'
        response = requests.delete(url, json={
                "api_secret": self.api_secret
        }, timeout=cloudlanguagetools.constants.RequestTimeout)
        # throttle
        time.sleep(CONVERTKIT_THROTTLE_REQUESTS_SLEEP)
        if response.status_code != 200:
            error_message = f'could not untag user subscriber_id {subscriber_id}, tag_id: {tag_id} status_code: {response.status_code} url: {url}'
            logger.error(error_message)
        else:
            logger.info(f'untagged user with tag_id {tag_id}: {subscriber_id}')

    def user_set_fields(self, email, subscriber_id, field_map):
        url = f'https://api.convertkit.com/v3/subscribers/{subscriber_id}'
        response = requests.put(url, json={
                "api_secret": self.api_secret,
                "fields": field_map
        }, timeout=cloudlanguagetools.constants.RequestTimeout)
        # throttle
        time.sleep(CONVERTKIT_THROTTLE_REQUESTS_SLEEP)        
        if response.status_code != 200:
            logger.error(f'could not update user {email}, subscriber_id: {subscriber_id} response: {response.content}, possible reason: user unsubscribed or deleted')
        else:
            logger.info(f'updated user {email}, {subscriber_id} fields: {field_map}')

    def tag_user_set_fields(self, email, tag_id, field_map):
        url = f'https://api.convertkit.com/v3/tags/{tag_id}/subscribe'
        response = requests.post(url, json={
                "api_key": self.api_key,
                "email": email,
                "fields": field_map
        }, timeout=cloudlanguagetools.constants.RequestTimeout)
        # throttle
        time.sleep(CONVERTKIT_THROTTLE_REQUESTS_SLEEP)        
        if response.status_code != 200:
            logger.error(f'could not tag user: {response.content}')            
        else:
            logger.info(f'tagged user with tag_id {tag_id}: {email}')

    def tag_user_trial_extended(self, email, trial_quota):
        self.tag_user_set_fields(email, self.tag_id_trial_extended, {'trial_quota': trial_quota})

    def tag_user_trial_vip(self, email, trial_quota):
        self.tag_user_set_fields(email, self.tag_id_trial_vip, {'trial_quota': trial_quota})

    def tag_user_trial_quota_increased(self, email, trial_quota):
        self.tag_user_set_fields(email, self.tag_id_trial_quota_increased, {'trial_quota': trial_quota})

    def tag_user_trial_inactive(self, email):
        self.tag_user(email, self.tag_id_trial_inactive)

    def list_subscribers_tag(self, tag_id):
        subscriber_list = []

        url = f'https://api.convertkit.com/v3/tags/{tag_id}/subscriptions?api_secret={self.api_secret}&page=1'
        response = requests.get(url, timeout=cloudlanguagetools.constants.RequestTimeout)
        if response.status_code != 200:
            raise Exception(f'could not request subscribers for tag_id {tag_id}: status_code {response.status_code}: {response.content}')
        # throttle
        time.sleep(CONVERTKIT_THROTTLE_REQUESTS_SLEEP)        
        data = response.json()
        current_page = data['page']
        total_pages = data['total_pages']


        for data in data['subscriptions']:
            subscriber = data['subscriber']
            subscriber_list.append(subscriber)

        while current_page < total_pages:
            next_page = current_page + 1
            url = f'https://api.convertkit.com/v3/tags/{tag_id}/subscriptions?api_secret={self.api_secret}&page={next_page}'
            response = requests.get(url, timeout=cloudlanguagetools.constants.RequestTimeout)
            if response.status_code != 200:
                raise Exception(f'could not request subscribers for tag_id {tag_id}: status_code {response.status_code}: {response.content}')
            # throttle
            time.sleep(CONVERTKIT_THROTTLE_REQUESTS_SLEEP)
            data = response.json()
            current_page = data['page']

            for data in data['subscriptions']:
                subscriber = data['subscriber']
                subscriber_list.append(subscriber)

        return subscriber_list

    def list_canceled(self):
        canceled_list = []

        url = f'https://api.convertkit.com/v3/subscribers?api_secret={self.api_secret}&sort_field=cancelled_at'
        response = requests.get(url, timeout=cloudlanguagetools.constants.RequestTimeout)
        data = response.json()

        current_page = data['page']
        total_pages = data['total_pages']

        canceled_list.extend(data['subscribers'])

        while current_page < total_pages:
            next_page = current_page + 1
            url = f'https://api.convertkit.com/v3/subscribers?api_secret={self.api_secret}&sort_field=cancelled_at&page={next_page}'
            response = requests.get(url, timeout=cloudlanguagetools.constants.RequestTimeout)
            # throttle
            time.sleep(CONVERTKIT_THROTTLE_REQUESTS_SLEEP)
            data = response.json()
            current_page = data['page']
            canceled_list.extend(data['subscribers'])

        return canceled_list

    def list_trial_users(self):
        return self.list_subscribers_tag(self.tag_id_trial_user)

    def list_patreon_users(self):
        return self.list_subscribers_tag(self.tag_id_patreon)

    def list_getcheddar_users(self):
        return self.list_subscribers_tag(self.tag_id_getcheddar_user)

    def list_tags(self, subscriber_id):
        url = f'https://api.convertkit.com/v3/subscribers/{subscriber_id}/tags?api_secret={self.api_secret}'
        response = requests.get(url, timeout=cloudlanguagetools.constants.RequestTimeout)
        if response.status_code != 200:
            raise Exception(f'could not list tags, status_code: {response.status_code}: {response.content}')
        # throttle
        time.sleep(CONVERTKIT_THROTTLE_REQUESTS_SLEEP)
        data = response.json()
        return data['tags']

    def populate_tag_map(self):
        logger.info('populating tag map')
        url = f'https://api.convertkit.com/v3/tags?api_key={self.api_key}'
        response = requests.get(url, timeout=cloudlanguagetools.constants.RequestTimeout)
        # throttle
        time.sleep(CONVERTKIT_THROTTLE_REQUESTS_SLEEP)
        assert response.status_code == 200
        data = response.json()
        tags = data['tags']
        for tag_entry in tags:
            tag_name = tag_entry['name']
            tag_id = tag_entry['id']
            self.full_tag_id_map[tag_name] = tag_id