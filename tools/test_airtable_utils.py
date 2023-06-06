import os
import sys
import inspect
import logging
import pytest

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

import airtable_utils

@pytest.mark.skip()
def test_get_trial_tag_requests():
    airtable = airtable_utils.AirtableUtils()
    tag_request_df = airtable.get_trial_tag_requests()
    print(tag_request_df)
    print(tag_request_df[['record_id', 'email','tag_request']])

@pytest.mark.skip()
def test_get_trial_users():
    airtable = airtable_utils.AirtableUtils()
    trial_users_df = airtable.get_trial_users()
    print(trial_users_df)    


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', 
                        datefmt='%Y%m%d-%H:%M:%S',
                        level=logging.DEBUG)
    test_get_trial_tag_requests()
    # test_get_trial_users()