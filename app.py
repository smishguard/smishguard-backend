from flask import Flask, jsonify, request
from datetime import datetime
from model.MensajeSMS import MensajeSMS
from model.Alerta import Alerta
from model.Analisis import Analisis
import json
import requests  # Importa la biblioteca requests para realizar solicitudes HTTP
import re
import aiohttp  # Para hacer las solicitudes HTTP de manera asíncrona
import asyncio  # Para manejar las tareas asíncronas

app = Flask(__name__)
application = app

@app.route('/')
def hello_world():
    return 'hello, world!'

@app.route("/ping")
def ping():
    return jsonify({"message": "pong"})

@app.route("/consultar-modelo", methods=['POST'])
async def consultar_modelo():
    data = request.get_json()
    mensaje = data.get('mensaje', '')

    # URLs de los microservicios
    url_microservicio_gpt = "https://smishguard-chatgpt-ms.onrender.com/consultar-modelo-gpt"
    url_microservicio = "https://smishguard-modeloml-ms.onrender.com/predict"
    url_microservicio_vt = "https://smishguard-virustotal-ms.onrender.com/analyze-url"

    headers = {'Content-Type': 'application/json'}
    payload_gpt = {"mensaje": mensaje}
    payload = {"text": mensaje}

    # Detectar URLs en el mensaje
    urls = re.findall(r'(?:https?://)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?', mensaje)
    payload_vt = {"url": urls[0]} if urls else {}

    # Timeout en segundos
    timeout_duration = 15

    # Hacemos las solicitudes de manera asíncrona
    async with aiohttp.ClientSession() as session:

        # Definir las tareas asíncronas con timeout
        async def consultar_gpt():
            try:
                async with session.post(url_microservicio_gpt, headers=headers, json=payload_gpt, timeout=timeout_duration) as response:
                    return await response.json()
            except asyncio.TimeoutError:
                return "La solicitud al microservicio GPT demoró más de 15 segundos"
            except aiohttp.ClientError as e:
                return "Error al contactar con el microservicio GPT"

        async def consultar_spam():
            try:
                async with session.post(url_microservicio, headers=headers, json=payload, timeout=timeout_duration) as response:
                    return await response.json()
            except asyncio.TimeoutError:
                return "La solicitud al microservicio de detección de spam demoró más de 15 segundos"
            except aiohttp.ClientError as e:
                return "Error al contactar con el microservicio de detección de spam"

        async def consultar_virustotal():
            if not urls:
                return {"Error": "No se encontraron URLs en el mensaje"}
            try:
                async with session.post(url_microservicio_vt, headers=headers, json=payload_vt, timeout=timeout_duration+30) as response:
                    vt_response = await response.json()
                    vt_response['url'] = urls[0]
                    return vt_response
            except asyncio.TimeoutError:
                return "La solicitud al microservicio VirusTotal demoró más de 45 segundos"
            except aiohttp.ClientError as e:
                return "Error al contactar con el microservicio de VirusTotal"

        # Ejecutamos las tareas en paralelo
        gpt_task = consultar_gpt()
        spam_task = consultar_spam()
        vt_task = consultar_virustotal()

        # Esperamos a que todas las tareas terminen
        response_json_microservicio_gpt, response_json_microservicio, response_json_microservicio_vt = await asyncio.gather(
            gpt_task, spam_task, vt_task
        )

    # Combinar las respuestas de los microservicios
    resultado_final = {
        "analisis_openai": response_json_microservicio_gpt,
        "analisis_microservicio": response_json_microservicio,
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
