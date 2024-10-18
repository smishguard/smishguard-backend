from flask import Flask, jsonify, request
from flask_cors import CORS
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
        # Si el mensaje ya existe en la base de datos, devolver el análisis almacenado en la estructura estandarizada
        return jsonify({
            "mensaje_analizado": mensaje_encontrado['contenido'],
            "enlace": mensaje_encontrado['url'],
            "analisis_gpt": mensaje_encontrado['analisis']['justificacion_gpt'],
            "puntaje": mensaje_encontrado['analisis']['ponderado'],
            "analisis_smishguard": mensaje_encontrado['analisis']['nivel_peligro']
        })

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
                return {"error": "Timeout en GPT"}
            except aiohttp.ClientError as e:
                return {"error": "Error en GPT"}

        async def consultar_spam():
            try:
                async with session.post(url_microservicio, headers=headers, json=payload, timeout=timeout_duration) as response:
                    return await response.json()
            except asyncio.TimeoutError:
                return {"error": "Timeout en ML"}
            except aiohttp.ClientError as e:
                return {"error": "Error en ML"}

        async def consultar_virustotal():
            if not urls:
                return {"error": "No se encontraron URLs en el mensaje"}
            try:
                async with session.post(url_microservicio_vt, headers=headers, json=payload_vt, timeout=timeout_duration+30) as response:
                    vt_response = await response.json()
                    vt_response['url'] = urls[0]
                    return vt_response
            except asyncio.TimeoutError:
                return {"error": "Timeout en VirusTotal"}
            except aiohttp.ClientError as e:
                return {"error": "Error en VirusTotal"}

        gpt_task = consultar_gpt()
        spam_task = consultar_spam()
        vt_task = consultar_virustotal()

        response_json_microservicio_gpt, response_json_microservicio, response_json_microservicio_vt = await asyncio.gather(
            gpt_task, spam_task, vt_task
        )

    # Manejar los valores devueltos de los microservicios
    valor_vt = 0
    enlace_retornado_vt = "No se analizaron URLs"
    if isinstance(response_json_microservicio_vt, dict) and 'overall_result' in response_json_microservicio_vt:
        valor_vt = 1 if response_json_microservicio_vt['overall_result'] == "POSITIVO: ES MALICIOSO" else 0
        enlace_retornado_vt = response_json_microservicio_vt['url']

    valor_ml = 0
    if isinstance(response_json_microservicio, dict) and 'prediction' in response_json_microservicio:
        valor_ml = 1 if response_json_microservicio['prediction'] == 'spam' else 0

    valor_gpt = 0
    analisis_gpt = "No disponible"
    if isinstance(response_json_microservicio_gpt, dict) and 'Calificación' in response_json_microservicio_gpt:
        valor_gpt = response_json_microservicio_gpt['Calificación']
        analisis_gpt = response_json_microservicio_gpt['Descripción']

    # Calcular el puntaje ponderado
    ponderacion_vt = 0.35
    ponderacion_ml = 0.40
    ponderacion_gpt = 0.25

    puntaje_total = (valor_vt * ponderacion_vt) + (valor_ml * ponderacion_ml) + (valor_gpt * ponderacion_gpt)
    puntaje_escalado = round(1 + (puntaje_total * 9))

    # Clasificar según el puntaje escalado
    if puntaje_escalado <= 3:
        analisis_smishguard = "Seguro"
    elif puntaje_escalado <= 7:
        analisis_smishguard = "Sospechoso"
    else:
        analisis_smishguard = "Peligroso"

    resultado_final = {
        "mensaje_analizado": mensaje,
        "enlace": enlace_retornado_vt,
        "analisis_gpt": analisis_gpt,
        "puntaje": puntaje_escalado,
        "analisis_smishguard": analisis_smishguard
    }

    # Verificar que no haya errores antes de guardar en la base de datos
    if not any("error" in res for res in [response_json_microservicio_gpt, response_json_microservicio, response_json_microservicio_vt]):
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
                "fecha_analisis": datetime.utcnow().isoformat() + 'Z'
            }
        }
        collection.insert_one(nuevo_documento)

    return jsonify(resultado_final)


# Función para convertir ObjectId a string en todos los documentos
def parse_json(doc):
    """
    Convierte los ObjectId en los documentos a strings para que sean serializables en JSON.
    """
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
    return doc

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

# Endpoint para almacenar comentarios de soporte
@app.route("/comentario-soporte", methods=['POST'])
def comentario_soporte():
    try:
        data = request.get_json()
        comentario = data.get('comentario', '')
        correo = data.get('correo', '')

        if not comentario or not correo:
            return jsonify({"error": "El comentario y el correo son requeridos"}), 400

        # Insertar en la colección ComentariosSoporte
        collection = db['ComentariosSoporte']
        nuevo_comentario = {
            "comentario": comentario,
            "correo": correo,
            "fecha": datetime.utcnow().isoformat() + 'Z'
        }
        collection.insert_one(nuevo_comentario)

        return jsonify({"mensaje": "Comentario guardado exitosamente."}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint para consultar comentarios de soporte por correo
@app.route("/comentario-soporte", methods=['GET'])
def obtener_todos_comentarios_soporte():
    try:
        collection = db['ComentariosSoporte']
        comentarios = collection.find()
        comentarios_list = [parse_json(comentario) for comentario in comentarios]

        return jsonify({"comentarios": comentarios_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint para almacenar el historial de mensajes reportados por usuario
@app.route("/historial-mensajes-reportados", methods=['POST'])
def historial_mensajes_reportados():
    try:
        data = request.get_json()
        mensaje = data.get('mensaje', '')
        url = data.get('url', '')
        analisis = data.get('analisis', {})
        correo = data.get('correo', '')

        if not mensaje or not url or not analisis or not correo:
            return jsonify({"error": "Faltan campos requeridos (mensaje, url, analisis, correo)"}), 400

        # Insertar en la colección HistorialMensajesReportadosUsuarios
        collection = db['HistorialMensajesReportadosUsuarios']
        nuevo_reporte = {
            "mensaje": mensaje,
            "url": url,
            "correo": correo,
            "analisis": {
                "calificacion_gpt": analisis.get('calificacion_gpt', 0),
                "calificacion_ml": analisis.get('calificacion_ml', False),
                "ponderado": analisis.get('ponderado', 0),
                "nivel_peligro": analisis.get('nivel_peligro', "Indeterminado"),
                "calificacion_vt": analisis.get('calificacion_vt', False),
                "justificacion_gpt": analisis.get('justificacion_gpt', ""),
                "fecha_analisis": analisis.get('fecha_analisis', datetime.utcnow().isoformat() + 'Z')
            }
        }
        collection.insert_one(nuevo_reporte)

        return jsonify({"mensaje": "Historial de mensaje reportado guardado exitosamente."}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint para consultar historial de mensajes reportados por correo
@app.route("/historial-mensajes-reportados/<correo>", methods=['GET'])
def obtener_historial_mensajes_reportados(correo):
    try:
        collection = db['HistorialMensajesReportadosUsuarios']
        historial = collection.find({"correo": correo})
        historial_list = [parse_json(mensaje) for mensaje in historial]

        return jsonify({"historial": historial_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint para almacenar números bloqueados por usuarios
@app.route("/numeros-bloqueados", methods=['POST'])
def numeros_bloqueados():
    try:
        data = request.get_json()
        numero = data.get('numero', '')
        correo = data.get('correo', '')

        if not numero or not correo:
            return jsonify({"error": "El número de teléfono y el correo son requeridos"}), 400

        # Insertar en la colección NumerosBloqueadosUsuarios
        collection = db['NumerosBloqueadosUsuarios']
        nuevo_numero_bloqueado = {
            "numero": numero,
            "correo": correo,
            "fecha_bloqueo": datetime.utcnow().isoformat() + 'Z'
        }
        collection.insert_one(nuevo_numero_bloqueado)

        return jsonify({"mensaje": "Número bloqueado guardado exitosamente."}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint para consultar números bloqueados por correo
@app.route("/numeros-bloqueados/<correo>", methods=['GET'])
def obtener_numeros_bloqueados(correo):
    try:
        collection = db['NumerosBloqueadosUsuarios']
        numeros = collection.find({"correo": correo})
        numeros_list = [parse_json(numero) for numero in numeros]

        return jsonify({"numeros": numeros_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
