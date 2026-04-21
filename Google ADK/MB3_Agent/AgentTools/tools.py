from MB3_Agent.AgentTools.utils import bucket_reader, decimal_default, clean_sql_from_model_output, validate_readonly_sql, PostgresDB
from MB3_Agent.AgentTools import tools_prompts
from config import MAX_ROWS, CREDS_DB_PATH, CLIENT_SCHEMA_PATH
import uuid


# RAG
from MB3_Agent.AgentTools.RAG.CustomRetriever import CustomRetriever
from MB3_Agent.AgentTools.RAG.Embeddings import get_query_embedding
from MB3_Agent.AgentTools.RAG.prompt import build_system_template_RAG


class ClientTools:
    def __init__(self, client_id: str): 
        # Configuración específica por cliente
        self.client_id = client_id
        self.max_rows = MAX_ROWS
        self.creds_db_path = CREDS_DB_PATH.format(client_id=client_id)
        self.client_schema_path = CLIENT_SCHEMA_PATH.format(client_id=client_id)
        self.states = {}


    ##################################################################################
    ##################################################################################

    def get_sql_metadata(self) -> dict:
        """Utiliza esta herramienta cuando necesites el esquema de la base de datos del cliente o generar una consulta SQL.
        - Proporciona las instrucciones necesarias para que tu mismo puedas generar consultas SQL para PostgresSQL.
        - Proporciona el esquema de la base de datos del cliente.

        Returns:
            dict: Diccionario con las instrucciones para generar la consulta SQL y el esquema de base de datos del cliente.
        """
        try:

            # Leemos el esquema.
            client_schema = bucket_reader(self.client_schema_path)
            # Prompt con instrucciones para generar la consulta SQL.
            instructions = tools_prompts.SQL_PROMPT

            # Respuesta para el modelo y logs
            response =  {"sql_instructions": instructions, "client_schema": client_schema}
        
        except Exception as e:
            # Respuesta para el modelo y logs
            response = {"error": "Error al recuperar esquema del cliente o instrucciones SQL. Finaliza con una respuesta adecuada para el usuario."}
        
            print("RESPONSE 'get_sql_metadata'\n", str(e))
            print("="*50)
        return response
    
    ##################################################################################
    ##################################################################################

    def ddbb_consultor(self, sql_query: str) -> dict:
        """Ejecuta una consulta SQL para extraer datos de la base de datos de un cliente.

        Args:
           sql_query: query en lenguaje PostgreSQL.


        Returns:
           dict: Diccionario con el ID de los datos devueltos.
        """
        try:
            #LIMPIEZA DE QUERY
            sql_query = clean_sql_from_model_output(sql_query)
            sql_query = validate_readonly_sql(sql_query)

            #LECTURA DE CREDENCIALES
            creds = bucket_reader(self.creds_db_path)

            #CONSULTA A BASE DE DATOS
            db = PostgresDB(creds)
            rows, truncated = db.ejecutar_query(sql_query, max_rows= self.max_rows)
            db.cerrar_conexion()

            # TRANSFORMAR LOS DATOS A JSON SERIALIZABLE PARA QUE PUEDA LEERLO LA FUNCIÓN DE AZURE
            rows_clean = decimal_default(rows)

            #GENERAR ID ALEATORIO
            data_id = str(uuid.uuid4())
            self.states[data_id] = rows_clean


            # Logueamos la salida y el tiempo de ejecución de la herramienta. En este caso, también es interesante loguear si la consulta ha sido truncada por el límite de filas establecidas, para tener esa información en los logs.
            response = {"data_id": data_id}

        except Exception as e:
            # Respuesta para el modelo y logs.
            response = {"error": f"Error: {e}. Error de consulta SQL: Corrige la consulta y vuelve a intentarlo. Otros errores:  Responde al usuario educadamente que no se ha podido realizar la consulta y que disculpe las molestias."}

            print("RESPONSE 'ddbb_consultor'\n", str(e))
            print("="*50)
        return response
        
    ##################################################################################
    ##################################################################################

    def data_response(self, data_id: str) -> dict:
        """Herramienta para respuestas relacionadas con consultas de datos, respuestas estructuradas tipo informe. 
        Proporciona reglas e instrucciones para generar la respuesta que hay que proporcionar al usuario a partir de los datos extraídos de la base de datos.

        Args:
            data_id (str): ID de los datos para leerlos y retornarlos.

        Returns:
            dict: instrucciones con el formato necesario para generar la respuesta."""
        try:
            # Recuperamos las instrucciones del cliente
            response_instructions = bucket_reader(f"clientes/prompts/{self.client_id}/response_instructions.txt")

            # Respuesta para el modelo y logs
            response = {"data_response_instructions": response_instructions, "data": self.states.get(data_id, [])}
        

        except Exception as e:
            # Respuesta para el modelo y logs
            response = {"error": "Error al obtener las instrucciones para generar la respuesta al usuario. Responde al usuario con una respuesta adecuada a pesar de no tener las instrucciones."}
            print("RESPONSE 'data_response'\n", str(e))
            print("="*50)
        return response
    
    ##################################################################################
    ##################################################################################

    def small_talker(self) -> dict:
        """
        Herramienta de mediación y soporte conversacional para respuestas no estructuradas.
        Proporciona reglas e instrucciones para generar la respuesta. 
        DEBE usarse en los siguientes escenarios:
        1. Cuando el usuario hace consultas generales fuera del dominio técnico del agente.
        2. Dudas sobre las capacidades del asistente ("¿Qué puedes hacer?", "¿Cómo me ayudas?").
        3. Aclaraciones sobre la conversación actual o el contexto previo ("¿Qué dije antes?", "¿A qué te refieres con X?").
        4. Confirmación de datos ya mencionados por el usuario que no requieren nueva consulta a base de datos.

        Returns:
            dict: Instrucciones dinámicas de estilo y comportamiento para la respuesta.
        """
        try:
            # Prompt con instrucciones para generar la consulta SQL.
            instructions = tools_prompts.SMALL_TALK_PROMPT

            # Respuesta para el modelo y logs
            response =  {"small_talk_instructions": instructions}
            
        except Exception as e:
            # Respuesta para el modelo y logs
            response = {"error": "Error al obtener las instrucciones para generar la respuesta al usuario. Responde al usuario con una respuesta adecuada a pesar de no tener las instrucciones."}
        
        return response

    ##################################################################################
    ##################################################################################

    def schema_explainer(self) -> dict:
        """Herramienta para generar respuesta relacionadas con esquemas de bases de datos. Proporciona reglas e instrucciones para generar la respuesta que hay que proporcionar al usuario.

        Returns:
            str: instrucciones con el formato necesario para generar la respuesta.
        """
        try:
            # Respuesta para el modelo y logs
            instructions = tools_prompts.SCHEMA_PROMPT
            response = {"schema_instructions": instructions}

        except Exception as e:
            # Respuesta para el modelo y logs
            response = {"error": "Error al obtener las instrucciones para generar la respuesta al usuario. Responde al usuario con una respuesta adecuada a pesar de no tener las instrucciones."}
            print("RESPONSE 'schema_explainer'\n", str(e))
            print("="*50)
        return response

    ##################################################################################
    ##################################################################################

    def doc_retrieval(self,  name: str, query: str) -> dict:
        """Herramienta para consulta en tablas vectoriales. Proporciona reglas e instrucciones para generar la respuesta que hay que proporcionar al usuario a partir de los chunks recuperados de la base de datos vectorial.
        
        Args:
            name (str): nombre de la tabla que contiene los chunks para ser recuperados. Este argumento se encuentra en el esquema de la base de datos del cliente
            query (str): Resumen usando palabras claves de:
                1. Input del usuario actual.
                2. Información relevante del historial de conversación con respecto al último input del usuario (no añadir cuando la información es irrelevante)
            
        Returns:
            dict: Un diccionario con las intrucciones para formar la respuesta y los chunks recuperados"""
        try:
            connection = bucket_reader(self.creds_db_path)
            connection["database"] = connection["db_name"]
            del connection["db_name"]
            # Respuesta para el modelo y logs
            retriever = CustomRetriever(
                coleccion_objetivo = name,
                embeddings = get_query_embedding(),
                connection = connection,
                k = 5,
                neighbours = 3
            )
            retrieved_docs = retriever.invoke(query)
            context = ("\n\n" + "-"*50+"\n\n").join([doc.page_content for doc in retrieved_docs])
            instrucciones = build_system_template_RAG(context)
            response = {"response_instructions": instrucciones}
        except Exception as e:
            # Respuesta para el modelo y logs
            response = {"error": "Error al recuperar los documentos. Responde al usuario con una respuesta adecuada a pesar de no tener los documentos para responder a su pregunta."}

        return response

    ##################################################################################
    ##################################################################################
    