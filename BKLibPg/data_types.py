from datetime import date, datetime, time
from decimal import Decimal
import ipaddress
import uuid
import base64

class BaseField:
    """
    Clase base para todos los tipos de campos. Define la interfaz y atributos comunes.
    """

    def __init__(self, name, dbname=None, doc="", nullable=True, default=None, primary_key=False, foreign_key="", **kwargs):
        """
        Inicializa un campo base con metainformación para validación y mapeo.

        :param name: Nombre interno del campo.
        :param dbname: Nombre del campo en base de datos. Si no se especifica, se usa `name`.
        :param doc: Descripción del campo.
        :param nullable: Indica si el campo acepta valores nulos.
        :param default: Valor por defecto si no se proporciona uno.
        :param primary_key: Indica si el campo es parte de la clave primaria.
        :param foreign_key: Clave foránea, si aplica.
        :param kwargs: Parámetros adicionales específicos del tipo de campo.
        """
        self.name = name
        self.dbname = dbname or name
        self.doc = doc
        self.nullable = nullable
        self.default = default
        self.primary_key = primary_key
        self.foreign_key = foreign_key
        self.extra = kwargs

    def validate(self, value):
        """
        Método que debe implementar cada tipo de campo para validar su valor.

        :param value: Valor a validar.
        :raises NotImplementedError: Si no es sobreescrito en una subclase.
        """
        raise NotImplementedError("Subclases deben implementar validate")


class StringType(BaseField):
    """
    Campo de tipo cadena de texto (str), con validación de longitud mínima y máxima.
    """

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, str):
            raise TypeError(f"{self.name} debe ser una cadena de texto (str)")
        min_len = self.extra.get("min_length")
        max_len = self.extra.get("max_length")
        if min_len is not None and len(value) < min_len:
            raise ValueError(f"{self.name} debe tener al menos {min_len} caracteres")
        if max_len is not None and len(value) > max_len:
            raise ValueError(f"{self.name} debe tener como máximo {max_len} caracteres")


class IntegerType(BaseField):
    """
    Campo de tipo entero (int), con validación de valor mínimo y máximo.
    """

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                raise TypeError(f"{self.name} debe ser un entero (int) o una cadena convertible a entero")
        if not isinstance(value, int):
            raise TypeError(f"{self.name} debe ser un entero (int)")
        min_val = self.extra.get("min_value")
        max_val = self.extra.get("max_value")
        if min_val is not None and value < min_val:
            raise ValueError(f"{self.name} debe ser >= {min_val}")
        if max_val is not None and value > max_val:
            raise ValueError(f"{self.name} debe ser <= {max_val}")


class FloatType(BaseField):
    """
    Campo numérico de punto flotante (float, decimal). También acepta enteros.
    """

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if isinstance(value, Decimal):
            value = float(value)
        if not isinstance(value, (float, int)):
            raise TypeError(f"{self.name} debe ser numérico (float)")
        min_val = self.extra.get("min_value")
        max_val = self.extra.get("max_value")
        if min_val is not None and value < min_val:
            raise ValueError(f"{self.name} debe ser >= {min_val}")
        if max_val is not None and value > max_val:
            raise ValueError(f"{self.name} debe ser <= {max_val}")


class BooleanType(BaseField):
    """
    Campo booleano (True o False).
    """

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, bool):
            raise TypeError(f"{self.name} debe ser booleano")


class DateType(BaseField):
    """
    Campo de tipo fecha (datetime.date).
    """

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, date):
            raise TypeError(f"{self.name} debe ser una fecha (datetime.date)")


class DateTimeType(BaseField):
    """
    Campo de tipo fecha y hora (datetime.datetime).
    """

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, datetime):
            raise TypeError(f"{self.name} debe ser fecha y hora (datetime.datetime)")


class TimeType(BaseField):
    """
    Campo de tipo hora (datetime.time).
    """

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, time):
            raise TypeError(f"{self.name} debe ser hora (datetime.time)")


class BinaryType(BaseField):
    """
    Campo de tipo binario (bytes o bytearray).
    """

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, (bytes, bytearray)):
            raise TypeError(f"{self.name} debe ser binario (bytes o bytearray)")


class JsonType(BaseField):
    """
    Campo que representa un valor serializable a JSON (dict, list, etc.).
    """

    def validate(self, value):
        import json
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        try:
            json.dumps(value) # Validar serialización
        except Exception:
            raise TypeError(f"{self.name} debe ser un valor JSON válido (dict, list, etc.)")


class UUIDType(BaseField):
    """
    Campo de tipo UUID. También acepta cadenas que representen UUIDs válidos.
    """

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
    """
    Campo que representa una cadena codificada en base64.
    """

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
        """
        Devuelve el contenido decodificado en binario de una cadena base64.

        :param value: Cadena base64 válida.
        :return: Bytes decodificados.
        """
        return base64.b64decode(value, validate=True)


class InetType(BaseField):
    """
    Campo para direcciones IP PostgreSQL tipo INET.
    Acepta IPv4Address, IPv6Address o str válidas.
    """

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return

        if isinstance(value, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            return

        if isinstance(value, str):
            try:
                ipaddress.ip_address(value)
            except ValueError:
                raise ValueError(f"{self.name} no es una dirección IP válida (str)")
            return

        raise TypeError(f"{self.name} debe ser una dirección IP (IPv4/IPv6 o str)")
