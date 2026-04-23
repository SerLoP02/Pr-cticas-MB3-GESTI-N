import streamlit as st
from src.main import src_main

st.set_page_config(page_title="Factoría Agentes", page_icon="🚀", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Un único "lienzo" para el chat: evitamos duplicados / gris por elementos stale
chat_placeholder = st.empty()

def render_chat():
    """Pinta todo el historial en un único lugar estable."""
    with chat_placeholder.container():
        for m in st.session_state.messages:
            with st.chat_message(m["role"], width="content"):
                st.markdown(m["content"])

# Pintamos el historial al cargar
render_chat()

# Barra de escritura
prompt = st.chat_input("¿En qué te puedo ayudar?")

if prompt:
    # Guardamos mensaje de usuario + repintamos
    st.session_state.messages.append({"role": "user", "content": prompt})
    render_chat()

    # Ejecutamos backend y vamos repintando según llegan mensajes del asistente
    src_main(prompt, render_chat)
    