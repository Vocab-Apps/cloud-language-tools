import os
import sys
import requests
import pprint
import inspect
import logging

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

import convertkit
import clt_secrets as secrets


def add_webhooks():
    convertkit_client = convertkit.ConvertKit()
    convertkit_client.populate_tag_map()

    url_base = 'https://cloudlanguagetools-api.vocab.ai'
    convertkit_client.configure_addtag_webhook('trial_quota_increase_request', url_base + '/convertkit_trial_quota_increase')


if __name__ == '__main__':
    # setup basic logging, info level
    logging.basicConfig(level=logging.INFO)
    add_webhooks()