from abc import ABC, abstractmethod
from typing import List, Type, Optional
from psycopg.rows import dict_row
from BKLibPg.manager.manager_base import ManagerBase
from BKLibPg.query_builders import QueryBuilder, wrapper_where_query, range_row_query
from BKLibPg.model import Model


class ManagerBuilder(ManagerBase, ABC):
    """
    Clase base abstracta para managers CRUD (Create, Read, Update, Delete)
    que gestionan operaciones sobre tablas PostgreSQL utilizando modelos personalizados.

    Esta clase se basa en `ManagerBase` y permite extender operaciones estándar
    mediante puntos de anclaje (`before_` y `after_` hooks) y SQL autogenerado
    basado en los metadatos del modelo.

    Parámetros:
        connection_engine: instancia de PgConnectionEngine para manejar conexiones.
        input_model: clase que representa los datos de entrada (ej. para insert/update).
        output_model: clase que representa los datos leídos desde la base (ej. para consultas).
        table_name: nombre de la tabla principal sobre la cual se harán las operaciones.
        id_field: nombre del campo clave primaria (por defecto: "id").
    """

    def __init__(
        self,
        connection_engine,
        input_model: Type[Model],
        output_model: Type[Model],
        table_name: str,
        id_field: str = "id"
    ):
        super().__init__(connection_engine)
        self.input_model = input_model
        self.output_model = output_model
        self.table_name = table_name
        self.id_field = id_field

    #################################################################
    ### Métodos SQL (sobrescribibles si se desea lógica especial) ###
    #################################################################

    def _get_sql_query(self) -> str:
        """
        Genera la sentencia SQL SELECT base según los campos definidos
        en el modelo de salida (`output_model`).
        """
        columns = ", ".join(
            f"{f.dbname} AS {fname}" for fname, f in self.output_model.fields.items()
        )
        return f"SELECT {columns} FROM {self.table_name}"

    def _get_sql_insert(self) -> str:
        """
        Genera la sentencia SQL INSERT dinámica basada en los campos del `input_model`.
        """
        fields = [f.dbname for f in self.input_model.fields.values()]
        cols = ", ".join(fields)
        vals = ", ".join([f"%({f})s" for f in fields])
        return f"INSERT INTO {self.table_name} ({cols}) VALUES ({vals})"

    def _get_sql_update(self) -> str:
        """
        Genera la sentencia SQL UPDATE dinámica basada en los campos del `input_model`.
        Excluye el campo `id_field` de la cláusula SET.
        """
        sets = ", ".join([
            f"{f.dbname} = %({f.dbname})s"
            for fname, f in self.input_model.fields.items()
            if f.name != self.id_field
        ])
        return f"UPDATE {self.table_name} SET {sets} WHERE {self.id_field} = %({self.id_field})s"

    def _get_sql_delete(self) -> str:
        """
        Genera la sentencia SQL DELETE que elimina un registro por su clave primaria.
        """
        return f"DELETE FROM {self.table_name} WHERE {self.id_field} = %({self.id_field})s"

    def run_transaction(self, fn):
        """
        Ejecuta una función que recibe un cursor dentro de una transacción controlada.
        Permite agrupar múltiples operaciones en la misma transacción y conexión.

        Parámetros:
            fn: función que recibe un cursor como argumento.

        Retorna:
            El valor que retorne la función `fn`, si aplica.

        Lanza:
            RuntimeError en caso de error, para asegurar rollback.
        """
        try:
            with self.connection_engine.get_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    result = fn(cur)
                    conn.commit()
                    return result
        except Exception as e:
            raise RuntimeError(f"Transaction failed: {e}")

    #################################################################
    ######################### CRUD públicos ######################### 
    #################################################################

    def getlist(self, filters: List[dict] = None, params: List[dict] = None) -> List[Model]:
        """
        Devuelve una lista de modelos aplicando filtros dinámicos.

        Parámetros:
            filters: lista de definiciones de filtro (columna, operador, función).
            params: lista de diccionarios con valores para los filtros.

        Retorna:
            Lista de modelos.
        """
        sql_base = wrapper_where_query(self._get_sql_query())
        if filters and params:
            qb = QueryBuilder(sql_base, filters, params)
            final_sql, bind_params = qb.build()
        else:
            final_sql = sql_base
            bind_params = {}

        rows = self.fetch_all(final_sql, bind_params)
        return [self.output_model.from_dict(r) for r in rows]

    def getlist_paginated(
        self,
        filters: List[dict] = None,
        params: List[dict] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Model]:
        """
        Devuelve una lista paginada de modelos aplicando filtros dinámicos.
    
        Parámetros:
            filters: lista de definiciones de filtro.
            params: lista de diccionarios con valores de filtro.
            limit: máximo de filas por página.
            offset: desplazamiento de filas.
    
        Retorna:
            Lista de modelos.
        """
        sql_base = wrapper_where_query(self._get_sql_query())
        if filters and params:
            qb = QueryBuilder(sql_base, filters, params)
            sql_with_filters, bind_params = qb.build()
        else:
            sql_with_filters = sql_base
            bind_params = {}
    
        paginated_sql = range_row_query(sql_with_filters, offset=offset, limit=limit)
        rows = self.fetch_all(paginated_sql, bind_params)
        return [self.output_model.from_dict(r) for r in rows]

    def getlist_page(
        self,
        page: int = 1,
        page_size: int = 10,
        filters: List[dict] = None,
        params: List[dict] = None
    ) -> List[Model]:
        """
        Devuelve una lista paginada por número de página y tamaño, con filtros dinámicos.

        Parámetros:
            page: número de página (1-indexado).
            page_size: cantidad de registros por página.
            filters: lista de definiciones de filtro.
            params: valores de los filtros.

        Retorna:
            Lista de modelos en la página solicitada.
        """
        offset = (page - 1) * page_size
        return self.getlist_paginated(filters=filters, params=params, limit=page_size, offset=offset)

    def before_insert(self, model_obj: Model) -> Model:
        """
        Hook opcional que se ejecuta antes de un INSERT.
        Puede usarse para validar o transformar datos.

        Retorna:
            El objeto modelo (modificado o no).
        """
        return model_obj

    def insert(self, data: dict) -> None:
        """
        Inserta un nuevo registro en la base de datos.

        Parámetros:
            data: diccionario de datos a insertar, compatible con el modelo de entrada.
        """
        def _tx(cur):
            model_obj = self.input_model(**data)
            model_obj = self.before_insert(model_obj)
            cur.execute(self._get_sql_insert(), model_obj.to_dict())
            self.after_insert(model_obj)

        self.run_transaction(_tx)

    def after_insert(self, model_obj: Model) -> None:
        """
        Hook opcional que se ejecuta después de un INSERT exitoso.
        """
        pass

    def before_update(self, model_obj: Model) -> Model:
        """
        Hook opcional que se ejecuta antes de un UPDATE.
        """
        return model_obj

    def update(self, data: dict) -> None:
        """
        Actualiza un registro existente en base al `id_field`.

        Parámetros:
            data: diccionario con los datos a actualizar, incluyendo la clave primaria.
        """
        def _tx(cur):
            model_obj = self.input_model(**data)
            model_obj = self.before_update(model_obj)
            cur.execute(self._get_sql_update(), model_obj.to_dict())
            self.after_update(model_obj)

        self.run_transaction(_tx)

    def after_update(self, model_obj: Model) -> None:
        """
        Hook opcional que se ejecuta después de un UPDATE exitoso.
        """
        pass

    def before_delete(self, model_obj: Model) -> Model:
        """
        Hook opcional que se ejecuta antes de un DELETE.
        """
        return model_obj

    def delete(self, data: dict) -> None:
        """
        Elimina un registro de la base de datos por su clave primaria.

        Parámetros:
            data: debe incluir el valor de la clave primaria (`id_field`).
        """
        def _tx(cur):
            model_obj = self.input_model(**data)
            model_obj = self.before_delete(model_obj)
            cur.execute(self._get_sql_delete(), model_obj.to_dict())
            self.after_delete(model_obj)

        self.run_transaction(_tx)

    def after_delete(self, model_obj: Model) -> None:
        """
        Hook opcional que se ejecuta después de un DELETE exitoso.
        """
        pass

    def execute_procedure(self, proc_name: str, params: dict = None) -> None:
        """
        Ejecuta un procedimiento almacenado en la base de datos (CALL).

        Parámetros:
            proc_name: nombre del procedimiento.
            params: diccionario de parámetros para el procedimiento.
        """
        sql = f"CALL {proc_name}({', '.join(f'%({k})s' for k in (params or {}))})"
        self.execute_query(sql, params or {}, commit=True)

    def execute_function(self, func_name: str, params: dict = None):
        """
        Ejecuta una función almacenada en PostgreSQL y devuelve el resultado.

        Parámetros:
            func_name: nombre de la función.
            params: parámetros como diccionario.

        Retorna:
            Valor devuelto por la función, o None si no hay resultado.
        """
        sql = f"SELECT {func_name}({', '.join(f'%({k})s' for k in (params or {}))}) AS result"
        row = self.fetch_one(sql, params or {})
        return row.get("result") if row else None
