#!/bin/bash -e

service cron start
printenv | awk '{print "export " $1}' > /.cron_env
chmod 644 /.cron_env

cd /sleepbattle

pip install -r requirements.txt

python -u sleepbattle.py
