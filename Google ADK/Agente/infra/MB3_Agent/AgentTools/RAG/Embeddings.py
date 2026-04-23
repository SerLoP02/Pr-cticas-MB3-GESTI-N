from langchain_google_genai import GoogleGenerativeAIEmbeddings
from config import GEMINI_API_KEY

def get_query_embedding():
    query_embedding = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001", 
        google_api_key = GEMINI_API_KEY,
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=1024
    ) 
    return query_embedding