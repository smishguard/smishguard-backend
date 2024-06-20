from flask import Flask, jsonify, request
from info_test import info_test

app = Flask(__name__)

@app.route("/ping")
def ping():
    return jsonify({"message": "pong"})

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

if __name__ == '__main__':
    app.run(debug = True, port=4000)
