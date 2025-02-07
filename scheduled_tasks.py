import logging
import schedule
import time
import datetime
import boto3
import json
import os
import requests
import redisdb
import user_utils
import clt_secrets as secrets
import sentry_sdk
import sentry_sdk.crons
import cloudlanguagetools.servicemanager

logger = logging.getLogger(__name__)

def signal_healthcheck_start(url):
    if secrets.config['report_healthchecks']:
        try:
            requests.get(url + '/start', timeout=10)
        except requests.RequestException as e:
            logger.exception(f'could not ping url {url}')

def signal_healthcheck_end(url):
    if secrets.config['report_healthchecks']:
        try:
            requests.get(url, timeout=10)
        except requests.RequestException as e:
            logger.exception(f'could not ping url {url}')

@sentry_sdk.crons.monitor(monitor_slug='backup_redis_db')
def backup_redis_db():
    try:
        logging.info('START TASK backing up redis db')
        healthcheck_url = 'https://healthchecks-v4.ipv6n.net/ping/6792d0b5-bd20-4a5f-b601-72a899770275'
        signal_healthcheck_start(healthcheck_url)
        start_time = time.time()
        connection = redisdb.RedisDb()

        # Digital ocean spaces
        # ====================
        session = boto3.session.Session()
        client = session.client('s3',
                                region_name=os.environ['SPACE_REGION'],
                                endpoint_url=os.environ['SPACE_ENDPOINT_URL'],
                                aws_access_key_id=os.environ['SPACE_KEY'],
                                aws_secret_access_key=os.environ['SPACE_SECRET'])    
        bucket_name = 'cloud-language-tools-redis-backups'

        full_db_dump = connection.full_db_dump()
        time_str = datetime.datetime.now().strftime('%H')
        file_name = f'redis_backup_{time_str}.json'
        data_str = str(json.dumps(full_db_dump))
        client.put_object(Body=data_str, Bucket=bucket_name, Key=file_name)
        logging.info(f'wrote {file_name} to {bucket_name}')

        # Wasabi
        # ======
        logging.info('starting backup to wasabi')
        session = boto3.session.Session()
        client = session.client('s3',
                                endpoint_url=secrets.config['wasabi']['endpoint_url'],
                                aws_access_key_id=secrets.config['wasabi']['access_key'],
                                aws_secret_access_key=secrets.config['wasabi']['secret_key'])
        bucket_name = secrets.config['wasabi']['bucket_name']
        file_name = f'redis_backup.json'
        client.put_object(Body=data_str, Bucket=bucket_name, Key=file_name)
        logging.info('finished backup to wasabi')

        end_time = time.time()
        logging.info(f'END TASK backing up redis db, time elapsed: {end_time - start_time}')
        signal_healthcheck_end(healthcheck_url)
    except:
        logging.exception(f'could not backup redis db')


@sentry_sdk.crons.monitor(monitor_slug='update_airtable')
def update_airtable():
    try:
        logging.info('updating airtable disabled')
        # logging.info('START TASK updating airtable')
        # healthcheck_url = 'https://healthchecks-v4.ipv6n.net/ping/ac84f934-269c-4a97-977f-e34ae04ea04a'
        # signal_healthcheck_start(healthcheck_url)
        # start_time = time.time()
        # utils = user_utils.UserUtils()
        # utils.update_airtable_all()
        # end_time = time.time()
        # logging.info(f'FINISHED TASK updating airtable, time elapsed: {end_time - start_time}')
        # signal_healthcheck_end(healthcheck_url)
    except:
        logging.exception(f'could not update airtable')    

@sentry_sdk.crons.monitor(monitor_slug='report_getcheddar_usage')
def report_getcheddar_usage():
    try:
        logging.info('START TASK reporting getcheddar usage')
        healthcheck_url = 'https://healthchecks-v4.ipv6n.net/ping/befaf855-9d31-4dae-a55c-3f380472d5cd'
        signal_healthcheck_start(healthcheck_url)
        utils = user_utils.UserUtils()
        utils.report_getcheddar_usage_all_users()
        logging.info('FINISHED TASK reporting getcheddar usage')
        signal_healthcheck_end(healthcheck_url)
    except:
        logging.exception(f'could not report getcheddar usage')

@sentry_sdk.crons.monitor(monitor_slug='update_language_data')
def update_language_data():
    try:    
        logging.info('START TASK updating language data')
        healthcheck_url = 'https://healthchecks-v4.ipv6n.net/ping/fe9e35a4-9de2-42cd-9042-a4287231879c'
        signal_healthcheck_start(healthcheck_url)
        manager = cloudlanguagetools.servicemanager.ServiceManager()
        manager.configure_default()
        language_data = manager.get_language_data_json()
        redis_connection = redisdb.RedisDb()
        redis_connection.store_language_data(language_data)
        logging.info('FINISHED TASK updating language data')
        signal_healthcheck_end(healthcheck_url)
    except:
        logging.exception(f'could not update language_data')

def setup_tasks():
    logging.info('running tasks once')
    if secrets.config['scheduled_tasks']['backup_redis']:
        logging.info('setting up redis_backup')
        backup_redis_db()
        schedule.every(2).hours.do(backup_redis_db)
    if secrets.config['scheduled_tasks']['user_data']:
        logging.info('setting up user_data tasks')
        report_getcheddar_usage()
        # update_airtable()
        # schedule.every(30).minutes.do(update_airtable)
        schedule.every(6).hours.do(report_getcheddar_usage)
    if secrets.config['scheduled_tasks']['language_data']:
        logging.info('setting up language_data')
        update_language_data()
        schedule.every(3).hours.do(update_language_data)


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(5)

if __name__ == '__main__':
    # remove all logging handlers
    logger = logging.getLogger()
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])    
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', 
                        datefmt='%Y%m%d-%H:%M:%S',
                        level=logging.INFO,
                        handlers=[logging.StreamHandler()])

    if secrets.config['sentry']['enable']:
        dsn = secrets.config['sentry']['dsn']
        sentry_sdk.init(
            dsn=dsn,
            environment=secrets.config['sentry']['environment'],
            traces_sample_rate=1.0
        )

    setup_tasks()
    run_scheduler()
