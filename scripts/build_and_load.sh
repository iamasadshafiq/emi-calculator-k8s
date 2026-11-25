#!/bin/bash
# Builds the web image and copies it into the Minikube node.
# usage: ./scripts/build_and_load.sh [version]        (default 1.0)
VERSION=${1:-1.0}
set -e
docker build --build-arg APP_VERSION="$VERSION" -t "emi-web:$VERSION" app/
minikube image load "emi-web:$VERSION"
minikube image ls | grep emi-web
