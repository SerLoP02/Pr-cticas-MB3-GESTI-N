import os
from dotenv import load_dotenv

load_dotenv()

# LLM RESPONSE CONFIG
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY3")
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
LLM_LOGS_FILE = "llm_response_logs.jsonl"
#LLM_MODEL = "gemini-3.1-flash-lite-preview"
LLM_MODEL = "gemini-3.1-flash-lite"

# ORQUESTADOR CONFIG
ORQUESTADOR_LOGS_FILE = "orquestador_logs.jsonl"

# TOOLS CONFIG
MAX_ROWS = int(os.getenv("DB_MAX_ROWS", "500"))

# VERSION
FACTORY_VERSION = "1.01"

# BBDD CONFIG
FACTORY_CREDS_DB_PATH = "factoria/credentials/postgres.json"
FROM_TABLE_LOGS = "pro_data.t_factory_logs"
CREDS_DB_PATH = "clientes/credentials/{client_id}/postgres.json"
CLIENT_SCHEMA_PATH = "clientes/schemas/{client_id}.json"