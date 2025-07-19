from __future__ import annotations
from collections import defaultdict
from typing import Any, Dict, List, Tuple

def wrapper_where_query(query: str) -> str:
    """
    Envuelve una consulta SQL arbitraria dentro de un sub-select y añade un
    comodín `WHERE 1 = 1`, lo que facilita concatenar luego condiciones
    adicionales sin preocuparse por la sintaxis del primer «WHERE».

    Parameters
    ----------
    query : str
        Cadena con la consulta SQL original que se desea encapsular.

    Returns
    -------
    str
        Consulta SQL formateada, lista para ampliar con cláusulas
        `AND ...` si es necesario.

    Notes
    -----
    - `WHERE 1 = 1` es una técnica habitual para simplificar la
      generación dinámica de filtros: todas las condiciones siguientes se
      introducen simplemente con `AND`.
    - La función **no** valida ni escapa la consulta recibida; se asume
      que `query` es una cadena SQL segura y bien formada.

    Examples
    --------
    >>> raw_query = "SELECT id, nombre FROM clientes"
    >>> wrapper_where_query(raw_query)
    '\\n        SELECT * FROM (\\n            SELECT id, nombre FROM clientes\\n        ) WHERE 1=1\\n    '
    >>> # Añadir filtros dinámicos
    >>> final_query = wrapper_where_query(raw_query) + " AND fecha_alta >= :fecha_ini"
    """
    format_query = f"""
        SELECT * FROM (
            {query}
        ) WHERE 1=1
    """
    return format_query

def counter_row_query(query: str) -> str:
    """
    Genera una sub-consulta que devuelve el número total de filas
    que produciría la sentencia SQL original.

    Se envuelve la consulta recibida en un `SELECT COUNT(*) FROM (...)`
    para obtener el recuento sin necesidad de ejecutar la consulta
    completa.

    Args:
        query (str): Sentencia SQL sobre la que se desea calcular
            el número de filas resultantes.

    Returns:
        str: Cadena SQL con la sub-consulta de conteo.

    Example:
        >>> sql_base = "SELECT * FROM users WHERE active = 1"
        >>> print(counter_row_query(sql_base))
        SELECT COUNT(*) FROM (
            SELECT * FROM users WHERE active = 1
        ) QUERY_COUNT
    """
    format_query = f"""
        SELECT COUNT(*) AS COUNTER FROM (
            {query}
        ) QUERY_COUNT
    """
    return format_query

def range_row_query(query: str, offset: int, limit: int) -> str:
    """
    Añade paginación basada en `OFFSET … FETCH NEXT …` a la sentencia SQL.

    Ideal para bases de datos que soportan la sintaxis de paginación
    estilo ANSI/ISO (por ejemplo, SQL Server 2012+, Oracle 12c,
    PostgreSQL v13+ con `FETCH`).

    Args:
        query (str): Consulta SQL original sin cláusulas de paginación.
        offset (int): Número de filas que se omitirán (*OFFSET*).
        limit (int): Número máximo de filas que se devolverán
            (*FETCH NEXT … ROWS ONLY*).

    Returns:
        str: Consulta SQL paginada.

    Raises:
        ValueError: Si `offset` o `limit` son negativos.

    Example:
        >>> sql_base = "SELECT id, name FROM products ORDER BY name"
        >>> print(range_row_query(sql_base, offset=20, limit=10))
        SELECT id, name FROM products ORDER BY name
        OFFSET 20 ROWS FETCH NEXT 10 ROWS ONLY
    """
    if offset < 0 or limit < 0:
        raise ValueError("offset y limit deben ser valores no negativos")

    format_query = f"""
        {query}
        OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY
    """
    return format_query


class QueryBuilder:
    """
    Constructor dinámico de consultas SQL para PostgreSQL.

    Esta clase permite construir cláusulas WHERE de forma dinámica a partir de
    filtros y valores proporcionados, utilizando parámetros nombrados en el
    formato de `psycopg2` (%(parametro)s). Soporta operadores como `=`, `!=`,
    `>`, `LIKE`, `IN`, `BETWEEN`, y funciones SQL sobre las columnas.

    Ejemplo básico de uso:
        base_sql = "SELECT * FROM empleados WHERE 1=1"
        filters = [{"column": "nombre", "condition": {"operator": "like", "function": "UPPER"}}]
        values = [{"nombre": "%PÉREZ%"}]

        qb = BKPgQueryBuilder(base_sql, filters, values)
        sql, params = qb.build()

    Resultado:
        sql =>
        SELECT * FROM empleados WHERE 1=1
        AND UPPER(nombre) ILIKE %(nombre)s

        params => {'nombre': '%PÉREZ%'}
    """

    _OPERATOR_MAP = {
        "equal": "=",
        "not_equal": "!=",
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
        "like": "ILIKE",   # PostgreSQL usa ILIKE para comparación insensible a mayúsculas
        "in": "IN",
        "between": "BETWEEN",
    }

    def __init__(
        self,
        base_sql: str,
        filters: List[Dict[str, Any]],
        values: List[Dict[str, Any]],
    ) -> None:
        """
        Inicializa el query builder con la sentencia base y los filtros.

        Args:
            base_sql (str): Sentencia SQL inicial, por ejemplo: 'SELECT * FROM tabla WHERE 1=1'
            filters (List[Dict]): Lista de filtros con estructura:
                {
                    "column": "nombre_columna",
                    "condition": {
                        "operator": "gt" | "like" | "between" | etc,
                        "function": "UPPER" | "LOWER" | etc (opcional)
                    }
                }
            values (List[Dict]): Lista de diccionarios con los valores para cada filtro.
                Ejemplo: [{"nombre": "Juan"}, {"nombre": "Pedro"}]
        """
        self.base_sql = base_sql.rstrip()
        self.filters = filters
        self.values = values

        self._bind_counter: Dict[str, int] = defaultdict(int)
        self._params: Dict[str, Any] = {}
        self._where_clauses: List[str] = []

    def build(self) -> Tuple[str, Dict[str, Any]]:
        """
        Construye la sentencia SQL final con filtros dinámicos y sus parámetros.

        Returns:
            Tuple[str, Dict[str, Any]]: Una tupla con:
                - SQL con cláusulas WHERE generadas
                - Diccionario de parámetros para el motor de base de datos
        """
        for rule in self.filters:
            column = rule["column"]
            cond = rule.get("condition", {})
            operator = cond.get("operator", "equal").lower()
            func = cond.get("function", "").strip().upper()

            vals = self._extract_column_values(column)
            if not vals:
                continue

            sql_column = f"{func}({column})" if func else column

            if operator == "between":
                self._handle_between(sql_column, column, vals)
            elif len(vals) == 1 and operator != "in":
                self._handle_single(sql_column, column, vals[0], operator)
            else:
                self._handle_in(sql_column, column, vals)

        sql = "\n".join([self.base_sql, *self._where_clauses])
        return sql, self._params

    def _extract_column_values(self, column: str) -> List[Any]:
        """
        Extrae todos los valores asociados a una columna específica desde `self.values`.

        Args:
            column (str): Nombre de la columna a buscar.

        Returns:
            List[Any]: Lista de valores asociados a la columna.
        """
        return [entry[column] for entry in self.values if column in entry]

    def _next_bind(self, column: str) -> str:
        """
        Genera un nombre único para el parámetro de bind de una columna.

        Args:
            column (str): Nombre base de la columna.

        Returns:
            str: Nombre del parámetro único, por ejemplo 'columna_copy1'.
        """
        count = self._bind_counter[column]
        self._bind_counter[column] += 1
        return f"{column}" if count == 0 else f"{column}_copy{count}"

    def _handle_single(self, sql_col: str, column: str, value: Any, op: str) -> None:
        """
        Crea una cláusula WHERE para un valor único (operadores: =, >, <, etc).

        Args:
            sql_col (str): Columna o expresión SQL.
            column (str): Nombre de la columna sin función.
            value (Any): Valor a usar en la comparación.
            op (str): Operador lógico ('equal', 'gt', etc).
        """
        bind = self._next_bind(column)
        self._params[bind] = value
        sql_op = self._OPERATOR_MAP.get(op, "=")
        self._where_clauses.append(f"AND {sql_col} {sql_op} %({bind})s")

    def _handle_in(self, sql_col: str, column: str, values: List[Any]) -> None:
        """
        Crea una cláusula WHERE para múltiples valores con el operador IN.

        Args:
            sql_col (str): Columna o expresión SQL.
            column (str): Nombre de la columna sin función.
            values (List[Any]): Lista de valores.
        """
        bind_names = []
        for val in values:
            bind = self._next_bind(column)
            self._params[bind] = val
            bind_names.append(f"%({bind})s")
        placeholders = ", ".join(bind_names)
        self._where_clauses.append(f"AND {sql_col} IN ({placeholders})")

    def _handle_between(self, sql_col: str, column: str, values: List[Any]) -> None:
        """
        Crea una cláusula WHERE para un rango BETWEEN con dos valores.

        Args:
            sql_col (str): Columna o expresión SQL.
            column (str): Nombre de la columna sin función.
            values (List[Any]): Lista con exactamente dos elementos (inicio y fin).

        Raises:
            ValueError: Si no se proporcionan exactamente 2 valores.
        """
        if len(values) != 2:
            raise ValueError(
                f"El operador BETWEEN requiere exactamente 2 valores para '{column}', "
                f"pero se recibieron {len(values)}."
            )
        lower_bind = self._next_bind(column)
        upper_bind = self._next_bind(column)
        self._params[lower_bind], self._params[upper_bind] = values
        clause = f"AND {sql_col} BETWEEN %({lower_bind})s AND %({upper_bind})s"
        self._where_clauses.append(clause)

"""
#######################################################################################
# Example Nº1:
base_sql = "SELECT * FROM empleados WHERE 1=1"

filters = [
    {"column": "departamento"},
    {"column": "estado"},
]
values = [
    {"departamento": "TI"},
    {"estado": "ACTIVO"},
]

SELECT * FROM empleados WHERE 1=1
AND departamento = %(departamento)s
AND estado = %(estado)s

#######################################################################################
# Example Nº2:
base_sql = "SELECT * FROM empleados WHERE 1=1"

filters = [
    {"column": "ciudad"},
    {"column": "puesto"},
]
values = [
    {"ciudad": "Madrid"},
    {"ciudad": "Sevilla"},
    {"puesto": "Analista"},
    {"puesto": "Jefe de Proyecto"},
]

SELECT * FROM empleados WHERE 1=1
AND ciudad IN (%(ciudad)s, %(ciudad_copy1)s)
AND puesto IN (%(puesto)s, %(puesto_copy1)s)

########################################################################################
# Example Nº3:

Base_sql = "SELECT * FROM empleados WHERE 1=1"

filters = [
    {"column": "fecha_ingreso", "condition": {"operator": "between"}},
    {"column": "salario", "condition": {"operator": "gte"}},
    {"column": "nombre", "condition": {"operator": "like", "function": "UPPER"}},
]
values = [
    {"fecha_ingreso": "2020-01-01"},
    {"fecha_ingreso": "2023-12-31"},
    {"salario": 3000},
    {"nombre": "%PÉREZ%"},
]

SELECT * FROM empleados WHERE 1=1
AND fecha_ingreso BETWEEN %(fecha_ingreso)s AND %(fecha_ingreso_copy1)s
AND salario >= %(salario)s
AND UPPER(nombre) ILIKE %(nombre)s

#########################################################################################
# Example Nº4:

base_sql = "SELECT * FROM empleados WHERE 1=1"

filters = [
    {"column": "edad", "condition": {"operator": "gt"}},
    {"column": "ciudad", "condition": {"operator": "in"}},
    {"column": "fecha_nacimiento", "condition": {"operator": "between"}},
    {"column": "estado", "condition": {"operator": "not_equal"}},
    {"column": "email", "condition": {"operator": "like", "function": "LOWER"}},
]
values = [
    {"edad": 25},
    {"ciudad": "Madrid"},
    {"ciudad": "Barcelona"},
    {"fecha_nacimiento": "1980-01-01"},
    {"fecha_nacimiento": "2000-12-31"},
    {"estado": "INACTIVO"},
    {"email": "%@empresa.com"},
]

SELECT * FROM empleados WHERE 1=1
AND edad > %(edad)s
AND ciudad IN (%(ciudad)s, %(ciudad_copy1)s)
AND fecha_nacimiento BETWEEN %(fecha_nacimiento)s AND %(fecha_nacimiento_copy1)s
AND estado != %(estado)s
AND LOWER(email) ILIKE %(email)s


##########################################################################################
# Example Nº5:

base_sql = "SELECT * FROM empleados WHERE 1=1"

filters = [
    {"column": "tipo_contrato"},  # sin operador -> usa `equal` o `in` implícitamente
    {"column": "jornada"},        # igual
]
values = [
    {"tipo_contrato": "TEMPORAL"},
    {"tipo_contrato": "FIJO"},
    {"jornada": "COMPLETA"},
    {"jornada": "PARCIAL"},
]

SELECT * FROM empleados WHERE 1=1
AND tipo_contrato IN (%(tipo_contrato)s, %(tipo_contrato_copy1)s)
AND jornada IN (%(jornada)s, %(jornada_copy1)s)

###########################################################################################
# Example Nº6:

base_sql = "SELECT * FROM empleados WHERE 1=1"
filters = [
    {"column": "categoria"},
    {"column": "nivel"},
    {"column": "salario", "condition": {"operator": "gte"}},
    {"column": "fecha_alta", "condition": {"operator": "between"}},
    {"column": "nombre", "condition": {"operator": "like", "function": "UPPER"}},
    {"column": "activo", "condition": {"operator": "equal"}},
]
values = [
    {"categoria": "A"},
    {"categoria": "B"},
    {"nivel": "Junior"},
    {"nivel": "Senior"},
    {"salario": 1500},
    {"fecha_alta": "2021-01-01"},
    {"fecha_alta": "2022-12-31"},
    {"nombre": "%PÉREZ%"},
    {"activo": True},
]

SELECT * FROM empleados WHERE 1=1
AND categoria IN (%(categoria)s, %(categoria_copy1)s)
AND nivel IN (%(nivel)s, %(nivel_copy1)s)
AND salario >= %(salario)s
AND fecha_alta BETWEEN %(fecha_alta)s AND %(fecha_alta_copy1)s
AND UPPER(nombre) ILIKE %(nombre)s
AND activo = %(activo)s

"""