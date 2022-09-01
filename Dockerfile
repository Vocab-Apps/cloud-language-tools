# building for dev:
# docker build -t lucwastiaux/cloud-language-tools:dev -f Dockerfile .
# docker push lucwastiaux/cloud-language-tools:dev
# 
# pushing to digitalocean registry
# docker tag lucwastiaux/cloud-language-tools:dev-3 registry.digitalocean.com/luc/cloud-language-tools:dev-3
# docker push registry.digitalocean.com/luc/cloud-language-tools:dev-3

# running:
# docker run --env-file ./cloud-language-tools-env  -p 0.0.0.0:8042:8042/tcp lucwastiaux/cloud-language-tools:dev-3

FROM ubuntu:20.04

ARG GPG_PASSPHRASE

# use ubuntu mirrors
RUN sed -i -e 's|archive\.ubuntu\.com|mirrors\.xtom\.com\.hk|g' /etc/apt/sources.list
# install packages first
RUN apt-get update -y && apt-get install -y libasound2 python3-pip git gnupg build-essential wget
# required by Epitran module
RUN wget http://tts.speech.cs.cmu.edu/awb/flite-2.0.5-current.tar.bz2 && tar xvjf flite-2.0.5-current.tar.bz2 && cd flite-2.0.5-current && ./configure && make && make install && cd testsuite && make lex_lookup && cp lex_lookup /usr/local/bin

# modules not available on pypi
RUN pip3 install git+https://github.com/Patreon/patreon-python

# install cloudlanguagetools-core requirements, which shoud not change often
RUN pip3 install clt_spacy==0.1
RUN pip3 install clt_argostranslate==0.4
RUN pip3 install clt_wenlin==0.7
RUN pip3 install clt_requirements==0.1
# install cloudlanguagetools-core, change version as required
RUN pip3 install cloudlanguagetools==2.3

# this adds any required modules not covered above
COPY requirements.txt ./
RUN pip3 install -r requirements.txt

# copy app files
COPY start.sh app.py version.py redisdb.py patreon_utils.py quotas.py convertkit.py airtable_utils.py getcheddar_utils.py user_utils.py scheduled_tasks.py ./
COPY secrets.py.gpg secrets/tts_keys.sh.gpg secrets/convertkit.sh.gpg secrets/airtable.sh.gpg secrets/digitalocean_spaces.sh.gpg secrets/patreon_prod_digitalocean.sh.gpg secrets/rsync_net.sh.gpg secrets/ssh_id_rsync_redis_backup.gpg ./

EXPOSE 8042
ENTRYPOINT ["./start.sh"]
