from flask import Flask, jsonify, request
from datetime import datetime
from model.MensajeSMS import MensajeSMS
from model.Alerta import Alerta
from model.Analisis import Analisis
import json
import requests  # Importa la biblioteca requests para realizar solicitudes HTTP
import re

app = Flask(__name__)
application = app

@app.route('/')
def hello_world():
    return 'hello, world!'

@app.route("/ping")
def ping():
    return jsonify({"message": "pong"})

@app.route("/consultar-modelo", methods=['POST'])
def consultar_modelo():
    # Obtener el objeto JSON enviado en el cuerpo de la solicitud
    data = request.get_json()
    mensaje = data.get('mensaje', '')

    # Enviar el mensaje al microservicio de gpt
    url_microservicio_gpt = "https://smishguard-chatgpt-ms.onrender.com/consultar-modelo-gpt"
    headers_gpt = {'Content-Type': 'application/json'}
    payload_gpt = {"mensaje": mensaje}
    
    # Realizar la solicitud POST al microservicio
    try:
        response_microservicio_gpt = requests.post(url_microservicio_gpt, headers=headers_gpt, json=payload_gpt)
        response_microservicio_gpt.raise_for_status()  # Lanza una excepción si la solicitud no fue exitosa
        response_json_microservicio_gpt = response_microservicio_gpt.json()
    except requests.exceptions.RequestException as e:
        response_json_microservicio_gpt = "Error al contactar con el microservicio"

    # Enviar el mensaje al microservicio de detección de spam
    url_microservicio = "https://microservicio-modelo-ml-spam.onrender.com/predict"
    headers = {'Content-Type': 'application/json'}
    payload = {"text": mensaje}
    
    # Realizar la solicitud POST al microservicio
    try:
        response_microservicio = requests.post(url_microservicio, headers=headers, json=payload)
        response_microservicio.raise_for_status()  # Lanza una excepción si la solicitud no fue exitosa
        response_json_microservicio = response_microservicio.json()
    except requests.exceptions.RequestException as e:
        response_json_microservicio = "Error al contactar con el microservicio"

    
    urls = re.findall(r'(?:https?://)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?', mensaje)
    if len(urls) > 0:
        # Enviar el mensaje al microservicio de detección urls de VT
        url_microservicio_vt = "https://microservicio-virustotal.onrender.com/analyze-url"
        headers_vt = {'Content-Type': 'application/json'}
        payload_vt = {"url": urls[0]}

            # Realizar la solicitud POST al microservicio VT
        try:
            response_microservicio_vt = requests.post(url_microservicio_vt, headers=headers_vt, json=payload_vt)
            response_microservicio_vt.raise_for_status()  # Lanza una excepción si la solicitud no fue exitosa
            response_json_microservicio_vt = response_microservicio_vt.json()
            response_json_microservicio_vt['url'] = urls[0] if len(urls) > 0 else "No se encontraron URLs en el mensaje"
        except requests.exceptions.RequestException as e:
            response_json_microservicio_vt = "Error al contactar con el microservicio"
    else:
        response_json_microservicio_vt = {"Error No se encontraron URLs en el mensaje"}
    
    # Combinar las respuestas de OpenAI y del microservicio
    resultado_final = {
        "analisis_openai": response_json_microservicio_gpt,
        "analisis_microservicio": response_json_microservicio,  # Contendrá solo {"prediction": "spam"} o {"prediction": "ham"}
        "analisis_microservicio_vt": response_json_microservicio_vt
    }

    # Retornar el objeto JSON combinado en la respuesta
    return jsonify(resultado_final)

@app.route("/publicar-tweet")
def publicar_tweet():
    tweetPrueba = Alerta(1, "123 Tweet probando", datetime.now())
    return jsonify({"Publicacion": json.dumps(tweetPrueba.to_dict())})

@app.route("/base-datos")
def base_datos():
    return jsonify({"message": "pong"})

if __name__ == '__main__':
    app.run(debug = True)
