# pg_connection_engine.py

import os
import psycopg
from psycopg_pool import ConnectionPool

class PgConnectionEngine:
    def __init__(self,
                 dbname=None,
                 user=None,
                 password=None,
                 host='localhost',
                 port=5432,
                 use_pool=False,
                 min_size=1,
                 max_size=5):
        self.dbname = dbname or os.getenv('PGDATABASE')
        self.user = user or os.getenv('PGUSER')
        self.password = password or os.getenv('PGPASSWORD')
        self.host = host or os.getenv('PGHOST', 'localhost')
        self.port = port or int(os.getenv('PGPORT', 5432))
        self.use_pool = use_pool

        self._pool = None
        if use_pool:
            self._create_pool(min_size, max_size)

    def _get_dsn(self):
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"

    def _create_pool(self, min_size, max_size):
        self._pool = ConnectionPool(
            conninfo=self._get_dsn(),
            min_size=min_size,
            max_size=max_size,
            timeout=10
        )

    def get_connection(self):
        if self.use_pool:
            return self._pool.connection()
        else:
            return psycopg.connect(self._get_dsn())

    def close_pool(self):
        if self._pool:
            self._pool.close()
