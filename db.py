import psycopg2

from settings import DATABASE_URL, DATETIME_FORMAT


class DBManager:

    def __init__(self):
        self.conn = self.get_connection()

    def __enter__(self):
        return self

    def __exit__(self, *exc_args):
        self.conn.close()

    @staticmethod
    def get_connection():
        return psycopg2.connect(DATABASE_URL)

    def insert_sleeptime(self, uid, sleeptime, post_id):
        with self.conn.cursor() as cur:
            cur.execute(f"insert into sleeptime (uid, sleeptime, post_id) values ({uid}, '{sleeptime.strftime(DATETIME_FORMAT)}', {post_id});")
            self.conn.commit()

    def is_last_sleep_completed(self, uid):
        with self.conn.cursor() as cur:
            res_sleeptime = self.get_last_sleep(uid)
            if res_sleeptime is None:
                return True
            cur.execute(f"select sleep_pk from score where uid={uid} order by id desc;")
            res_score = cur.fetchone()
            if res_score is None:
                return False
            return res_sleeptime[0] == res_score[0]

    def get_last_sleep(self, uid):
        with self.conn.cursor() as cur:
            cur.execute(f"select id, sleeptime, post_id from sleeptime where uid={uid} order by id desc;")
            return cur.fetchone()

    def get_last_wake(self, uid):
        with self.conn.cursor() as cur:
            cur.execute(f"select id, waketime, post_id from waketime where uid={uid} order by id desc;")
            return cur.fetchone()

