from datetime import date, datetime
from typing import List, NamedTuple

import psycopg2

from settings import DATABASE_URL, DATE_FORMAT, DATETIME_FORMAT

SLEEPTIME_COLUMNS = "id, uid, post_id, sleeptime"
WAKETIME_COLUMNS = "id, uid, post_id, waketime"
SCORE_COLUMNS = "id, uid, sleep_pk, wake_pk, score, date, owner"
ATTACK_COLUMNS = "uid, state, target, attack_date, swap_date, confirmed_at"


class SleepTime(NamedTuple):
    pk: int
    uid: int
    post_id: int
    sleeptime: datetime


class WakeTime(NamedTuple):
    pk: int
    uid: int
    post_id: int
    waketime: datetime


class Score(NamedTuple):
    pk: int
    uid: int
    sleep_pk: int
    wake_pk: int
    score: float
    date: date
    owner: int


class Attack(NamedTuple):
    uid: int
    state: int
    target: int
    attack_date: date
    swap_date: date
    confirmed_at: datetime


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

    def insert_sleeptime(self, uid, sleeptime, post_id) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                "insert into sleeptime (uid, sleeptime, post_id) values "
                f"({uid}, '{sleeptime.strftime(DATETIME_FORMAT)}', {post_id}) returning id;"
            )
            inserted_id = cur.fetchone()[0]
            self.conn.commit()
            return inserted_id

    def insert_waketime(self, uid, waketime, post_id) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                "insert into waketime (uid, waketime, post_id) values "
                f"({uid}, '{waketime.strftime(DATETIME_FORMAT)}', {post_id}) returning id;"
            )
            inserted_id = cur.fetchone()[0]
            self.conn.commit()
            return inserted_id

    def insert_score(self, uid, sleep_pk, wake_pk, score, date) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "insert into score (uid, sleep_pk, wake_pk, score, date, owner) values "
                f"({uid}, {sleep_pk}, {wake_pk}, {score}, '{date.strftime(DATE_FORMAT)}', {uid});"
            )
            self.conn.commit()

    def update_score(self, pk, sleep_pk, wake_pk, score) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                f"update score set (sleep_pk, wake_pk, score)=({sleep_pk}, {wake_pk}, {score}) "
                f"where id={pk};"
            )
            self.conn.commit()

    def is_last_sleep_completed(self, uid) -> bool:
        with self.conn.cursor() as cur:
            res_sleeptime = self.get_last_sleep(uid)
            if res_sleeptime is None:
                return True
            cur.execute(f"select sleep_pk from score where uid={uid} order by id desc;")
            res_score = cur.fetchone()
            if res_score is None:
                return False
            return res_sleeptime[0] == res_score[0]

    def get_last_sleep(self, uid) -> SleepTime:
        with self.conn.cursor() as cur:
            cur.execute(
                f"select {SLEEPTIME_COLUMNS} from sleeptime where uid={uid} order by id desc;"
            )
            if (res := cur.fetchone()) is None:
                return None
            return SleepTime(*res)

    def get_last_wake(self, uid) -> WakeTime:
        with self.conn.cursor() as cur:
            cur.execute(
                f"select {WAKETIME_COLUMNS} from waketime where uid={uid} order by id desc;"
            )
            if (res := cur.fetchone()) is None:
                return None
            return WakeTime(*res)

    def get_raw_score(self, uid, date) -> Score:
        with self.conn.cursor() as cur:
            cur.execute(
                f"select {SCORE_COLUMNS} from score where uid={uid} and "
                f"date='{date.strftime(DATE_FORMAT)}';"
            )
            if (res := cur.fetchone()) is None:
                return None
            return Score(*res)

    def get_compare_score(self, my_uid, other_uid, date, dur=True) -> Score:
        op = ">=" if dur else "="
        with self.conn.cursor() as cur:
            cur.execute(
                f"select {SCORE_COLUMNS} from score where owner in ({my_uid}, {other_uid}) "
                f"and date{op}'{date.strftime(DATE_FORMAT)}'"
            )
            return [Score(*t) for t in cur.fetchall()]

    def get_day_score(self, date) -> Score:
        with self.conn.cursor() as cur:
            cur.execute(
                f"select {SCORE_COLUMNS} from score where date='{date.strftime(DATE_FORMAT)}' "
                "order by score desc;"
            )
            return [Score(*t) for t in cur.fetchall()]

    def get_owned_score(self, uid, date) -> Score:
        with self.conn.cursor() as cur:
            cur.execute(
                f"select {SCORE_COLUMNS} from score where owner={uid} and "
                f"date='{date.strftime(DATE_FORMAT)}';"
            )
            if (res := cur.fetchone()) is None:
                return None
            return Score(*res)

    def set_owner(self, pk, uid) -> None:
        with self.conn.cursor() as cur:
            cur.execute(f"update score set owner={uid} where id={pk}")
            self.conn.commit()

    def get_attack_state(self, uid) -> int:
        with self.conn.cursor() as cur:
            cur.execute(f"select state from attack where uid={uid};")
            if (res := cur.fetchone()) is not None:
                return res[0]

            # create a record
            cur.execute(f"insert into attack (uid, state) values ({uid}, 0);")
            self.conn.commit()
            return 0

    def get_active_users(self, date_since) -> List[int]:
        with self.conn.cursor() as cur:
            cur.execute(
                f"select distinct uid from score where date>='{date_since.strftime(DATE_FORMAT)}';"
            )
            return [t[0] for t in cur.fetchall()]

    def set_attack_state(self, uid, state) -> None:
        with self.conn.cursor() as cur:
            cur.execute(f"update attack set state={state} where uid={uid};")
            self.conn.commit()

    def set_target(self, uid, target_uid) -> None:
        with self.conn.cursor() as cur:
            cur.execute(f"update attack set (state, target)=(2, {target_uid}) where uid={uid}")
            self.conn.commit()

    def set_swap_date(self, uid, swap_date) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "update attack set (state, swap_date)="
                f"(3, '{swap_date.strftime(DATE_FORMAT)}') where uid={uid};"
            )
            self.conn.commit()

    def set_attack_date(self, uid, attack_date, confirmed_at) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                f"update attack set (state, attack_date, confirmed_at)="
                f"(4, '{attack_date.strftime(DATE_FORMAT)}', "
                f"'{confirmed_at.strftime(DATETIME_FORMAT)}') where uid={uid};"
            )
            self.conn.commit()

    def get_attack_info(self, uid) -> Attack:
        with self.conn.cursor() as cur:
            cur.execute(f"select {ATTACK_COLUMNS} from attack where uid={uid};")
            if (res := cur.fetchone()) is None:
                return None
            return Attack(*res)

    def delete_attack_record(self, uid) -> None:
        with self.conn.cursor() as cur:
            cur.execute(f"delete from attack where uid={uid};")
            self.conn.commit()

    def get_standby_attack(self, date) -> Attack:
        with self.conn.cursor() as cur:
            cur.execute(
                f"select {ATTACK_COLUMNS} from attack where state=4 and "
                f"attack_date='{date.strftime(DATE_FORMAT)}' order by confirmed_at asc;"
            )
            return [Attack(*t) for t in cur.fetchall()]

    def reset_attack_record(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("delete from attack where state=5;")
            self.conn.commit()
