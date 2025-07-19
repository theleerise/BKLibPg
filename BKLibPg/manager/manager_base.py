# pg_query_manager.py

from BKLibPg.connection_database import PgConnectionEngine
from psycopg.rows import dict_row

class ManagerBase:
    def __init__(self, connection_engine: PgConnectionEngine):
        self.connection_engine = connection_engine

    def execute_query(self, sql: str, params: dict = None, commit: bool = False):
        try:
            with self.connection_engine.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params or {})
                    if commit:
                        conn.commit()
        except Exception as e:
            raise RuntimeError(f"Error executing query: {e}")

    def fetch_all(self, sql: str, params: dict = None):
        try:
            with self.connection_engine.get_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, params or {})
                    return cur.fetchall()
        except Exception as e:
            raise RuntimeError(f"Error fetching data: {e}")

    def fetch_one(self, sql: str, params: dict = None):
        try:
            with self.connection_engine.get_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, params or {})
                    return cur.fetchone()
        except Exception as e:
            raise RuntimeError(f"Error fetching row: {e}")
        
    @classmethod
    def pydantic_row_factory(model_cls):
        return lambda cur, row: model_cls(**dict_row(cur, row))
