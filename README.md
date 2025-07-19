# BKLibPg

**BKLibPg** es una librería modular escrita en Python que proporciona una capa de abstracción avanzada para trabajar con bases de datos PostgreSQL. Ofrece un sistema de modelos validables con tipado fuerte, gestión dinámica de consultas y un `QueryBuilder` flexible para filtrado y paginación.

---

## 🚀 Características principales

- 📦 **Modelos personalizables** con validación a nivel de aplicación.
- 🧠 **Tipos de datos enriquecidos** (`StringType`, `IntegerType`, `DateType`, `JsonType`, etc.) con metainformación.
- 🛠️ **Gestores de acceso (`Manager`)** extensibles para operaciones CRUD complejas.
- 🔍 **BKPgQueryBuilder** para construir consultas SQL dinámicas con filtros avanzados.
- 🔄 **Conversión automática a modelos Pydantic** para integración con FastAPI.
- ✅ **Validación y documentación** de cada campo según sus metadatos.

---

## 📁 Estructura del proyecto

```
BKLibPg/
├── managers/                # Managers CRUD y de consulta especializada
├── model                    # Crea objetos python que representen registros de la base de datos
├── data_types               # Objetos que representan tipos de datos
├── query_builder            # Crear querys con filtros y operadores SQL
├── connection_database      # Crea conexiones y pool de coneciones para realizar peticiones a la base de datos
└── config                   # Configuraciones base aplicadas a los demas mnodulos
```

---

## 🧩 Ejemplo de uso

### 1. Definir un modelo personalizado

```python
from bklibpg.core import Model
from bklibpg.models import StringType, IntegerType

class Usuario(Model):
    id = IntegerType(db_name='id_usuario', nullable=False, doc="ID del usuario")
    nombre = StringType(nullable=False)
    email = StringType(nullable=True)
```

### 2. Validar datos

```python
usuario = Usuario.from_dict({
    "id": 123,
    "nombre": "Juan",
    "email": None
})
usuario.validate()
```

### 3. Manager con filtros dinámicos

```python
from bklibpg.managers import BasePgManager

class ManagerUsuarios(BasePgManager):
    def get_sql_select(self):
        return "SELECT * FROM usuarios"

manager = ManagerUsuarios()
filters = [{"field": "nombre", "op": "ILIKE", "value": "%juan%"}]
resultado = manager.getlist(filters=filters)
```

---

## 🔧 Tipos de datos disponibles

- `StringType`
- `IntegerType`
- `FloatType`
- `BooleanType`
- `DateType`
- `DateTimeType`
- `JsonType`
- `ArrayType`
- `CustomType` (definido por el usuario)

Cada tipo soporta:

- `db_name`: nombre en la base de datos
- `nullable`: permite `None`
- `default`: valor por defecto
- `doc`: descripción

---

## 🔗 Integración con FastAPI

Los modelos pueden convertirse en esquemas Pydantic automáticamente:

```python
UsuarioPydantic = Usuario.to_pydantic_model()
```

### Ejemplo en una ruta de FastAPI

```python
from fastapi import FastAPI
from bklibpg.core import Model
from bklibpg.models import StringType

class Producto(Model):
    nombre = StringType(nullable=False)

ProductoSchema = Producto.to_pydantic_model()

app = FastAPI()

@app.post("/productos")
async def crear_producto(producto: ProductoSchema):
    p = Producto.from_pydantic(producto)
    p.validate()
    return {"status": "ok", "producto": p.to_dict()}
```

---

## ⚙️ Requisitos

- Python 3.9+
- [psycopg](https://www.psycopg.org/) o `psycopg2`
- (Opcional) FastAPI para uso web

---

## 🧪 Pruebas

Para ejecutar los tests:

```bash
pytest tests/
```

---

## 📦 Instalación como paquete

1. Clona el repositorio:

```bash
git clone https://github.com/tuusuario/BKLibPg.git
cd BKLibPg
```

2. Instala localmente:

```bash
pip install -e .
```

3. O crea un paquete con `pyproject.toml`:

```toml
[project]
name = "bklibpg"
version = "0.1.0"
description = "Librería avanzada para PostgreSQL con validación de modelos"
authors = [{ name = "Tu Nombre", email = "tu@email.com" }]
dependencies = ["psycopg[binary]>=3.1", "pydantic>=2", "fastapi"]

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
```

---

## 📌 Estado del proyecto

> BKLibPg está en desarrollo activo. Aún no se recomienda para producción sin pruebas específicas en tu entorno.

---
