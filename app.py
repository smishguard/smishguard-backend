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
from datetime import datetime, timedelta
from random import randint

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
    numero_celular = data.get('numero_celular', None)

    # Conexión a la colección Mensajes
    collection = db['Mensajes']

    # Buscar el mensaje en la base de datos
    mensaje_encontrado = collection.find_one({"contenido": mensaje})

    # Calcular la fecha de hace un mes
    hace_un_mes = datetime.utcnow() - timedelta(days=30)

    if mensaje_encontrado:
        fecha_analisis = datetime.fromisoformat(mensaje_encontrado['analisis']['fecha_analisis'][:-1])
        if fecha_analisis > hace_un_mes:
            return jsonify({
                "analisis_gpt": mensaje_encontrado['analisis']['justificacion_gpt'],
                "analisis_smishguard": mensaje_encontrado['analisis']['nivel_peligro'],
                "enlace": mensaje_encontrado['url'],
                "resultado_url": mensaje_encontrado['analisis'].get('resultado_url', "No disponible"),
                "resultado_ml": mensaje_encontrado['analisis'].get('resultado_ml', "No disponible"),
                "mensaje_analizado": mensaje_encontrado['contenido'],
                "numero_celular": numero_celular,
                "puntaje": mensaje_encontrado['analisis']['ponderado']
            })

    # URLs de los microservicios
    url_microservicio_gpt = "https://smishguard-chatgpt-ms.onrender.com/consultar-modelo-gpt"
    url_conclusion_gpt = "https://smishguard-chatgpt-ms.onrender.com/conclusion-modelo-gpt"
    url_microservicio_ml = "https://smishguard-modeloml-ms.onrender.com/predict"
    url_microservicio_vt = "https://smishguard-virustotal-ms.onrender.com/analyze-url"

    headers = {'Content-Type': 'application/json'}
    payload_ml = {"text": mensaje}

    # Detectar URLs en el mensaje
    urls = re.findall(r'\b(?:https?://)?(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?\b', mensaje)
    payload_vt = {"url": urls[0]} if urls else {}

    # Timeout en segundos
    timeout_duration = 15

    async with aiohttp.ClientSession() as session:

        async def consultar_spam():
            try:
                async with session.post(url_microservicio_ml, headers=headers, json=payload_ml, timeout=timeout_duration) as response:
                    return await response.json()
            except asyncio.TimeoutError:
                return {"error": "Timeout en ML"}
            except aiohttp.ClientError:
                return {"error": "Error en ML"}

        async def consultar_virustotal():
            if not urls:
                return {"overall_result": "SIN URL", "url": "No se proporcionó URL"}
            try:
                async with session.post(url_microservicio_vt, headers=headers, json=payload_vt, timeout=timeout_duration + 30) as response:
                    vt_response = await response.json()
                    vt_response['url'] = urls[0]
                    return vt_response
            except asyncio.TimeoutError:
                return {"error": "Timeout en VirusTotal"}
            except aiohttp.ClientError:
                return {"error": "Error en VirusTotal"}

        # Ejecutar consultas a ML y VirusTotal primero
        spam_task = consultar_spam()
        vt_task = consultar_virustotal()

        response_json_ml, response_json_vt = await asyncio.gather(spam_task, vt_task)

    # Procesar respuestas de ML y VirusTotal
    valor_vt = 0
    enlace_retornado_vt = "No se analizaron URLs"
    resultado_url = "Indeterminado"
    if isinstance(response_json_vt, dict) and 'overall_result' in response_json_vt:
        valor_vt = 1 if response_json_vt['overall_result'] == "POSITIVO: ES MALICIOSO" else 0
        enlace_retornado_vt = response_json_vt['url']
        resultado_url = "Malicioso" if valor_vt == 1 else "Seguro"

    valor_ml = 0
    resultado_ml = "No disponible"
    if isinstance(response_json_ml, dict) and 'prediction' in response_json_ml:
        valor_ml = 1 if response_json_ml['prediction'] == 'spam' else 0
        resultado_ml = "Spam" if valor_ml == 1 else "No Spam"

    # Preparar payload para el servicio GPT con solo el mensaje
    payload_gpt = {
        "mensaje": mensaje
    }

    async with aiohttp.ClientSession() as session:
        async def consultar_gpt():
            try:
                async with session.post(url_microservicio_gpt, headers=headers, json=payload_gpt, timeout=timeout_duration) as response:
                    return await response.json()
            except asyncio.TimeoutError:
                return {"error": "Timeout en GPT"}
            except aiohttp.ClientError:
                return {"error": "Error en GPT"}

        response_json_gpt = await consultar_gpt()

    # Verificar que 'Calificación' es numérico; si no, asignar 0 por defecto
    valor_gpt_raw = response_json_gpt.get("Calificación", 0)
    if isinstance(valor_gpt_raw, (int, float)):
        valor_gpt = float(valor_gpt_raw)
    else:
        valor_gpt = 0

    # Ajustar ponderaciones y calcular el puntaje ponderado
    ponderacion_ml = ponderacion_gpt = ponderacion_vt = 0.0

    if not urls:
        ponderacion_ml = 0.60
        ponderacion_gpt = 0.40
    elif "error" in response_json_gpt:
        ponderacion_ml = 0.70
        ponderacion_vt = 0.30
    elif "error" in response_json_ml:
        ponderacion_gpt = 0.70
        ponderacion_vt = 0.30
    elif "error" in response_json_vt:
        ponderacion_ml = 0.60
        ponderacion_gpt = 0.40
    else:
        ponderacion_vt = 0.35
        ponderacion_ml = 0.40
        ponderacion_gpt = 0.25

    # Calcular el puntaje total
    puntaje_total = (float(valor_vt) * ponderacion_vt) + (float(valor_ml) * ponderacion_ml) + (float(valor_gpt) * ponderacion_gpt)
    puntaje_escalado = round(1 + (puntaje_total * 9))

    # Clasificar según el puntaje escalado
    if puntaje_escalado <= 3:
        analisis_smishguard = "Seguro"
    elif puntaje_escalado <= 7:
        analisis_smishguard = "Sospechoso"
    else:
        analisis_smishguard = "Peligroso"

    # Estructura de la respuesta
    resultado_parcial = {
        "valor_gpt": valor_gpt,
        "analisis_smishguard": analisis_smishguard,
        "enlace": enlace_retornado_vt,
        "resultado_url": resultado_url,
        "resultado_ml": resultado_ml,
        "mensaje_analizado": mensaje,
        "numero_celular": numero_celular,
        "puntaje": puntaje_escalado
    }

    # Preparar payload para el servicio GPT con todo el analísis para realizar la conclusión
    payload_gpt = {
        "resultado_parcial": resultado_parcial
    }

    try:
        response = requests.post(url_conclusion_gpt, headers=headers, json=payload_gpt, timeout=timeout_duration)
        response_json_gpt = response.json()
    except requests.Timeout:
        response_json_gpt = {"error": "Timeout en GPT"}
    except requests.RequestException:
        response_json_gpt = {"error": "Error en GPT"}

    conclusion_gpt = response_json_gpt.get("conclusion", "No disponible") if isinstance(response_json_gpt, dict) else "No disponible"

    # Si se realizó un análisis nuevo o es la primera vez, guardar o actualizar en la base de datos
    if not any("error" in res for res in [response_json_gpt, response_json_ml]):
        nuevo_documento = {
            "contenido": mensaje,
            "numero_celular": numero_celular,
            "url": enlace_retornado_vt,
            "analisis": {
                "calificacion_gpt": valor_gpt,
                "calificacion_ml": valor_ml,
                "ponderado": puntaje_escalado,
                "nivel_peligro": analisis_smishguard,
                "calificacion_vt": valor_vt,
                "justificacion_gpt": conclusion_gpt,
                "resultado_url": resultado_url,
                "resultado_ml": resultado_ml,
                "fecha_analisis": datetime.utcnow().isoformat() + 'Z'
            }
        }
        if mensaje_encontrado:
            collection.update_one({"_id": mensaje_encontrado["_id"]}, {"$set": nuevo_documento})
        else:
            collection.insert_one(nuevo_documento)
    
    resultado_final = {
        "analisis_gpt": conclusion_gpt,
        "analisis_smishguard": analisis_smishguard,
        "enlace": enlace_retornado_vt,
        "resultado_url": resultado_url,
        "resultado_ml": resultado_ml,
        "mensaje_analizado": mensaje,
        "numero_celular": numero_celular,
        "puntaje": puntaje_escalado
    }
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

@app.route("/mensajes-para-publicar", methods=['GET'])
def mensajes_para_publicar():
    try:
        # Seleccionar la colección MensajesParaPublicar
        collection = db['MensajesParaPublicar']

        # Filtrar solo los mensajes que no han sido publicados (publicado = false)
        documentos = collection.find({"publicado": False})
        
        # Convertir los documentos a una lista de diccionarios y convertir ObjectId a string
        documentos_list = [parse_json(doc) for doc in documentos]

        # Devolver los documentos en formato JSON
        return jsonify({"documentos": documentos_list})

    except Exception as e:
        return jsonify({"error": str(e)})

    
@app.route("/guardar-mensaje-para-publicar", methods=['POST'])
def guardar_mensaje_para_publicar():
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

        # Conexión a la colección MensajesParaPublicar
        collection = db['MensajesParaPublicar']

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
        # Conexión a la colección MensajesParaPublicar
        collection = db['MensajesParaPublicar']

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
@app.route("/eliminar-mensaje-para-publicar/<mensaje_id>", methods=['DELETE'])
def eliminar_mensaje(mensaje_id):
    try:
        # Conexión a la colección MensajesParaPublicar
        collection = db['MensajesParaPublicar']

        # Intentar eliminar el mensaje por su ID
        resultado = collection.delete_one({"_id": ObjectId(mensaje_id)})
        
        # Verificar si el mensaje fue encontrado y eliminado
        if resultado.deleted_count == 0:
            return jsonify({"error": "Mensaje no encontrado"}), 404

        return jsonify({"mensaje": "El mensaje ha sido eliminado exitosamente."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/publicar-tweet", methods=['POST'])
def publicar_tweet():
    data = request.get_json()
    mensaje = data.get('mensaje', '')

    if not mensaje:
        return jsonify({"error": "No se proporcionó un mensaje"}), 400

    # Reemplazar las URLs en el mensaje con "[ENLACE REMOVIDO]"
    mensaje_sin_url = re.sub(r'\b(?:https?://)?(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?\b', '[ENLACE REMOVIDO]', mensaje)

    url_microservicio_twitter = "https://smishguard-twitter-ms.onrender.com/tweet"
    headers = {'Content-Type': 'application/json'}
    payload = {"sms": mensaje_sin_url}

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

@app.route("/eliminar-comentario-soporte/<comentario_id>", methods=['DELETE'])
def eliminar_comentario(comentario_id):
    try:
        # Conexión a la colección ComentariosSoporte
        collection = db['ComentariosSoporte']

        # Intentar eliminar el comentario por su ID
        resultado = collection.delete_one({"_id": ObjectId(comentario_id)})
        
        # Verificar si el comentario fue encontrado y eliminado
        if resultado.deleted_count == 0:
            return jsonify({"error": "Comentario no encontrado"}), 404

        return jsonify({"mensaje": "El comentario ha sido eliminado exitosamente."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# Endpoint para almacenar el historial de mensajes reportados por usuario
# Endpoint para almacenar el historial de mensajes reportados por usuario

@app.route("/historial-analisis-usuarios", methods=['POST'])
def historial_analisis_usuarios():
    try:
        data = request.get_json()
        mensaje = data.get('mensaje', '')
        url = data.get('url', None)
        analisis = data.get('analisis', {})
        correo = data.get('correo', '')
        numero_celular = data.get('numero_celular', None)  # Nuevo campo

        # Verificar que todos los campos requeridos están presentes
        if not mensaje or not url or not analisis or not correo or not numero_celular:
            return jsonify({"error": "Faltan campos requeridos (mensaje, url, analisis, correo, numero_celular)"}), 400

        # Insertar en la colección HistorialAnalisisUsuarios
        collection = db['HistorialAnalisisUsuarios']
        nuevo_reporte = {
            "mensaje": mensaje,
            "url": url,
            "correo": correo,
            "numero_celular": numero_celular,  # Guardar el número de celular en el historial
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
@app.route("/historial-analisis-usuarios/<correo>", methods=['GET'])
def obtener_historial_analisis_usuarios(correo):
    try:
        collection = db['HistorialAnalisisUsuarios']
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

@app.route("/historial-analisis-usuarios/<id>", methods=['DELETE'])
def eliminar_historial_mensaje_reportado(id):
    try:
        collection = db['HistorialAnalisisUsuarios']
        result = collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            return jsonify({"error": "No se encontró el historial a eliminar"}), 404
        return jsonify({"mensaje": "Historial eliminado exitosamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/numeros-bloqueados/<correo>/<numero>", methods=['DELETE'])
def eliminar_numero_bloqueado(correo, numero):
    try:
        # Conexión a la colección NumerosBloqueadosUsuarios
        collection = db['NumerosBloqueadosUsuarios']
        
        # Buscar y eliminar el documento usando el correo y el número de celular
        result = collection.delete_one({"correo": correo, "numero": numero})
        
        # Verificar si se encontró y eliminó el documento
        if result.deleted_count == 0:
            return jsonify({"error": "No se encontró el número a eliminar para el correo especificado"}), 404

        return jsonify({"mensaje": "Número bloqueado eliminado exitosamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/mensaje-aleatorio", methods=['GET'])
def mensaje_aleatorio():
    try:
        collection = db['Mensajes']
        total_mensajes = collection.count_documents({})
        if total_mensajes == 0:
            return jsonify({"error": "No hay mensajes disponibles"}), 404
        random_index = randint(0, total_mensajes - 1)
        mensaje_aleatorio = collection.find().skip(random_index).limit(1)
        mensaje = next(mensaje_aleatorio, None)
        mensaje = parse_json(mensaje)
        return jsonify({"mensaje": mensaje}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/estadisticas", methods=['GET'])
def obtener_estadisticas():
    try:
        # Conexión a la colección Mensajes
        mensajes_collection = db['Mensajes']

        # Contar el total de mensajes analizados
        total_mensajes = mensajes_collection.count_documents({})

        # Contar cuántos mensajes se catalogaron como seguros, sospechosos y peligrosos
        seguros = mensajes_collection.count_documents({"analisis.nivel_peligro": "Seguro"})
        sospechosos = mensajes_collection.count_documents({"analisis.nivel_peligro": "Sospechoso"})
        peligrosos = mensajes_collection.count_documents({"analisis.nivel_peligro": "Peligroso"})

        # Conexión a la colección MensajesParaPublicar
        mensajes_publicar_collection = db['MensajesParaPublicar']

        # Contar el total de mensajes en MensajesParaPublicar
        total_mensajes_para_publicar = mensajes_publicar_collection.count_documents({})

        # Contar cuántos mensajes han sido publicados y cuántos no
        publicados = mensajes_publicar_collection.count_documents({"publicado": True})
        no_publicados = mensajes_publicar_collection.count_documents({"publicado": False})

        # Estructurar la respuesta en JSON
        estadisticas = {
            "mensajes": {
                "total_analizados": total_mensajes,
                "seguros": seguros,
                "sospechosos": sospechosos,
                "peligrosos": peligrosos
            },
            "mensajes_para_publicar": {
                "total": total_mensajes_para_publicar,
                "publicados": publicados,
                "no_publicados": no_publicados
            }
        }

        return jsonify(estadisticas), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
