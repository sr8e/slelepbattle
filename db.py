import psycopg2

from settings import DATABASE_URL, DATETIME_FORMAT


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def insert_sleeptime(uid, sleeptime):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"insert into sleeptime (uid, sleeptime) values ({uid}, '{sleeptime.strftime(DATETIME_FORMAT)}');")
            conn.commit()

