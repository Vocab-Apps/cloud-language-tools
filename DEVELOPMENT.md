# secrets
## encrypting new secrets
gpg --batch --yes --passphrase-file ~/secrets/cloudlanguagetools/gpg_passphrase_file --output secrets.py.gpg --symmetric clt_secrets.py