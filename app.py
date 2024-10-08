from flask import Flask, jsonify, request
from flask_cors import CORS  # Importa el paquete CORS
from pymongo import MongoClient
from bson import ObjectId 
from dotenv import load_dotenv
import requests
import re
import aiohttp
import asyncio
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

application = app

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# URI de MongoDB Atlas
MONGO_URI = f"mongodb+srv://{os.getenv('MONGO_USERNAME')}:{os.getenv('DB_PASSWORD')}@clustermain.pagaw.mongodb.net/?retryWrites=true&w=majority&appName=ClusterMain"

# Conexión al cliente MongoDB Atlas
client = MongoClient(MONGO_URI)

# Seleccionar la base de datos
db = client[os.getenv("MONGO_DBNAME")]

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

    # Conexión a la colección Mensaje
    collection = db['Mensaje']
    
    # Buscar el mensaje en la base de datos
    mensaje_encontrado = collection.find_one({"contenido": mensaje})

    if mensaje_encontrado:
        # Si el mensaje ya existe en la base de datos, devolver el análisis almacenado
        return jsonify(mensaje_encontrado['analisis'])

    # Si el mensaje no existe en la base de datos, realizar el análisis
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

        gpt_task = consultar_gpt()
        spam_task = consultar_spam()
        vt_task = consultar_virustotal()

        response_json_microservicio_gpt, response_json_microservicio, response_json_microservicio_vt = await asyncio.gather(
            gpt_task, spam_task, vt_task
        )

    # Ponderaciones
    ponderacion_vt = 0.35
    ponderacion_ml = 0.40
    ponderacion_gpt = 0.25

    # Valor numérico de VirusTotal (0 si no es malicioso, 1 si es malicioso)
    if isinstance(response_json_microservicio_vt, dict) and 'overall_result' in response_json_microservicio_vt:
        valor_vt = 1 if response_json_microservicio_vt['overall_result'] == "POSITIVO: ES MALICIOSO" else 0
        enlace_retornado_vt = response_json_microservicio_vt['url']
    else:
        valor_vt = 0  # Si no se puede determinar, asumimos no malicioso
        enlace_retornado_vt = response_json_microservicio_vt

    # Valor numérico de Machine Learning (0 si 'not spam', 1 si 'spam')
    if isinstance(response_json_microservicio, dict) and 'prediction' in response_json_microservicio:
        valor_ml = 1 if response_json_microservicio['prediction'] == 'spam' else 0
    else:
        valor_ml = 0  # Si no se puede determinar, asumimos no spam

    # Valor numérico de GPT (valor entre 0 y 1) con un decimal
    if isinstance(response_json_microservicio_gpt, dict) and 'Calificación' in response_json_microservicio_gpt:
        valor_gpt = response_json_microservicio_gpt['Calificación']
        analisis_gpt = response_json_microservicio_gpt['Descripción']
    else:
        valor_gpt = 0  # Si no se puede determinar, asumimos 0
        analisis_gpt = response_json_microservicio_gpt

    # Calcular el puntaje ponderado
    puntaje_total = (valor_vt * ponderacion_vt) + (valor_ml * ponderacion_ml) + (valor_gpt * ponderacion_gpt)

    # Escalar el puntaje a una escala de 1 a 10
    puntaje_escalado = round(1 + (puntaje_total * 9))

    # Crear la variable analisis_smishguard según el puntaje_escalado
    if puntaje_escalado >= 1 and puntaje_escalado <= 3:
        analisis_smishguard = "Seguro"
    elif puntaje_escalado >= 4 and puntaje_escalado <= 7:
        analisis_smishguard = "Sospechoso"
    elif puntaje_escalado >= 8 and puntaje_escalado <= 10:
        analisis_smishguard = "Peligroso"
    else:
        analisis_smishguard = "Indeterminado"  # Por si el puntaje queda fuera del rango esperado

    resultado_final = {
        "mensaje_analizado": mensaje,
        "enlace": enlace_retornado_vt,
        "analisis_gpt": analisis_gpt,
        "puntaje": puntaje_escalado,
        "analisis_smishguard": analisis_smishguard
    }

    # Almacenar el análisis en la base de datos solo si no existe previamente (esto ya no es necesario porque ya comprobamos antes)
    nuevo_documento = {
        "contenido": mensaje,
        "url": enlace_retornado_vt,
        "analisis": {
            "calificacion_gpt": valor_gpt,
            "calificacion_ml": valor_ml,
            "ponderado": puntaje_escalado,
            "nivel_peligro": analisis_smishguard,
            "calificacion_vt": valor_vt,
            "justificacion_gpt": analisis_gpt,
            "fecha_analisis": datetime.utcnow().isoformat() + 'Z'  # ISO 8601 con zona horaria Z
        }
    }

    # Insertar el nuevo documento en la base de datos
    collection.insert_one(nuevo_documento)

    return jsonify(resultado_final)


# Función para convertir ObjectId a string en todos los documentos
def parse_json(doc):
    """
    Convierte los ObjectId en los documentos a strings para que sean serializables en JSON.
    """
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)  # Convertir ObjectId a string
    return doc

@app.route("/base-datos")
def base_datos():
    try:
        # Seleccionar la colección dentro de la base de datos
        collection = db['Mensaje']

        # Realizar una operación en la base de datos (ejemplo: encontrar todos los documentos)
        documentos = collection.find()
        
        # Convertir los documentos a una lista de diccionarios, y convertir ObjectId a string
        documentos_list = [parse_json(doc) for doc in documentos]

        # Devolver los documentos en formato JSON
        return jsonify({"documentos": documentos_list})

    except Exception as e:
        return jsonify({"error": str(e)})
    
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

@app.route("/mensajes-reportados", methods=['GET'])
def mensajes_reportados():
    try:
        # Seleccionar la colección MensajesReportados
        collection = db['MensajesReportados']

        # Filtrar solo los mensajes que no han sido publicados (publicado = false)
        documentos = collection.find({"publicado": False})
        
        # Convertir los documentos a una lista de diccionarios y convertir ObjectId a string
        documentos_list = [parse_json(doc) for doc in documentos]

        # Devolver los documentos en formato JSON
        return jsonify({"documentos": documentos_list})

    except Exception as e:
        return jsonify({"error": str(e)})

    
@app.route("/guardar-mensaje-reportado", methods=['POST'])
def guardar_mensaje_reportado():
    try:
        # Obtener los datos enviados en la solicitud
        data = request.get_json()

        # Validar que los campos requeridos estén presentes
        contenido = data.get('contenido', '')
        url = data.get('url', '')
        analisis = data.get('analisis', {})
        publicado = data.get('publicado', False)  # Valor por defecto es False

        if not contenido or not url or not analisis:
            return jsonify({"error": "Faltan campos requeridos (contenido, url o analisis)."}), 400

        # Conexión a la colección MensajesReportados
        collection = db['MensajesReportados']

        # Verificar si ya existe un mensaje con el mismo contenido
        mensaje_existente = collection.find_one({"contenido": contenido})

        if mensaje_existente:
            # Si ya existe, devolver un mensaje indicando que ya fue reportado
            return jsonify({"mensaje": "El mensaje ya fue reportado previamente.", "documento": parse_json(mensaje_existente)}), 200

        # Crear el documento para insertar
        nuevo_documento = {
            "contenido": contenido,
            "url": url,
            "publicado": publicado,  # Agregar el campo "publicado"
            "analisis": {
                "calificacion_gpt": analisis.get('calificacion_gpt', 0),
                "calificacion_ml": analisis.get('calificacion_ml', False),
                "ponderado": analisis.get('ponderado', 0),
                "nivel_peligro": analisis.get('nivel_peligro', "Indeterminado"),
                "calificacion_vt": analisis.get('calificacion_vt', False),
                "justificacion_gpt": analisis.get('justificacion_gpt', ""),
                "fecha_analisis": analisis.get('fecha_analisis', datetime.utcnow().isoformat() + 'Z')  # Usar fecha actual si no se provee
            }
        }

        # Insertar el nuevo documento en la base de datos
        collection.insert_one(nuevo_documento)

        return jsonify({"mensaje": "El mensaje reportado se ha guardado exitosamente."}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/actualizar-publicado/<mensaje_id>", methods=['PUT'])
def actualizar_publicado(mensaje_id):
    try:
        # Conexión a la colección MensajesReportados
        collection = db['MensajesReportados']

        # Buscar el mensaje por su ID
        mensaje = collection.find_one({"_id": ObjectId(mensaje_id)})
        if not mensaje:
            return jsonify({"error": "Mensaje no encontrado"}), 404

        # Actualizar el campo "publicado" a true
        collection.update_one(
            {"_id": ObjectId(mensaje_id)},
            {"$set": {"publicado": True}}
        )

        return jsonify({"mensaje": "El estado de 'publicado' ha sido actualizado exitosamente."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
