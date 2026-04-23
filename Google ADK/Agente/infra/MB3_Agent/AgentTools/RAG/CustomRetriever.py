import psycopg2
from typing import List, Tuple, Dict
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.embeddings import Embeddings

class CustomRetriever(BaseRetriever):
    """
    Este Retriever personalizado devuelve, de cada chunk recuperado por la distancia del coseno, 
    los vecinos a este chunk y el header padre del que viene

    Args:
        coleccion_objetivo: Nombre de la colección que contiene los chunks
        embeddings: El modelo de embedding que usaremos para vectorizar la query
        connection: Las credenciales para acceder a la base de datos PostgreSQL
        k: El número de documentos que recuperaremos por la métrica cosine_distance
        neighbours: Cuantos vecinos (a los lados) queremos del resultado principal
    """
    coleccion_objetivo: str
    embeddings: Embeddings
    connection: Dict
    k: int = 3
    neighbours: int = 1 

    def _run_query(
        self,
        query: str,
        include_score: bool
    ) -> List[Document]:
        
        # Convertimos la query a embedding mediante el modelo de embedding
        query_vector = self.embeddings.embed_query(query) # Vectorizamos la query
        query_vector = str(query_vector) # PGVector espera que lo que le pasemos sea string

        # Definimos la consulta SQL
        sql_query = f"""
        
        -- CREAMOS UNA TABLA AUXILIAR QUE ME FILTRE LA 'TABLA' QUE QUEREMOS
        WITH coleccion_objetivo AS (
            select 
                uuid
            from langchain_pg_collection
            where name = %s
        ),
        -- CREAMOS UNA TABLA AUXILIAR A PARTIR DE LA METADATA. ESTA TABLA CONTENDRÁ LOS CHUNKS MÁS SIMILARES
        top_chunks AS (
            SELECT
                d.file_name,
                d.chunk_id,
                d.headers
            FROM langchain_pg_embedding AS d
            INNER JOIN coleccion_objetivo AS co
                ON d.collection_id = co.uuid
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        )
        SELECT DISTINCT 
            d.id AS id,
            d.document AS page_content,
            d.cmetadata AS metadata
            {", d.embedding <=> %s::vector AS score" if include_score else ""}
        FROM langchain_pg_embedding d
        INNER JOIN coleccion_objetivo AS co
            ON d.collection_id = co.uuid
        INNER JOIN top_chunks tc 
            ON d.file_name = tc.file_name
        WHERE 
                                    -- CONDICIÓN DE PADRE --
            d.headers = (tc.headers - (-1)) and jsonb_array_length(tc.headers) > 1 --  Si jsonb_array_length(tc.headers) = 1, entonces no tiene padre; no perdemos el tiempo buscando quién es el padre
            OR
                                    -- CONDICIÓN DE VECINO --
            d.chunk_id between tc.chunk_id - %s AND tc.chunk_id + %s
        ORDER BY 
            {"score" if include_score else "d.id"};
        """

        params = (
            self.coleccion_objetivo,
            query_vector,
            self.k,
            *([query_vector] if include_score else []),
            self.neighbours,
            self.neighbours
        )
        try:
            # Nos conectamos a la base de datos
            with psycopg2.connect(**self.connection) as conn:
                # Nos conectamos para hacer la consulta a la base de datos
                with conn.cursor() as cur:
                    cur.execute(sql_query, params)
                    # Recuperamos todos los resultados. El resultado es una lista de tuplas donde
                    # cada elemento de la lista es una fila, y cada elemento de la tupla es una columna
                    return cur.fetchall()
        except Exception as e:
            print(f"Error al ejectura la consulta: {e}")
            return []



    # Langchain solo nos exige que cualquier retriever tenga el método _get_relevant_documents y que devuelva una lista de Documents
    def _get_relevant_documents(
        self, 
        query: str, 
        *, 
        run_manager=None
    ) -> List[Document]:

        docs = []
        results = self._run_query(query, include_score=False)
        for fila in results:
            id = fila[0]
            page_content = fila[1]
            metadata = fila[2]
            doc = Document(page_content, id=id, metadata=metadata)
            docs.append(doc)
        return docs
    
    def _get_relevant_documents_with_score(
        self, 
        query: str, 
        *, 
        run_manager=None
    ) -> List[Tuple[Document, float]]:
        
        docs = []
        results = self._run_query(query, include_score = True)
        for fila in results:
            id = fila[0]
            page_content = fila[1]
            metadata = fila[2]
            score = fila[3]
            doc = Document(page_content, id=id, metadata=metadata)
            docs.append(tuple([doc, score]))
        return docs