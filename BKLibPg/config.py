from datetime import date, datetime, time
from uuid import UUID
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

class Config:
    """
    Configuration class for BKLibPg.
    This class holds the configuration settings for the library.
    """

    # Database connection settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "mydatabase"
    DB_USER: str = "myuser"
    DB_PASSWORD: str = "mypassword"

    # Other configuration settings can be added here
    DATABASE_OPERATORS = {
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
    
    PYDANTIC_TYPE_EQUIVALENTS = {
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
    
    FIELD_LAMBDA_TYPE_MAP = {
        "string": lambda name, **kwargs: StringType(name, **kwargs),
        "integer": lambda name, **kwargs: IntegerType(name, **kwargs),
        "float": lambda name, **kwargs: FloatType(name, **kwargs),
        "boolean": lambda name, **kwargs: BooleanType(name, **kwargs),
        "date": lambda name, **kwargs: DateType(name, **kwargs),
        "datetime": lambda name, **kwargs: DateTimeType(name, **kwargs),
        "time": lambda name, **kwargs: TimeType(name, **kwargs),
        "json": lambda name, **kwargs: JsonType(name, **kwargs),
        "binary": lambda name, **kwargs: BinaryType(name, **kwargs),
        "uuid": lambda name, **kwargs: UUIDType(name, **kwargs),
        "base64": lambda name, **kwargs: Base64Type(name, **kwargs),
    }