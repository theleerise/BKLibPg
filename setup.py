from setuptools import setup, find_packages

# Lee el contenido del README.md para la descripción larga
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="BKLibPg",  # Nombre del paquete
    version="1.0.1",  # Versión incrementada para reflejar las nuevas funcionalidades
    author="Elieser Castro",
    author_email="bkelidireccion@gmail.com",
    description=(
        "Una librería que utiliza psycopg y otras dependencias "
        "para generar managers y models que permiten consultar bases de datos Postgresql."
    ),
    long_description=long_description,  # Descripción larga desde README.md
    long_description_content_type="text/markdown",
    url="https://github.com/theleerise/BKLibPg.git",
    license="Personal Use Only",
    classifiers=[
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries",
    ],
    packages=find_packages(),  # Encuentra todos los subpaquetes automáticamente
    python_requires=">=3.10",  # Versión mínima de Python
    install_requires=[
        "psycopg >= 3.2.9",
        "psycopg-pool >= 3.2.6",
        "pydantic >= 2.11.7",
    ],
    include_package_data=True,  # Incluye archivos adicionales en MANIFEST.in
    project_urls={
        "Source": "https://github.com/theleerise/BKLibPg.git",
        "Bug Tracker": "https://github.com/theleerise/BKLibPg/issues",
    },
)
