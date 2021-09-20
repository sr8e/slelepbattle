import psycopg2

from settings import DATABASE_URL, DATE_FORMAT, DATETIME_FORMAT


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
            cur.execute(
                "insert into sleeptime (uid, sleeptime, post_id) values "
                f"({uid}, '{sleeptime.strftime(DATETIME_FORMAT)}', {post_id}) returning id;"
            )
            inserted_id = cur.fetchone()[0]
            self.conn.commit()
            return inserted_id

    def insert_waketime(self, uid, waketime, post_id):
        with self.conn.cursor() as cur:
            cur.execute(
                "insert into waketime (uid, waketime, post_id) values "
                f"({uid}, '{waketime.strftime(DATETIME_FORMAT)}', {post_id}) returning id;"
            )
            inserted_id = cur.fetchone()[0]
            self.conn.commit()
            return inserted_id

    def insert_score(self, uid, sleep_pk, wake_pk, score, date):
        with self.conn.cursor() as cur:
            cur.execute(
                "insert into score (uid, sleep_pk, wake_pk, score, date) values "
                f"({uid}, {sleep_pk}, {wake_pk}, {score}, '{date.strftime(DATE_FORMAT)}');"
            )
            self.conn.commit()

    def update_score(self, pk, sleep_pk, wake_pk, score):
        with self.conn.cursor() as cur:
            cur.execute(
                f"update score set (sleep_pk, wake_pk, score)=({sleep_pk}, {wake_pk}, {score}) "
                f"where id={pk};"
            )
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

    def get_score(self, uid, date):
        with self.conn.cursor() as cur:
            cur.execute(
                "select id, sleep_pk, wake_pk, score from score where "
                f"uid={uid} and date='{date.strftime(DATE_FORMAT)}';"
            )
            return cur.fetchone()

    def get_compare_score(self, my_uid, other_uid, date):
        with self.conn.cursor() as cur:
            cur.execute(
                f"select id, uid, score, date from score where uid in ({my_uid}, {other_uid}) "
                f"and date>='{date.strftime(DATE_FORMAT)}'"
            )
            return cur.fetchall()

    def get_attack_state(self, uid):
        with self.conn.cursor() as cur:
            cur.execute(f"select state from attack where uid={uid};")
            if (res := cur.fetchone()) is not None:
                return res[0]

            # create a record
            cur.execute(f"insert into attack (uid, state) values ({uid}, 0);")
            self.conn.commit()
            return 0

    def get_active_users(self, date_since):
        with self.conn.cursor() as cur:
            cur.execute(f"select distinct uid from score where date>='{date_since.strftime(DATE_FORMAT)}';")
            return [t[0] for t in cur.fetchall()]

    def set_attack_state(self, uid, state):
        with self.conn.cursor() as cur:
            cur.execute(f"update attack set state={state} where uid={uid};")
            self.conn.commit()
