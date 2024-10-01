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
                return "No se encontraron URLs en el mensaje"
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

    # Ponderaciones
    ponderacion_vt = 0.35
    ponderacion_ml = 0.40
    ponderacion_gpt = 0.25

    # Valor numérico de VirusTotal (0 si no es malicioso, 1 si es malicioso)
    if isinstance(response_json_microservicio_vt, dict) and 'malicious' in response_json_microservicio_vt:
        valor_vt = 1 if response_json_microservicio_vt['malicious'] else 0
    else:
        valor_vt = 0  # Si no se puede determinar, asumimos no malicioso

    # Valor numérico de Machine Learning (0 si 'not spam', 1 si 'spam')
    if isinstance(response_json_microservicio, dict) and 'prediction' in response_json_microservicio:
        valor_ml = 1 if response_json_microservicio['prediction'] == 'spam' else 0
    else:
        valor_ml = 0  # Si no se puede determinar, asumimos no spam

    # Valor numérico de GPT (valor entre 0 y 1)
    if isinstance(response_json_microservicio_gpt, dict) and 'score' in response_json_microservicio_gpt:
        valor_gpt = response_json_microservicio_gpt['score']
    else:
        valor_gpt = 0  # Si no se puede determinar, asumimos 0

    # Calcular el puntaje ponderado
    puntaje_total = (valor_vt * ponderacion_vt) + (valor_ml * ponderacion_ml) + (valor_gpt * ponderacion_gpt)

    # Escalar el puntaje a una escala de 1 a 10
    puntaje_escalado = 1 + (puntaje_total * 9)

    # Combinar las respuestas de los microservicios
    resultado_final = {
        "analisis_openai": response_json_microservicio_gpt,
        "analisis_microservicio": response_json_microservicio,  # Contendrá solo {"prediction": "spam"} o {"prediction": "ham"}
        "analisis_microservicio_vt": response_json_microservicio_vt,
        "puntaje_total": puntaje_total,
        "puntaje_escalado": puntaje_escalado
    }

    # Retornar el objeto JSON combinado en la respuesta
    return jsonify(resultado_final)

@app.route("/publicar-tweet", methods=['POST'])
def publicar_tweet():
    # Obtener el cuerpo de la solicitud
    data = request.get_json()
    mensaje = data.get('mensaje', '')

    if not mensaje:
        return jsonify({"error": "No se proporcionó un mensaje"}), 400

    # URL del microservicio de Twitter
    url_microservicio_twitter = "https://smishguard-twitter-ms.onrender.com/tweet"

    # Configurar los headers y el payload
    headers = {'Content-Type': 'application/json'}
    payload = {"sms": mensaje}  # Asegurarse de que el campo coincide con lo que espera el microservicio

    try:
        # Hacer la solicitud POST al microservicio
        response = requests.post(url_microservicio_twitter, headers=headers, json=payload)
        response.raise_for_status()
        
        # Obtener la respuesta JSON del microservicio
        result = response.json()
        
        # Retornar la respuesta exitosa con los datos recibidos del microservicio
        return jsonify({
            "mensaje": "Tweet publicado exitosamente",
            "ResultadoTwitter": result
        }), 200

    except requests.exceptions.RequestException as e:
        # Manejar los errores de la solicitud al microservicio
        return jsonify({"mensaje": "Error al publicar el tweet", "ResultadoTwitter": str(e)}), 500

@app.route("/base-datos")
def base_datos():
    return jsonify({"message": "pong"})

if __name__ == '__main__':
    app.run(debug = True)
