#!/usr/bin/env bash

set -e

echo "### Installing dependencies"
pip3 install -r requirements.txt

echo "### Migrating and initializing database"
python3 manage.py migrate --noinput
python3 manage.py initialize_plans

echo "### Collecting static files"
python3 manage.py collectstatic --noinput --clear

echo "Build completed successfully"
