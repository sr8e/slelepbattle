# Sleepbattle

Sleepbattle is a discord bot which logs and scores sleep of server members to maintain their health.


## Environments
- python 3.9.5
  - discord.py 1.7.3
  - psycopg2-binary 2.9.1
  - python-dotenv 0.19.0
  - flake8 3.9.2
- postgreSQL 13.4

## Setting up .env
This project uses `.env` to provide environment variables.
```
DISCORDBOT_TOKEN=xxxxxxEXAMPLETOKENxxxxxx.xxxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxx
CHANNEL_ID=000000000000000000
DATABASE_URL=postgres://username:dbpass@localhost:5432/dbname
```