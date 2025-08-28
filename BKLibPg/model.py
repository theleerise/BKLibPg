from typing import Type, Dict
import json
from pydantic import create_model
from pydantic import BaseModel as PydanticBaseModel, Field as PydanticField
from BKLibPg.config import Config
from BKLibPg.data_types import BaseField

PYDANTIC_TYPE_MAP = Config.PYDANTIC_TYPE_EQUIVALENTS
FIELD_TYPE_MAP = Config.FIELD_LAMBDA_TYPE_MAP


class Model:
    """
    Clase base para representar un modelo de datos con validación y conversión a formatos comunes.
    """
    fields: dict = {}

    def __init__(self, **kwargs):
        """
        Inicializa una instancia del modelo utilizando los valores proporcionados en `kwargs`.
        Valida cada campo de acuerdo con su definición.
        """
        self._data = {}
        for key, field in self.__class__.fields.items():
            value = kwargs.get(field.dbname, field.default)
            field.validate(value)
            self._data[key] = value

    def __getattr__(self, item):
        """
        Permite acceder a los valores de los campos como atributos del objeto.
        Lanza AttributeError si el campo no existe.
        """
        if item in self._data:
            return self._data[item]
        raise AttributeError(f"No existe el campo '{item}'")

    def __repr__(self):
        """
        Representación textual de la instancia del modelo.
        """
        return f"<{self.__class__.__name__} {self._data}>"

    def to_dict(self):
        """
        Convierte el modelo a un diccionario.
        
        :return: Diccionario con los datos del modelo.
        """
        return self._data.copy()

    def to_json(self, **kwargs):
        """
        Convierte el modelo a una cadena JSON.
        
        :param kwargs: Parámetros adicionales para `json.dumps`.
        :return: Cadena JSON.
        """
        return json.dumps(self.to_dict(), **kwargs)

    def to_pydantic(self):
        """
        Convierte la instancia actual del modelo a una instancia Pydantic.
        
        :return: Instancia de un modelo Pydantic equivalente.
        """
        PydanticCls = self.__class__.pydantic_definition_model()
        return PydanticCls(**self.to_dict())

    def get_primary_key(self):
        """
        Devuelve un dict con los valores de los campos que componen la clave primaria.
        Si no hay ninguna clave primaria definida, lanza una excepción.
        
        :return: Diccionario con los campos clave primaria.
        :raises AttributeError: Si no hay claves primarias definidas.
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
        """
        Crea una instancia del modelo a partir de un diccionario.
        
        :param data: Diccionario con los datos del modelo.
        :return: Instancia del modelo.
        """
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str):
        """
        Crea una instancia del modelo a partir de una cadena JSON.
        
        :param json_str: Cadena JSON.
        :return: Instancia del modelo.
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_pydantic(cls, pyd_obj: PydanticBaseModel):
        """
        Crea una instancia del modelo a partir de un modelo Pydantic.
        
        :param pyd_obj: Instancia Pydantic.
        :return: Instancia del modelo.
        """
        data = pyd_obj.dict(by_alias=True)
        return cls.from_dict(data)

    @classmethod
    def pydantic_definition_model(cls, name=None) -> Type[PydanticBaseModel]:
        """
        Genera una clase Pydantic equivalente al modelo actual.
        
        :param name: Nombre opcional para el modelo generado.
        :return: Clase de modelo Pydantic.
        """
        name = name or f"P_{cls.__name__}"
        annotations = {}

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
    def json_definition_model(cls, **kwargs) -> str:
        """
        Devuelve un JSON con la definición estructural del modelo,
        incluyendo metadatos de cada campo como nombre, tipo, nulabilidad, etc.

        :param kwargs: Parámetros adicionales para `json.dumps`.
        :return: Cadena JSON con la definición de los campos.
        
        :example:
        print(model_usuario.json_definition_model(indent=4))

        {
            "model": "Usuario",
            "fields": {
                "id": {
                    "name": "id",
                    "dbname": "id",
                    "type": "IntegerType",
                    "doc": "Identificador único",
                    "nullable": false,
                    "default": null,
                    "primary_key": true,
                    "foreign_key": "",
                    "master": "",
                    "extra": {}
                },
                "email": {
                    "name": "email",
                    "dbname": "email",
                    "type": "EmailType",
                    "doc": "Correo del usuario",
                    "nullable": false,
                    "default": null,
                    "primary_key": false,
                    "foreign_key": "",
                    "master": "USUARIOS_MAIL",,
                    "extra": {}
                }
            }
        }
        """
        def field_definition(field: BaseField):
            return {
                "name": field.name,
                "dbname": field.dbname,
                "type": type(field).__name__,
                "doc": field.doc,
                "nullable": field.nullable,
                "default": field.default,
                "primary_key": field.primary_key,
                "foreign_key": field.foreign_key,
                "master": field.master,
                "extra": field.extra
            }

        definition = {
            "model": cls.__name__,
            "table": getattr(cls, "table_name", None),
            "fields": {
                field_name: field_definition(field)
                for field_name, field in cls.fields.items()
            }
        }
        return json.dumps(definition, **kwargs)

    @classmethod
    def get_primary_key_definition(cls):
        """
        Devuelve una lista con los nombres de los campos que componen la clave primaria.
        
        :return: Lista de nombres de campos clave primaria.
        :raises AttributeError: Si no hay claves primarias definidas.
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
    """
    Clase que permite crear modelos dinámicamente a partir de una definición estructurada.
    """

    @classmethod
    def configure(cls, definition: dict, registry: Dict[str, Type] = None):
        """
        Configura la clase dinámica con los campos definidos en `definition`.

        :param definition: Diccionario con la definición del modelo (tabla y campos).
        :param registry: Diccionario de clases disponibles para claves foráneas.
        :raises ValueError: Si el tipo de campo no es reconocido.
        """
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
