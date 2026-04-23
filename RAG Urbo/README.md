Fecha aproximada de la creación del RAG -> 01/03/2026

# Documentos empleados para el RAG
Se han usado los siguientes documentos:
1. urbo-main/docs
    - Todos los .md de la carpeta *widgets*
    - Todos los .md de la carpeta *troubleshooting*
    - Los archivos *config.md*, *custom-design-conf.md*, *datasources.md*, *operators.md*, *reports.md*, *user_defaults.md*, *user_navigation.md*
2. urbo-deployer-master
    - El archivo *README.md*
    - Todos los .md de la carpeta *doc*

# Funcionamiento
Se debe crear un .env con la siguiente estructura:
```
GEMINI_API_KEY1=...
GEMINI_API_KEY2=...
...
CONNECTION_STRING=postgresql+psycopg://usuario:contraseña@host:puerto/nombre_base_datos
```

Dentro de la carpeta *definitivo*, se debe crear un archivo *database.ini* con la siguiente estructura:
```
[postgresql]
host=...
port=...
database=...
user=...
password=...
```

Dentro de la carpeta *definitivo*, se debe crear una carpeta *documentos* con los documentos a subir. Esta carpeta permite archivos .md y carpetas con únicamente archivos .md

## *subida_documentos.ipynb*
En la sección **Añadimos los Chunks a la Base de Datos** hay una parte que dice:
```python
# Preparamos los datos
ids = [str(i) for i in range(1, len(chunked_documents) + 1)]
#ids = [str(i) for i in range(815, 815 + len(chunked_documents))]
...
```
Si es la primera vez que se van a subir los documentos, se debe dejar como está; si ya se han subido documentos anteriormente, se debe comentar la primera línea y descomentar la segunda, cambiando *815* por el documento del que se quiere comenzar

**IMPORTANTE**: 
- Hay que modificar las tablas que crea por defecto LangChain a 
    ```sql
    ALTER TABLE langchain_pg_embedding
        ADD column file_name TEXT 
            GENERATED ALWAYS AS (cmetadata ->> 'file_name') stored,
        ADD column chunk_id INT 
            GENERATED ALWAYS AS ((cmetadata ->> 'chunk_id')::INT) stored,
        ADD column headers jsonb 
            GENERATED ALWAYS AS (cmetadata -> 'headers') stored;
    ```
- Hay que asegurarse **antes** de subir los documentos que la columna   *id* de la tabla *langchain_pg_embedding* sea de tipo *VARCHAR*. Si es la primera vez que se suben documentos, langchain creará las tablas por defecto y la columna será de tipo *VARCHAR*
    ```sql
    ALTER TABLE langchain_pg_embedding
        ALTER column id TYPE VARCHAR
            USING id::VARCHAR;
    ```
- Una vez que se suben los documentos, para que la recuperación funcione correctamente hay que cambiar la columna *id* a entero
    ```sql
    ALTER TABLE langchain_pg_embedding
        ALTER column id TYPE INT
            USING id::INT;
    ```

## *recuperacion_documentos.ipynb*
Simplemente ejecutar este archivo