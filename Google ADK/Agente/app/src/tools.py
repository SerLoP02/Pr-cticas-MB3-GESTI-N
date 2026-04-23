import requests

def llamar_endopoint_azure(
    url: str, 
    payload: dict
) -> dict | str:
    """
    La función llama a un endpoint o url con los parámetros necesarios.
    Si la respuesta es 2xx, es decir que es correcta (ok) entonces se devuelve le json o texto.
    En caso de que haya algún fallo se devuelve el error.
    """    
    
    try:
        resp = requests.post(url, json=payload, timeout=60)
        status_code = resp.status_code

        if resp.ok:
            try:
                data = resp.json() # Parseamos a JSON
            except ValueError:
                data = resp.text # Si no es JSON, devuelve texto
            print({"ok": True, "status_code": status_code})
            retorno = data
        else:
            print({"ok": False, "status_code": status_code, "error": f"Error HTTP {status_code}: {resp.text}"})
            retorno = {}
        return retorno
    except requests.RequestException as e:
        print({"ok": False, "status_code": None, "error": f"Error de conexión: {e}"})
        return {}
    except requests.Timeout:
        print({"ok":False, "status_code" : None, "error" : "Timeout al llamar a la función"})
        return {}
    

if __name__ == "__main__":
    url = "http://localhost:7071/api/mb3_factory_agent"
    payload = {
        "user_innput": "Hola"
    }
    a = llamar_endopoint_azure(url, payload)
    print(a)