from pathlib import Path
from sqlalchemy import create_engine, text, insert, Table, MetaData
from google.genai import types
from sqlalchemy.engine import URL
import re
import json
import decimal
from datetime import date, datetime
import uuid
from config import CREDS_DB_PATH, FACTORY_CREDS_DB_PATH 


def bucket_reader(direccion, bucket = Path(__file__).resolve().parents[3] / "bucket"):
    #Herramienta que sirve para leer archivos json del bucket.
    path = Path(bucket / direccion)
    
    if path.suffix == '.json' :
        with path.open("r", encoding = "utf-8") as f:
            data = json.load(f)
    if path.suffix == '.txt':
        data = path.read_text(encoding='utf-8')

    return data

def clean_sql_from_model_output(raw_text):
    """
    Limpia el output de Gemini por si viene envuelto en ```sql ... ``` u otros formatos.
    """
    if not raw_text:
        return ""

    text = raw_text.strip()

    # Quitar fences de código tipo ```sql ... ``` o ``` ...
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            # quitar primera línea (```sql o ```)
            lines = lines[1:]
        # quitar última línea ``` si aparece
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    return text

_DISALLOWED_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|VACUUM|ANALYZE)\b",
    re.IGNORECASE,
)

def validate_readonly_sql(sql_query: str) -> str:
    if not sql_query or not sql_query.strip():
        raise ValueError("La query SQL está vacía")

    q = sql_query.strip()

    if _DISALLOWED_SQL.search(q):
        raise ValueError("La query contiene operaciones no permitidas")

    return q


### CLASE DE POSTGRES

class PostgresDB:
    def __init__(self, credentials: dict):
        self.engine = None
        self.credentials = credentials or {}
        self._create_engine()

    def _create_engine(self):
        url = URL.create(
            drivername="postgresql+psycopg2",
            username=self.credentials.get("user"),
            password=self.credentials.get("password"),
            host=self.credentials.get("host"),
            port=int(self.credentials.get("port", 5432)),
            database=self.credentials.get("db_name"),
            query={
                **({"sslmode": self.credentials["sslmode"]} if self.credentials.get("sslmode") else {}),
                "application_name": "azurefunc-ddbb_consultor",
            },
        )
        self.engine = create_engine(url, pool_pre_ping=True)

    def ejecutar_query(self, query: str, params: dict = None, max_rows: int = 500):
        rows = []
        truncated = False
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            while True:
                batch = result.fetchmany(size=200)
                if not batch:
                    break
                for row in batch:
                    rows.append(dict(row._mapping))
                    if len(rows) >= max_rows:
                        truncated = True
                        break
                if truncated:
                    break
        return rows, truncated

    def insertar_datos(self, from_table: str, data: list):
        # 'data' es la lista de diccionarios obtenida del csv.DictReader
        metadata = MetaData()
        table_name = from_table.split(".")[1]
        schema = from_table.split(".")[0]  # Extraemos el nombre del esquema
        # Reflejamos la tabla para que SQLAlchemy sepa su estructura
        tabla = Table(table_name, metadata, autoload_with=self.engine, schema = schema)
        
        with self.engine.begin() as conn: # .begin() hace commit automático al final
            conn.execute(insert(tabla), data)

    def cerrar_conexion(self):
        if self.engine:
            self.engine.dispose()


# Helper para manejar los Decimals
def decimal_default(data):
    def transform(obj):
        # 1. Manejar decimales
        if isinstance(obj, decimal.Decimal):
            return float(obj) 
        
        # 2. Manejar fechas y horas
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        
        # 3. Manejar UUIDs
        if isinstance(obj, uuid.UUID):
            return str(obj) 
        # devuelve un string para que la función no rompa.
        try:
            return str(obj)
        except:
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
    
    # 1. Serializamos a texto usando el helper para los decimales
    data_string = json.dumps(data, default = transform)
    
    # 2. Deserializamos de nuevo a diccionario estándar
    resultado_limpio = json.loads(data_string)

    return resultado_limpio


#############
# Función para formatear la respuesta del LLM.
##############

def format_llm_response(response):
    # Extraemos la información relevante de la respuesta del modelo
    metadata = response.usage_metadata
    candidate = response.candidates[0]

    # Tokens usados
    p_tokens = metadata.prompt_token_count or 0
    r_tokens = metadata.candidates_token_count or 0
    t_tokens = metadata.thoughts_token_count or 0
    total_tokens = metadata.total_token_count or 0

    # Ahora verificamos si obtuvimos algo
    respuesta_final = response.text
    price = (p_tokens * 0.3 / 1e6) + ((r_tokens + t_tokens) * 2.5 / 1e6) # Coste en euros
    finish_reason = candidate.finish_reason
    # Preparamos el log completo con toda la información relevante para registrar en Google Sheets
    payload = {"state" : "success", "tool": "llm_response", "tool_phase": "end", "output": respuesta_final, "tokens": total_tokens, "price": price}
    
    return payload, respuesta_final


#############
# Función para generar el content que pasaremos al LLM leyendo en la memoria.
##############

def read_memory_content(user_input : str, client_id :str) -> list:
    """
    Lee la memoria relacionada con el input del usuario desde la base de datos y construye el historial de contenidos para pasárselo al modelo junto con el input del usuario.
    Args:
        user_input: input del usuario que se le pasará al modelo para generar la respuesta.
        client_id: ID del cliente para filtrar la memoria.
    Returns:        
        list: Lista de contenidos con la memoria previa y el input del usuario para pasárselo al modelo.
    """

    # Conectamos con la base de datos
    db = PostgresDB(bucket_reader(FACTORY_CREDS_DB_PATH))
    sql_query = f"select role, text from pro_data.v_factory_memory where client_id = '{client_id}'"

    # Leemos la memoria relacionada con el input del usuario
    rows, truncated = db.ejecutar_query(sql_query)
    db.cerrar_conexion()

    # Construimos el historial previo con la memoria de la base de datos
    history_contents = [types.Content(role=row['role'], parts=[types.Part.from_text(text = row['text'])]) for row in rows]

    # Añadimos el input del usuario al final del historial para que el modelo lo procese teniendo en cuenta ese contexto previo
    history_contents.append(types.Content(role="user", parts=[types.Part.from_text(text = user_input)]))

    return history_contents


from google.genai.types import Content
def my_filter(contents: list[Content]):

    last_user_text_idx = -1
    # Recorremos desde el final hacia el principio
    for rev_i, content in enumerate(reversed(contents)):
        is_user = getattr(content, "role", "") == "user"
        
        has_text = any(getattr(part, "text", None) for part in content.parts)
        # Las function_responses tienen role = user
        has_function_response = any(getattr(part, "function_response", None) for part in content.parts)
        
        if is_user and has_text and not has_function_response:
            last_user_text_idx = len(contents) - 1 - rev_i
            break
    
    quitamos_tool_messages = contents[:last_user_text_idx]
    no_quitamos_tool_messages = contents[last_user_text_idx:]

    contents = []
    for content in quitamos_tool_messages:
        has_tool_usage = any(
            getattr(part, "function_call", None) or getattr(part, "function_response", None)
            for part in content.parts
        )

        if not has_tool_usage:
            contents.append(content)
    return contents + no_quitamos_tool_messages
