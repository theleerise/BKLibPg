from datetime import date, datetime, time, timedelta
from decimal import Decimal
import json as _json
import ipaddress, uuid, re
from urllib.parse import urlparse
import base64
import unicodedata

class BaseField:
    """
    Clase base para todos los tipos de campos. Define la interfaz y atributos comunes.
    """

    def __init__(self, name, dbname=None, doc="", nullable=True, default=None, primary_key=False, foreign_key="", master="", **kwargs):
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
        self.master = master
        self.extra = kwargs

    def deserialize(self, value):
        # Por defecto, no hace nada; las subclases que necesiten conversión la implementan.
        return value

    def validate(self, value):
        """
        Método que debe implementar cada tipo de campo para validar su valor.

        :param value: Valor a validar.
        :raises NotImplementedError: Si no es sobreescrito en una subclase.
        """
        raise NotImplementedError("Subclases deben implementar validate")

def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).strip().lower()

class StringType(BaseField):
    def deserialize(self, value):
        if value is None:
            return None
        return str(value)

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
    def deserialize(self, value):
        if value is None:
            return None
        if isinstance(value, bool):
            # Evitar True/False como enteros
            raise TypeError(f"{self.name} no debe ser booleano")
        if isinstance(value, int):
            return value
        if isinstance(value, (float, Decimal)):
            if int(value) != value:
                raise ValueError(f"{self.name} no es entero exacto")
            return int(value)
        if isinstance(value, str):
            s = value.strip()
            if s == "":
                return None
            return int(s)
        raise TypeError(f"{self.name} debe ser un entero o convertible a entero")

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, int):
            raise TypeError(f"{self.name} debe ser un entero (int)")
        min_val = self.extra.get("min_value")
        max_val = self.extra.get("max_value")
        if min_val is not None and value < min_val:
            raise ValueError(f"{self.name} debe ser >= {min_val}")
        if max_val is not None and value > max_val:
            raise ValueError(f"{self.name} debe ser <= {max_val}")


class FloatType(BaseField):
    def deserialize(self, value):
        if value is None:
            return None
        if isinstance(value, (float, int)):
            return float(value)
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, str):
            s = value.strip().replace(",", ".")
            if s == "":
                return None
            return float(s)
        raise TypeError(f"{self.name} debe ser numérico o convertible a float")

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, (float, int)):
            raise TypeError(f"{self.name} debe ser numérico (float)")
        min_val = self.extra.get("min_value")
        max_val = self.extra.get("max_value")
        if min_val is not None and value < min_val:
            raise ValueError(f"{self.name} debe ser >= {min_val}")
        if max_val is not None and value > max_val:
            raise ValueError(f"{self.name} debe ser <= {max_val}")


class BooleanType(BaseField):
    def deserialize(self, value):
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int,)):
            if value in (0, 1):
                return bool(value)
            raise ValueError(f"{self.name} debe ser 0/1 si es entero")
        if isinstance(value, str):
            s = _norm(value)
            truthy = {"true", "t", "1", "yes", "y", "on", "si", "sí", "verdadero"}
            falsy  = {"false", "f", "0", "no", "n", "off", "falso"}
            if s in truthy:  return True
            if s in falsy:   return False
        raise TypeError(f"{self.name} debe ser booleano o convertible (true/false, 1/0, sí/no)")

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, bool):
            raise TypeError(f"{self.name} debe ser booleano")


class DateType(BaseField):
    def deserialize(self, value):
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            s = value.strip()
            # ISO: YYYY-MM-DD
            return date.fromisoformat(s)
        raise TypeError(f"{self.name} debe ser fecha o cadena ISO 'YYYY-MM-DD'")

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, date) or isinstance(value, datetime):
            raise TypeError(f"{self.name} debe ser una fecha (datetime.date)")


class DateTimeType(BaseField):
    def deserialize(self, value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, time(0, 0, 0))
        if isinstance(value, (int, float)):
            # Epoch (segundos)
            return datetime.fromtimestamp(value)
        if isinstance(value, str):
            s = value.strip()
            if s.endswith("Z"):   # normaliza 'Z' a '+00:00'
                s = s[:-1] + "+00:00"
            # ISO 8601: '2025-09-04T21:04:54.085654' etc.
            return datetime.fromisoformat(s)
        raise TypeError(f"{self.name} debe ser datetime o cadena ISO 8601")

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, datetime):
            raise TypeError(f"{self.name} debe ser fecha y hora (datetime.datetime)")


class TimeType(BaseField):
    def deserialize(self, value):
        if value is None:
            return None
        if isinstance(value, time):
            return value
        if isinstance(value, datetime):
            return value.time()
        if isinstance(value, str):
            return time.fromisoformat(value.strip())
        raise TypeError(f"{self.name} debe ser hora o cadena 'HH:MM[:SS[.mmmmmm]]'")

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
    def deserialize(self, value):
        if value is None:
            return None
        if isinstance(value, (dict, list, int, float, str, bool)) or value is None:
            # si ya es JSON-serializable, lo dejamos
            return value
        if isinstance(value, (bytes, bytearray)):
            value = value.decode("utf-8")
        if isinstance(value, str):
            return _json.loads(value)
        raise TypeError(f"{self.name} debe ser JSON o cadena JSON")

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        try:
            _json.dumps(value)
        except Exception:
            raise TypeError(f"{self.name} debe ser un valor JSON válido (dict, list, etc.)")


class UUIDType(BaseField):
    def deserialize(self, value):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        if isinstance(value, str):
            return uuid.UUID(value)
        raise TypeError(f"{self.name} debe ser UUID o string representando UUID")

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, uuid.UUID):
            raise TypeError(f"{self.name} debe ser UUID")


class Base64Type(BaseField):
    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, str):
            raise TypeError(f"{self.name} debe ser una cadena base64")
        try:
            base64.b64decode(value, validate=True)
        except Exception:
            raise ValueError(f"{self.name} no contiene una cadena base64 válida")

    def get_decoded(self, value):
        return base64.b64decode(value, validate=True)


class InetType(BaseField):
    def deserialize(self, value):
        if value is None:
            return None
        if isinstance(value, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            return value
        if isinstance(value, str):
            return ipaddress.ip_address(value)
        raise TypeError(f"{self.name} debe ser dirección IP o cadena")

    def validate(self, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name} no puede ser nulo")
            return
        if not isinstance(value, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            raise TypeError(f"{self.name} debe ser IPv4/IPv6")


class EmailType(BaseField):
    def validate(self, value):
        if value is None and not self.nullable:
            raise ValueError(f"{self.name} no puede ser nulo")
        if value is None:
            return
        if not isinstance(value, str):
            raise TypeError(f"{self.name} debe ser una cadena (email)")
        regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(regex, value):
            raise ValueError(f"{self.name} no es un email válido")


class URLType(BaseField):
    def validate(self, value):
        if value is None and not self.nullable:
            raise ValueError(f"{self.name} no puede ser nulo")
        if value is None:
            return
        if not isinstance(value, str):
            raise TypeError(f"{self.name} debe ser una cadena (URL)")
        parsed = urlparse(value)
        if not all([parsed.scheme, parsed.netloc]):
            raise ValueError(f"{self.name} no es una URL válida")


class EnumType(BaseField):
    def validate(self, value):
        allowed = self.extra.get("choices", [])
        if value is None and not self.nullable:
            raise ValueError(f"{self.name} no puede ser nulo")
        if value is None:
            return
        if value not in allowed:
            raise ValueError(f"{self.name} debe estar en {allowed}")


class ListType(BaseField):
    def deserialize(self, value):
        if value is None:
            return None
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # intenta JSON primero
            try:
                parsed = _json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        raise TypeError(f"{self.name} debe ser una lista o cadena JSON de lista")

    def validate(self, value):
        if value is None and not self.nullable:
            raise ValueError(f"{self.name} no puede ser nulo")
        if value is None:
            return
        if not isinstance(value, list):
            raise TypeError(f"{self.name} debe ser una lista")
        subtype = self.extra.get("subtype")
        if subtype:
            for item in value:
                subtype(name=f"{self.name}_item").validate(item)


class MoneyType(BaseField):
    def deserialize(self, value):
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            s = value.strip().replace("€", "").replace(",", ".")
            return Decimal(s)
        raise TypeError(f"{self.name} debe ser Decimal/numérico o cadena")

    def validate(self, value):
        if value is None and not self.nullable:
            raise ValueError(f"{self.name} no puede ser nulo")
        if value is None:
            return
        if not isinstance(value, Decimal):
            raise TypeError(f"{self.name} debe ser Decimal (para dinero)")


class XMLType(BaseField):
    def validate(self, value):
        if value is None and not self.nullable:
            raise ValueError(f"{self.name} no puede ser nulo")
        if value is None:
            return
        if not isinstance(value, str):
            raise TypeError(f"{self.name} debe ser una cadena XML")
        if not value.strip().startswith("<"):
            raise ValueError(f"{self.name} debe parecer XML")


class IntervalType(BaseField):
    def validate(self, value):
        if value is None and not self.nullable:
            raise ValueError(f"{self.name} no puede ser nulo")
        if value is None:
            return
        if not isinstance(value, timedelta):
            raise TypeError(f"{self.name} debe ser un objeto timedelta")


class CidrType(BaseField):
    def deserialize(self, value):
        if value is None:
            return None
        try:
            return ipaddress.ip_network(value, strict=False)
        except Exception:
            raise ValueError(f"{self.name} no es un bloque CIDR válido")

    def validate(self, value):
        if value is None and not self.nullable:
            raise ValueError(f"{self.name} no puede ser nulo")


class MacAddressType(BaseField):
    def validate(self, value):
        if value is None and not self.nullable:
            raise ValueError(f"{self.name} no puede ser nulo")
        if value is None:
            return
        if not isinstance(value, str):
            raise TypeError(f"{self.name} debe ser una cadena (MAC)")
        if not re.match(r"^([0-9A-Fa-f]{2}:){5}([0-9A-Fa-f]{2})$", value):
            raise ValueError(f"{self.name} no es una MAC válida")


class MacAddress8Type(BaseField):
    def validate(self, value):
        if value is None and not self.nullable:
            raise ValueError(f"{self.name} no puede ser nulo")
        if value is None:
            return
        if not isinstance(value, str):
            raise TypeError(f"{self.name} debe ser una cadena (MAC8)")
        if not re.match(r"^([0-9A-Fa-f]{2}:){7}([0-9A-Fa-f]{2})$", value):
            raise ValueError(f"{self.name} no es una MAC de 8 bytes válida")


class BitType(BaseField):
    def validate(self, value):
        if value is None and not self.nullable:
            raise ValueError(f"{self.name} no puede ser nulo")
        if value is None:
            return
        if not isinstance(value, str):
            raise TypeError(f"{self.name} debe ser una cadena de bits")
        if not re.fullmatch(r"[01]+", value):
            raise ValueError(f"{self.name} debe contener solo 0 y 1")


class BitVaryingType(BaseField):
    def validate(self, value):
        BitType.validate(self, value)


class RangeType(BaseField):
    def validate(self, value):
        if value is None and not self.nullable:
            raise ValueError(f"{self.name} no puede ser nulo")
        if value is None:
            return
        if not isinstance(value, tuple) or len(value) != 2:
            raise TypeError(f"{self.name} debe ser una tupla (inicio, fin)")


class PointType(BaseField):
    def deserialize(self, value):
        if value is None:
            return None
        if isinstance(value, tuple) and len(value) == 2:
            x, y = value
            return (float(x), float(y))
        if isinstance(value, str):
            # formato simple "x,y"
            parts = value.split(",")
            if len(parts) == 2:
                return (float(parts[0].strip()), float(parts[1].strip()))
        raise TypeError(f"{self.name} debe ser tupla (x,y) o cadena 'x,y'")

    def validate(self, value):
        if value is None and not self.nullable:
            raise ValueError(f"{self.name} no puede ser nulo")
        if value is None:
            return
        if not (isinstance(value, tuple) and
                len(value) == 2 and
                all(isinstance(v, (int, float)) for v in value)):
            raise TypeError(f"{self.name} debe ser una tupla (x, y)")
