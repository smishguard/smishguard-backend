from flask import Flask, jsonify, request
from flask_cors import CORS  # Importa el paquete CORS
from datetime import datetime
import json
import requests
import re
import aiohttp
import asyncio

app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

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

    async with aiohttp.ClientSession() as session:

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

        gpt_task = consultar_gpt()
        spam_task = consultar_spam()
        vt_task = consultar_virustotal()

        response_json_microservicio_gpt, response_json_microservicio, response_json_microservicio_vt = await asyncio.gather(
            gpt_task, spam_task, vt_task
        )

    resultado_final = {
        "analisis_openai": response_json_microservicio_gpt,
        "analisis_microservicio": response_json_microservicio,
        "analisis_microservicio_vt": response_json_microservicio_vt
    }

    return jsonify(resultado_final)

@app.route("/publicar-tweet", methods=['POST'])
def publicar_tweet():
    data = request.get_json()
    mensaje = data.get('mensaje', '')

    if not mensaje:
        return jsonify({"error": "No se proporcionó un mensaje"}), 400

    url_microservicio_twitter = "https://smishguard-twitter-ms.onrender.com/tweet"
    headers = {'Content-Type': 'application/json'}
    payload = {"sms": mensaje}

    try:
        response = requests.post(url_microservicio_twitter, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return jsonify({
            "mensaje": "Tweet publicado exitosamente",
            "ResultadoTwitter": result
        }), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"mensaje": "Error al publicar el tweet", "ResultadoTwitter": str(e)}), 500

@app.route("/base-datos")
def base_datos():
    return jsonify({"message": "pong"})

if __name__ == '__main__':
    app.run(debug=True)
