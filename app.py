from flask import Flask, jsonify, request
from openai import OpenAI
from datetime import datetime
from model.MensajeSMS import MensajeSMS
from model.Alerta import Alerta
from model.Analisis import Analisis
import json
import os

app = Flask(__name__)
application = app
client = OpenAI()

# Ruta temporal para verificar la API key
@app.route('/check-api-key')
def check_api_key():
    api_key = os.getenv('OPENAI_API_KEY')
    return jsonify({"OPENAI_API_KEY": api_key})

@app.route('/')
def hello_world():
    return 'hello, world!'

@app.route("/ping")
def ping():
    return jsonify({"message": "pong"})

@app.route("/consultar-modelo", methods = ['POST'])
async def consultar_modelo():
    #mensajePrueba = MensajeSMS(1, "Prueba", datetime.now(), "+573107788388")
    analisisPrueba = Analisis(1, 1, 0.8, "otros detalles")
    #return jsonify({"Mensaje enviado": json.dumps(mensajePrueba.to_dict())})

    # Obtener el objeto JSON enviado en el cuerpo de la solicitud
    data = request.get_json()
    mensaje = data.get('mensaje', '')

    # Realizar la solicitud a la API de OpenAI
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
        {"role": "system", "content": "Eres un asistente de IA especializado en identificar mensajes de phishing. Proporciona una probabilidad entre 0 (no peligroso) y 1 (muy peligroso). Responde en el siguiente formato JSON: { \"Calificación\": [número], \"Descripción\": \"[breve explicación]\" }"},
        {f"role": "user", "content": 'Evalúa este mensaje: "{mensaje}"'}
        ]
    );   
    
    #return jsonify({"Analisis realizado": json.dumps(analisisPrueba.to_dict())})

    # Convertir la cadena JSON a un objeto Python
    response_json = json.loads(response.choices[0].message.content)
    
    # Retornar el objeto JSON en la respuesta
    return jsonify(response_json)

@app.route("/publicar-tweet")
def publicar_tweet():
    tweetPrueba = Alerta(1, "123 Tweet probando", datetime.now())
    return jsonify({"Publicacion": json.dumps(tweetPrueba.to_dict())})

@app.route("/base-datos")
def base_datos():
    return jsonify({"message": "pong"})

if __name__ == '__main__':
    app.run(debug = True)
