from typing import Type
from datetime import date, datetime, time
from uuid import UUID
import json
from pydantic import create_model
from pydantic import BaseModel as PydanticBaseModel, Field as PydanticField
from pydantic import Json

from BKLibPg.data_types import (
    StringType,
    IntegerType,
    FloatType,
    BooleanType,
    DateType,
    DateTimeType,
    TimeType,
    BinaryType,
    Base64Type,
    JsonType,
    UUIDType,
)

PYDANTIC_TYPE_MAP = {
    StringType: str,
    IntegerType: int,
    FloatType: float,
    BooleanType: bool,
    DateType: date,
    DateTimeType: datetime,
    TimeType: time,
    BinaryType: bytes,
    Base64Type: str,     # Pydantic no tiene un tipo base64 como tal; se usa `str`
    JsonType: Json,      # Usa el validador `Json` de Pydantic
    UUIDType: UUID,
}


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

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str):
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def to_pydantic_model(cls, name=None) -> Type[PydanticBaseModel]:
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