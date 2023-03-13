# Sleepbattle

Sleepbattle is a discord bot which logs and scores sleep of server members to maintain their health.


## Environments
- python 3.9.5
  - discord.py 2.2.2
  - psycopg2-binary 2.9.5
  - python-dotenv 1.0.0
- postgreSQL 13.4

### Linting
- flake8 6.0.0
- black 23.1.0
- isort 5.12.0

## Setting up environment
`$ pip install -r requirements.txt`

## Setting up .env
This project uses `.env` to provide environment variables for development.

### Example
```
DISCORDBOT_TOKEN=xxxxxxEXAMPLETOKENxxxxxx.xxxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxx
CHANNEL_ID=000000000000000000
NOTIFY_CHANNEL_ID=111111111111111111
DATABASE_URL=postgres://username:dbpass@localhost:5432/dbname
BEGINNING_DATE=1970-01-01
```
|Variable|Explanation|
|:--|:--|
|`DISCORDBOT_TOKEN`|Token of your Discord bot|
|`CHANNEL_ID`|ID of the channel where people post their sleep/wake time|
|`NOTIFY_CHANNEL_ID`|ID of the channel where attack results and ranking tables are shown|
|`DATABASE_URL`|Credentials of your database|
|`BEGINNING_DATE`|The date when logging started. Should be Sunday|

## Database setup
`$ createdb -U username dbname`

`$ psql -U username -d dbname < createtable.sql`

## For docker
Just type:

`$ docker compose up --build -d`

Database creation differs a little bit:

`$ createdb -h localhost -U username -p 5433 dbname`
 
