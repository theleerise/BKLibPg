from typing import Type
import json
from pydantic import create_model
from pydantic import BaseModel as PydanticBaseModel, Field as PydanticField
from BKLibPg.config import Config

PYDANTIC_TYPE_MAP = Config.PYDANTIC_TYPE_EQUIVALENTS


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