# pg_connection_engine.py

from BKLibPg.config import Config
import os
import psycopg
from psycopg_pool import ConnectionPool

class PgConnectionEngine:
    """
    Clase para manejar la conexión a la base de datos PostgreSQL.
    Esta clase permite establecer una conexión a la base de datos y manejar un pool de conexiones.
    Se puede usar para ejecutar consultas y transacciones de manera eficiente.
    
    :param dbname: Nombre de la base de datos.
    :param user: Usuario de la base de datos.
    :param password: Contraseña del usuario de la base de datos.
    :param host: Dirección del servidor de la base de datos.
    :param port: Puerto del servidor de la base de datos.
    :param use_pool: Si se debe usar un pool de conexiones.
    :param min_size: Tamaño mínimo del pool de conexiones.
    :param max_size: Tamaño máximo del pool de conexiones.
    :raises ValueError: Si los parámetros de conexión son inválidos.
    :raises psycopg.OperationalError: Si no se puede conectar a la base de datos.
    :raises psycopg.InterfaceError: Si hay un error en la interfaz de conexión.
    :raises psycopg.DatabaseError: Si hay un error en la base de datos.
    :raises psycopg.ProgrammingError: Si hay un error de programación en la consulta.
    :raises psycopg.DataError: Si hay un error de datos en la consulta.
    :raises psycopg.IntegrityError: Si hay un error de integridad en
    
    Private methods:
    - `_get_dsn`: Construye la cadena de conexión DSN para PostgreSQL.
    - `_create_pool`: Crea un pool de conexiones si `use_pool` es `True`.
    
    Public methods:
    - `get_connection`: Obtiene una conexión de la base de datos, ya sea del pool o una nueva.
    - `close_pool`: Cierra el pool de conexiones si se está utilizando.
    """
    
    DATABASE_CONFIG =  Config()

    def __init__(self,
                 dbname=None,
                 user=DATABASE_CONFIG.DB_USER,
                 password=DATABASE_CONFIG.DB_PASSWORD,
                 host=DATABASE_CONFIG.DB_HOST,
                 port=DATABASE_CONFIG.DB_PORT,
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
