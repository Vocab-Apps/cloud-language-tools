#!/bin/sh
CWD=`pwd`
gpg --batch --yes --passphrase ${GPG_PASSPHRASE} --output ${CWD}/clt_secrets.py  --decrypt secrets.py.gpg
gpg --batch --yes --passphrase ${GPG_PASSPHRASE} --output ${CWD}/tts_keys.sh  --decrypt tts_keys.sh.gpg
gpg --batch --yes --passphrase ${GPG_PASSPHRASE} --output ${CWD}/convertkit.sh  --decrypt convertkit.sh.gpg
gpg --batch --yes --passphrase ${GPG_PASSPHRASE} --output ${CWD}/airtable.sh  --decrypt airtable.sh.gpg
gpg --batch --yes --passphrase ${GPG_PASSPHRASE} --output ${CWD}/digitalocean_spaces.sh  --decrypt digitalocean_spaces.sh.gpg
gpg --batch --yes --passphrase ${GPG_PASSPHRASE} --output ${CWD}/patreon_prod_digitalocean.sh  --decrypt patreon_prod_digitalocean.sh.gpg
gpg --batch --yes --passphrase ${GPG_PASSPHRASE} --output ${CWD}/rsync_net.sh  --decrypt rsync_net.sh.gpg
gpg --batch --yes --passphrase ${GPG_PASSPHRASE} --output ${CWD}/ssh_id_rsync_redis_backup  --decrypt ssh_id_rsync_redis_backup.gpg
if [ -n "$RUN_SCHEDULED_TASKS" ]
then
. ${CWD}/tts_keys.sh
. ${CWD}/convertkit.sh
. ${CWD}/airtable.sh
. ${CWD}/digitalocean_spaces.sh
. ${CWD}/patreon_prod_digitalocean.sh
. ${CWD}/rsync_net.sh
echo "starting scheduled tasks"
python3 scheduled_tasks.py
else
. ${CWD}/tts_keys.sh
. ${CWD}/convertkit.sh
WORKERS="${GUNICORN_WORKERS:-1}" 
GUNICORN_THREADS="${GUNICORN_THREADS:-8}"
MAX_REQUESTS="${GUNICORN_MAX_REQUESTS:50000}" # should amount to a weekly restart
MAX_REQUESTS_JITTER="${GUNICORN_MAX_REQUESTS_JITTER:5000}"
echo "starting gunicorn with ${WORKERS} workers, ${GUNICORN_THREADS} threads, and ${MAX_REQUESTS} max requests, max requests jitter ${MAX_REQUESTS_JITTER}" 
exec gunicorn --workers $WORKERS --threads ${GUNICORN_THREADS} -b :8042 --timeout 120 --max-requests ${MAX_REQUESTS} --max-requests-jitter ${MAX_REQUESTS_JITTER} --access-logfile - --error-logfile - app:app
fi