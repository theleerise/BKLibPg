# pg_query_manager.py

from BKLibPg.connection_database import PgConnectionEngine
from psycopg.rows import dict_row

class ManagerBase:
    """
    Clase base para manejar consultas a una base de datos PostgreSQL utilizando un motor de conexión.
    Proporciona métodos para ejecutar consultas, obtener múltiples resultados, obtener un solo resultado
    y generar una fábrica de filas compatible con Pydantic.
    """

    def __init__(self, connection_engine: PgConnectionEngine):
        """
        Inicializa el manager con un motor de conexión a PostgreSQL.

        :param connection_engine: Instancia de PgConnectionEngine para gestionar conexiones.
        """
        self.connection_engine = connection_engine

    def execute_query(self, sql: str, params: dict = None, commit: bool = False):
        """
        Ejecuta una consulta SQL que no devuelve resultados (por ejemplo, INSERT, UPDATE, DELETE).

        :param sql: Cadena SQL a ejecutar.
        :param params: Diccionario de parámetros para la consulta.
        :param commit: Si es True, realiza commit de la transacción.
        :raises RuntimeError: Si ocurre un error durante la ejecución.
        """
        try:
            with self.connection_engine.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params or {})
                    if commit:
                        conn.commit()
        except Exception as e:
            raise RuntimeError(f"Error executing query: {e}")

    def fetch_all(self, sql: str, params: dict = None):
        """
        Ejecuta una consulta SQL y devuelve todos los resultados como una lista de diccionarios.

        :param sql: Cadena SQL a ejecutar.
        :param params: Diccionario de parámetros para la consulta.
        :return: Lista de resultados (cada fila como diccionario).
        :raises RuntimeError: Si ocurre un error durante la ejecución.
        """
        try:
            with self.connection_engine.get_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, params or {})
                    return cur.fetchall()
        except Exception as e:
            raise RuntimeError(f"Error fetching data: {e}")

    def fetch_one(self, sql: str, params: dict = None):
        """
        Ejecuta una consulta SQL y devuelve una sola fila como diccionario.

        :param sql: Cadena SQL a ejecutar.
        :param params: Diccionario de parámetros para la consulta.
        :return: Fila resultante como diccionario, o None si no hay resultados.
        :raises RuntimeError: Si ocurre un error durante la ejecución.
        """
        try:
            with self.connection_engine.get_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, params or {})
                    return cur.fetchone()
        except Exception as e:
            raise RuntimeError(f"Error fetching row: {e}")
        
    @classmethod
    def pydantic_row_factory(model_cls):
        """
        Devuelve una función que transforma cada fila del cursor en una instancia del modelo Pydantic proporcionado.

        :param model_cls: Clase Pydantic a instanciar por fila.
        :return: Función que convierte filas dict_row en instancias del modelo Pydantic.
        """
        return lambda cur, row: model_cls(**dict_row(cur, row))
