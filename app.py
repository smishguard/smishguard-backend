from flask import Flask, jsonify, request
import requests
import firebase_admin
from firebase_admin import credentials, firestore
import os
from info_test import info_test

app = Flask(__name__)
app.config.from_object('config.Config')

@app.route("/ping")
def ping():
    return jsonify({"message": "pong"})

# Inicializar Firebase
cred = credentials.Certificate(app.config['FIREBASE_CREDENTIALS'])
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route('/consumir_servicios', methods=['POST'])
def consumir_servicios():
    data = request.json
    chatgpt_response = requests.post('https://api.openai.com/v1/chat/completions', json=data['chatgpt'])
    ml_response = requests.post('https://api.mimodeloml.com/predict', json=data['ml'])
    virustotal_response = requests.get(f'https://www.virustotal.com/api/v3/files/{data["virustotal"]["file_id"]}')
    
    return jsonify({
        'chatgpt': chatgpt_response.json(),
        'ml': ml_response.json(),
        'virustotal': virustotal_response.json()
    })

@app.route('/almacenar_datos', methods=['POST'])
def almacenar_datos():
    data = request.json
    doc_ref = db.collection('mis_datos').add(data)
    return jsonify({'id': doc_ref[1].id})

@app.route('/consumir_twitter', methods=['GET'])
def consumir_twitter():
    headers = {
        'Authorization': f'Bearer {app.config["TWITTER_BEARER_TOKEN"]}'
    }
    response = requests.get('https://api.twitter.com/2/tweets', headers=headers)
    return jsonify(response.json())
'''
@app.route("/info", methods=["GET"])
def obtenerInfo():
    return jsonify(info_test)

@app.route("/info/<string:id>", methods=["GET"])
def obtenerInfoXId(id):
    #print(id)
    info_found = {}
    for info in info_test:
        if str(info['id']) == id:
            info_found = info
            break
    return jsonify({"info": info_found})

@app.route('/info', methods=['POST'])
def agregarInfo():
    #print(request.json)
    new_info = {
        "id": request.json['id'], 
        "name": request.json['name'],
        "price": request.json['price'],
        "quantity": request.json['quantity']
    }
    info_test.append(new_info)

    return jsonify({"info": info_test, "message": "Info agregada exitosamente"})

@app.route('/info/<string:id>', methods=['PUT'])
def actualizarInfo(id):
    info_found = {}
    for info in info_test:
        if str(info['id']) == id:
            info_found = info
            break
    
    if info_found:
        info_found['name'] = request.json['name']
        info_found['price'] = request.json['price']
        info_found['quantity'] = request.json['quantity']
        return jsonify({"info": info_test, "message": "Info actualizada exitosamente"})

    return jsonify({"message": "Info no encontrada"})

@app.route('/info/<string:id>', methods=['DELETE'])
def eliminarInfo(id):
    info_found = {}
    for info in info_test:
        if str(info['id']) == id:
            info_found = info
            break
    
    if info_found:
        info_test.remove(info_found)
        return jsonify({"info": info_test, "message": "Info eliminada exitosamente"})
    
    return jsonify({"message": "Info no encontrada"})
'''
if __name__ == '__main__':
    app.run(debug = True, port=4000)
