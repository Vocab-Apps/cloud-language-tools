# building for dev:
# docker build -t lucwastiaux/cloud-language-tools:dev -f Dockerfile .
# docker push lucwastiaux/cloud-language-tools:dev
# 
# pushing to digitalocean registry
# docker tag lucwastiaux/cloud-language-tools:dev-3 registry.digitalocean.com/luc/cloud-language-tools:dev-3
# docker push registry.digitalocean.com/luc/cloud-language-tools:dev-3

# running locally:
# docker run --env-file /home/luc/python/cloud-language-tools-secrets/cloud-language-tools-local  -p 0.0.0.0:8042:8042/tcp lucwastiaux/cloud-language-tools:20220902-7
# inspecting space usage
# docker container exec 224e53da8507 du -hc --max-depth=1 /root

FROM lucwastiaux/cloud-language-tools-core:11.5.0

ARG GPG_PASSPHRASE

# modules not available on pypi
RUN pip3 install git+https://github.com/Patreon/patreon-python && pip3 cache purge

# this adds any required modules not covered above
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt && pip3 cache purge

# copy app files
COPY start.sh app.py version.py redisdb.py patreon_utils.py quotas.py convertkit.py airtable_utils.py getcheddar_utils.py user_utils.py scheduled_tasks.py ./
COPY secrets.py.gpg secrets/tts_keys.sh.gpg secrets/convertkit.sh.gpg secrets/airtable.sh.gpg secrets/digitalocean_spaces.sh.gpg secrets/patreon_prod_digitalocean.sh.gpg secrets/rsync_net.sh.gpg secrets/ssh_id_rsync_redis_backup.gpg ./

EXPOSE 8042
ENTRYPOINT ["./start.sh"]
