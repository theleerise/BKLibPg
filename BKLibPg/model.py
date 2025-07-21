from typing import Type, Dict, List
from typing import Type
import json
from pydantic import create_model
from pydantic import BaseModel as PydanticBaseModel, Field as PydanticField
from BKLibPg.config import Config

PYDANTIC_TYPE_MAP = Config.PYDANTIC_TYPE_EQUIVALENTS
FIELD_TYPE_MAP = Config.FIELD_LAMBDA_TYPE_MAP


class Model:
    fields: dict = {}

    def __init__(self, **kwargs):
        self._data = {}
        for key, field in self.__class__.fields.items():
            value = kwargs.get(field.dbname, field.default)
            field.validate(value)
            self._data[key] = value

    def __getattr__(self, item):
        if item in self._data:
            return self._data[item]
        raise AttributeError(f"No existe el campo '{item}'")

    def __repr__(self):
        return f"<{self.__class__.__name__} {self._data}>"

    def to_dict(self):
        return self._data.copy()

    def to_json(self, **kwargs):
        return json.dumps(self.to_dict(), **kwargs)

    def to_pydantic(self):
        PydanticCls = self.__class__.pydantic_definition_model()
        return PydanticCls(**self.to_dict())

    def get_primary_key(self):
        """
        Devuelve un dict con los valores de los campos que componen la clave primaria.
        Si no hay ninguna clave primaria definida, lanza una excepción.
        """
        pk_fields = {
            key: self._data[key]
            for key, field in self.__class__.fields.items()
            if field.primary_key
        }
        if not pk_fields:
            raise AttributeError("Este modelo no tiene campos de clave primaria definidos.")
        return pk_fields

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str):
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_pydantic(cls, pyd_obj: PydanticBaseModel):
        data = pyd_obj.dict(by_alias=True)
        return cls.from_dict(data)

    @classmethod
    def pydantic_definition_model(cls, name=None) -> Type[PydanticBaseModel]:
        name = name or f"P_{cls.__name__}"
        annotations = {}
        field_defs = {}

        for attr_name, field in cls.fields.items():
            py_type = PYDANTIC_TYPE_MAP.get(type(field), str)
            default = ... if not field.nullable and field.default is None else field.default

            annotations[attr_name] = (py_type, PydanticField(
                default=default,
                description=field.doc or "",
                alias=field.dbname,
            ))

        pydantic_cls = create_model(name, **annotations)
        return pydantic_cls

    @classmethod
    def get_primary_key_definition(cls):
        """
        Devuelve una lista con los nombres de los campos que componen la clave primaria.
        """
        pk_keys = [
            key
            for key, field in cls.fields.items()
            if field.primary_key
        ]
        if not pk_keys:
            raise AttributeError("Este modelo no tiene campos de clave primaria definidos.")
        return pk_keys


class DynamicModel(Model):
    @classmethod
    def configure(cls, definition: dict, registry: Dict[str, Type] = None):
        cls.table_name = definition["table"]
        cls.fields = {}
        registry = registry or {}

        for field_name, info in definition["fields"].items():
            field_type = info.pop("type")
            factory = FIELD_TYPE_MAP.get(field_type)
            if not factory:
                raise ValueError(f"Tipo de campo no reconocido: {field_type}")

            # Foreign key support
            foreign_model = info.pop("foreign_model", None)
            foreign_manager = info.pop("foreign_manager", None)
            if foreign_model:
                info["foreign_model"] = registry.get(foreign_model)
            if foreign_manager:
                info["foreign_manager_class"] = registry.get(foreign_manager)

            cls.fields[field_name] = factory(field_name, **info)
