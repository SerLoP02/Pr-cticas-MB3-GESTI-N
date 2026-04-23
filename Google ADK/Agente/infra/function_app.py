import azure.functions as func
import azure.durable_functions as df

from main import main_async

myApp = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@myApp.route(route="mb3_factory_agent")
@myApp.durable_client_input(client_name="client")
async def http_start(
    req: func.HttpRequest, 
    client: df.DurableOrchestrationClient
) -> func.HttpResponse:

    # Hacemos validación de formato
    try:
        payload = req.get_json()
        for key in ["user_input"]:
            if key not in payload:
                return func.HttpResponse(f"Falta la clave '{key}' en el JSON", status_code=400)
    except ValueError:
        return func.HttpResponse("JSON inválido", status_code=400)
    
    # Creamos la instancia de la sesión del cliente que dispara al orquestador
    instance_id = await client.start_new("Orquestador", None, payload) # Enviamos el payload al orquestador como parámetro de entrada
    
    # Devolvemos este json con información útil para comprobar el estado de la app
    return client.create_check_status_response(req, instance_id)

@myApp.orchestration_trigger(context_name="context")
def Orquestador(context: df.DurableOrchestrationContext):

    if not context.is_replaying:
        print("Orquestador iniciado")
    
    user_input = context.get_input().get("user_input")

    # Creamos una lista para ir acumulando los pasos (el customStatus)
    status_history = []

    status_history.append({"step": 1, "message": "Generando respuesta..."})
    context.set_custom_status(status_history)

    user_response = yield context.call_activity("generate_llm_response", user_input)

    return {"llm_response": user_response} # Para ver la respuesta, hay que mandar una petición GET a "statusQueryGetUri" (viene en la respuesta del http_start (POSTMAN por ejemplo))

@myApp.activity_trigger(input_name="user_input")
async def generate_llm_response(user_input: str):
    user_response = await main_async(user_input)
    return user_response

#@myApp.activity_trigger(input_name="user_input")
#async def generate_llm_response(user_input: str):

#    import asyncio
#    await asyncio.sleep(5)
#    user_response = "Adiós"
#    return user_response