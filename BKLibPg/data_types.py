from datetime import date, datetime, time
import uuid
import base64

class BaseField:
    def __init__(self, name, dbname=None, doc="", nullable=True, default=None, **kwargs):
        self.name = name
        self.dbname = dbname or name
        self.doc = doc
        self.nullable = nullable
        self.default = default
        self.extra = kwargs

    def validate(self, value):
        raise NotImplementedError("Subclases deben implementar validate")


class FloatType(BaseField):
    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, float) and not isinstance(value, int):  # permitir enteros también
            raise TypeError(f"{self.name} debe ser numérico (float)")
        min_val = self.extra.get("min_value")
        max_val = self.extra.get("max_value")
        if min_val is not None and value < min_val:
            raise ValueError(f"{self.name} debe ser >= {min_val}")
        if max_val is not None and value > max_val:
            raise ValueError(f"{self.name} debe ser <= {max_val}")


class BooleanType(BaseField):
    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, bool):
            raise TypeError(f"{self.name} debe ser booleano")


class DateType(BaseField):
    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, date):
            raise TypeError(f"{self.name} debe ser una fecha (datetime.date)")


class DateTimeType(BaseField):
    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, datetime):
            raise TypeError(f"{self.name} debe ser fecha y hora (datetime.datetime)")


class TimeType(BaseField):
    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, time):
            raise TypeError(f"{self.name} debe ser hora (datetime.time)")


class BinaryType(BaseField):
    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, (bytes, bytearray)):
            raise TypeError(f"{self.name} debe ser binario (bytes o bytearray)")


class JsonType(BaseField):
    def validate(self, value):
        import json
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        try:
            json.dumps(value)  # Validar serialización
        except Exception:
            raise TypeError(f"{self.name} debe ser un valor JSON válido (dict, list, etc.)")


class UUIDType(BaseField):
    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, uuid.UUID):
            if isinstance(value, str):
                try:
                    uuid.UUID(value)
                except Exception:
                    raise ValueError(f"{self.name} debe ser un UUID válido")
            else:
                raise TypeError(f"{self.name} debe ser UUID o string representando UUID")


class Base64Type(BaseField):
    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return

        if not isinstance(value, str):
            raise TypeError(f"{self.name} debe ser una cadena base64")

        try:
            decoded = base64.b64decode(value, validate=True)
            self._decoded = decoded  # guardamos el valor decodificado si hace falta
        except Exception:
            raise ValueError(f"{self.name} no contiene una cadena base64 válida")

    def get_decoded(self, value):
        return base64.b64decode(value, validate=True)
