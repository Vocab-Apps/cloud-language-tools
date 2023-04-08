import os
import sys
import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

import airtable_utils


def test_get_trial_tag_requests():
    airtable = airtable_utils.AirtableUtils()
    tag_request_df = airtable.get_trial_tag_requests()
    print(tag_request_df)



if __name__ == '__main__':
    test_get_trial_tag_requests()