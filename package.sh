#!/bin/sh
set -eoux pipefail

# exit if argument is not passed in
if [ -z "$1" ]; then
  echo "Please pass major, minor or patch"
  exit 1
fi

BUMP_TYPE=$1 # major, minor or patch
# check that the bump type is valid
if [ "$BUMP_TYPE" != "major" ] && [ "$BUMP_TYPE" != "minor" ] && [ "$BUMP_TYPE" != "patch" ]; then
  echo "Please pass major, minor or patch"
  exit 1
fi

NEW_VERSION=`bump2version --list ${BUMP_TYPE} | grep new_version | sed -r s,"^.*=",,`
# push to upstream
git push
git push --tags

VERSION_NUMBER=$NEW_VERSION

# docker build
export DOCKER_BUILDKIT=1
docker build -t lucwastiaux/cloud-language-tools:${VERSION_NUMBER} -f Dockerfile .
docker push lucwastiaux/cloud-language-tools:${VERSION_NUMBER}