import os
import requests
import pprint
import convertkit
import logging
import clt_secrets as secrets

api_key = secrets.config['convertkit']['CONVERTKIT_API_KEY']
api_secret = secrets.config['convertkit']['CONVERTKIT_API_SECRET']

def list_subscribers():
    # curl https://api.convertkit.com/v3/subscribers?api_secret=<your_secret_api_key>&from=2016-02-01&to=2015-02-28
    url = f'https://api.convertkit.com/v3/subscribers?api_secret={api_secret}'
    response = requests.get(url)
    data = response.json()
    pprint.pprint(data)    

def list_canceled():
    # curl https://api.convertkit.com/v3/subscribers?api_secret=<your_secret_api_key>&from=2016-02-01&to=2015-02-28
    url = f'https://api.convertkit.com/v3/subscribers?api_secret={api_secret}&sort_field=cancelled_at'
    response = requests.get(url)
    data = response.json()
    pprint.pprint(data)   

def view_subscriber():
    url = f'https://api.convertkit.com/v3/subscribers/1215642036?api_secret={api_secret}'
    response = requests.get(url)
    data = response.json()
    pprint.pprint(data)    

def list_tags_subscriber():
    # curl https://api.convertkit.com/v3/subscribers/<subscriber_id>/tags?api_key=<your_public_api_key>
    url = f'https://api.convertkit.com/v3/subscribers/1215642036/tags?api_secret={api_secret}'
    response = requests.get(url)
    data = response.json()
    pprint.pprint(data)        

def list_sequences():
    # curl https://api.convertkit.com/v3/subscribers/<subscriber_id>/tags?api_key=<your_public_api_key>
    url = f'https://api.convertkit.com/v3/sequences?api_key={api_key}'
    response = requests.get(url)
    data = response.json()
    pprint.pprint(data)        

def list_forms():
    # curl https://api.convertkit.com/v3/forms?api_key=<your_public_api_key>
    url = f'https://api.convertkit.com/v3/forms?api_key={api_key}'
    response = requests.get(url)
    data = response.json()
    pprint.pprint(data)        


def add_subscriber_sequence():
    email = 'lemoselioliveira@gmail.com'
    sequence_id = 826851 # extend_trial
    url = f'https://api.convertkit.com/v3/sequences/{sequence_id}/subscribe'
    response = requests.post(url, json={
            "api_key": api_key,
            "email": email
    })
    print(response)
    print(response.content)
    data = response.json()
    pprint.pprint(data)        


def add_subscriber_tag():
    email = 'languagetools+development.language_tools.customer-20230801-2@mailc.net'
    first_name = 'Luc'
    tag_id = 4024166 # vocabai_user
    url = f'https://api.convertkit.com/v3/tags/{tag_id}/subscribe'
    response = requests.post(url, json={
            "api_key": api_key,
            "email": email,
            "first_name": first_name
    })
    response.raise_for_status()
    data = response.json()
    pprint.pprint(data)            

def tag_subscriber():
    # curl -X POST https://api.convertkit.com/v3/tags/<tag_id>/subscribe\
    #      -H "Content-Type: application/json; charset=utf-8"\
    #      -d '{ \
    #             "api_key": "<your_public_api_key>",\
    #             "email": "jonsnow@example.com"\
    #          }'    

    # 2248152 - trial_api_key_ready
    # 2248154 - trial_api_key_requested
    url = f'https://api.convertkit.com/v3/tags/{2248154}/subscribe'
    response = requests.post(url, json={
            "api_key": api_key,
            "email": "bear@mailc.net",
            'fields' : {
                'trial_api_key': "api_key_1"
            }
    })
    print(response)
    print(response.content)
    data = response.json()
    pprint.pprint(data)    

def set_subscriber_field():
    url = f'https://api.convertkit.com/v3/subscribers/1215674041'

    response = requests.post(url, json={
        'api_secret': api_secret,
        'fields': {
            'trial_api_key': "api_key_1"
        } 
        })
    print(url)
    print(response)
    data = response.json()
    pprint.pprint(data)        


def list_tags():
    url = f'https://api.convertkit.com/v3/tags?api_key={api_key}'
    response = requests.get(url)
    data = response.json()
    pprint.pprint(data)

def list_fields():
    url = f'https://api.convertkit.com/v3/custom_fields?api_key={api_key}'
    response = requests.get(url)
    data = response.json()
    pprint.pprint(data)


def configure_addtag_webhook():
    # curl -X POST https://api.convertkit.com/v3/automations/hooks
    #      -H 'Content-Type: application/json'\
    #      -d '{ "api_secret": "<your_secret_api_key>",\
    #            "target_url": "http://example.com/incoming",\
    #            "event": { "name": "subscriber.subscriber_activate" } }'    

    url = 'https://api.convertkit.com/v3/automations/hooks'
    response = requests.post(url, json={
        'api_secret': api_secret,
        # 'target_url': 'https://bfa7c6b87809.ngrok.io/convertkit_subscriber_request_trial_key',
        # 'target_url': 'https://cloud-language-tools-dev.anki.study/convertkit_subscriber_request_trial_key',
        # 'target_url': 'https://cloud-language-tools-prod.anki.study/convertkit_subscriber_request_trial_key',
        # 'target_url': 'https://cloud-language-tools-prod.anki.study/convertkit_subscriber_request_patreon_key',
        'target_url': 'https://cloud-language-tools-tts-prod.anki.study/convertkit_trial_quota_increase',
        # 'event': {  'name': 'subscriber.tag_add', 'tag_id': int(os.environ['CONVERTKIT_TRIAL_API_KEY_REQUESTED_TAG']) }
        'event': {  'name': 'subscriber.tag_add', 'tag_id': 3772416 }
    })
    print(response)
    print(response.content)
    data = response.json()
    pprint.pprint(data)

def configure_addtag_webhook_trialkey():
    url = 'https://api.convertkit.com/v3/automations/hooks'
    response = requests.post(url, json={
        'api_secret': api_secret,
        'target_url': 'https://cloud-language-tools-tts-prod.anki.study/convertkit_subscriber_request_trial_key',
        'event': {  'name': 'subscriber.tag_add', 'tag_id': 2248152 } # trial_api_key_requested
    })
    print(response)
    print(response.content)
    data = response.json()
    pprint.pprint(data)

def configure_addtag_webhook_patreonuser():
    url = 'https://api.convertkit.com/v3/automations/hooks'
    response = requests.post(url, json={
        'api_secret': api_secret,
        'target_url': 'https://cloud-language-tools-tts-prod.anki.study/convertkit_subscriber_request_patreon_key',
        'event': {  'name': 'subscriber.tag_add', 'tag_id': 2293841 } # patreon_user
    })
    print(response)
    print(response.content)
    data = response.json()
    pprint.pprint(data)    

def verify_email():
    client = convertkit.ConvertKit()
    input_email = 'gavad73385@vootin.com'
    email_valid, reason = client.check_email_valid(input_email)
    print(f'{input_email}: email_valid: {email_valid}, reason: {reason}')


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', 
                        datefmt='%Y%m%d-%H:%M:%S',
                        level=logging.DEBUG)
    # configure_addtag_webhook()
    # configure_addtag_webhook_trialkey()
    # configure_addtag_webhook_patreonuser()
    # list_tags()
    # list_fields()
    # list_subscribers()
    # list_canceled()
    # view_subscribers()
    # list_tags_subscriber()
    # tag_subscriber()
    # set_subscriber_field()
    # list_sequences()
    # add_subscriber_sequence()
    # list_forms()
    # verify_email()
    add_subscriber_tag()