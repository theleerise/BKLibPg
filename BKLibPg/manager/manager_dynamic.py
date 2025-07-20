from typing import Dict, Type
from BKLibPg.model import DynamicModel
from BKLibPg.manager.manager_builder import ManagerBuilder


class DynamicManager(ManagerBuilder):
    @classmethod
    def configure(cls, connection_engine, model_definition: dict, registry: Dict[str, Type] = None, id_field: str = "id"):
        DynamicModel.configure(model_definition, registry)
        return cls(
            connection_engine=connection_engine,
            input_model=DynamicModel,
            output_model=DynamicModel,
            table_name=DynamicModel.table_name,
            id_field=id_field
        )

"""
definition = {
    "model_name": "ProductoModel",
    "table": "public.producto",
    "id_field": "id",
    "fields": {
        "id": {"type": "integer", "nullable": False},
        "nombre": {"type": "string"},
        "precio": {"type": "float", "nullable": False, "min_value": 0},
        "categoria_id": {
            "type": "integer",
            "nullable": True,
            "foreign_model": "CategoriaModel",
            "foreign_manager": "CategoriaManager"
        }
    }
}

registry = {
    "CategoriaModel": CategoriaModel,
    "CategoriaManager": CategoriaManager
}

manager = DynamicManager.configure(connection_engine, definition, registry)
registros = manager.getlist()

"""