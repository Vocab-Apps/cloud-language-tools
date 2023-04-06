import os
import sys
import inspect
import boto3

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

import clt_secrets as secrets

def test_backup():
    session = boto3.session.Session()
    client = session.client('s3',
                            endpoint_url=secrets.config['wasabi']['endpoint_url'],
                            aws_access_key_id=secrets.config['wasabi']['access_key'],
                            aws_secret_access_key=secrets.config['wasabi']['secret_key'])
    bucket_name = secrets.config['wasabi']['bucket_name']
    data = "test backup"
    file_name = f'test_backup.txt'
    client.put_object(Body=data, Bucket=bucket_name, Key=file_name)

if __name__ == '__main__':
    test_backup()