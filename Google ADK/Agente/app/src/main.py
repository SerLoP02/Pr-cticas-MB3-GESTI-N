from src.tools import llamar_endopoint_azure
import streamlit as st
import requests

def src_main(user_input: str, render_chat: callable) -> str:
    """
    Envía el prompt del usuario a la Azure Durable Function y va añadiendo
    mensajes del asistente al historial. Cada mensaje queda en su propia burbuja.

    user_input (str): Mensaje que el usuario escribirá en Streamlit
    render_chat (callable): Función para repintar el chat en un placeholder estable.
    """

    url = "http://localhost:7071/api/mb3_factory_agent"
    payload = {
        "user_input": user_input
    } 

    respuesta = llamar_endopoint_azure(url, payload)
    status_url = respuesta.get("statusQueryGetUri")

    if not status_url:
        msg = "❌ No se ha podido obtener la URL de estado de la orquestación."
        st.session_state.messages.append({"role": "assistant", "content": msg})
        render_chat()
        return msg
    
    # Con esto nos aseguramos que el mensaje no se muestre dos veces
    step_control = -1

    # Creamos el espacio temporal donde se mostrarán los mensajes del customStatus
    status_placeholder = st.empty()

    while True:
        sresp = requests.get(status_url)
        status = sresp.json()

        runtime = status.get("runtimeStatus")
        custom = status.get("customStatus") or [] # Status personalizados para que mientras runtime sea "Running" mostremos al usuario algún mensaje y 
                                                  # que sirva para hacerle saber que se necesita tiempo
                                                  
        #print("status -> ", status)
        #print()
        #print("runtime -> ", runtime)
        #print()
        #print("custom -> ", custom)

        # customStatus a veces puede venir como dict; lo normalizamos a lista
        if isinstance(custom, dict):
            custom = [custom]

        for fase in custom:
            step = fase.get("step")
            if step is None:
                continue

            if step > step_control:
                msg = fase.get("message", "")
                if msg:
                    with status_placeholder.chat_message("assistant"):
                        st.markdown(f"⏳ *{msg}*")
                step_control = step

        if runtime == "Completed":
            # Borramos el mensaje temporal generado por el customStatus
            status_placeholder.empty()

            output_obj = status.get("output") or {}
            output = output_obj.get("llm_response", "")

            if output:
                st.session_state.messages.append({"role": "assistant", "content": output})
                render_chat()
            break

        elif runtime in ("Failed", "Terminated"):
            # Borramos el mensaje temporal generado por el customStatus
            status_placeholder.empty()

            msg = "Estamos teniendo problemas."
            st.session_state.messages.append({"role": "assistant", "content": msg})
            render_chat()
            break

    return str(status)        


if __name__ == "__main__":
    print(src_main("Hola"))       