#!/bin/bash
set -euxo pipefail

echo "not supported anymore, moved to vocabai"
exit 1

DOCKER_IMAGE=vocabai/cloud-language-tools-postdeploy:latest

export DOCKER_BUILDKIT=1
docker build -t ${DOCKER_IMAGE} -f Dockerfile.postdeploy_test .
docker push ${DOCKER_IMAGE}