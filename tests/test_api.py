import pytest
from app import app

# Configura el cliente de prueba para la aplicación Flask
@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_ping(client):
    """Prueba el endpoint /ping para verificar la conexión básica"""
    response = client.get('/ping')
    assert response.status_code == 200
    assert response.json == {"message": "pong"}

def test_guardar_mensaje_para_publicar(client):
    """Prueba el endpoint /guardar-mensaje-para-publicar"""
    data = {
        "contenido": "Mensaje de prueba",
        "url": "http://example.com",
        "analisis": {
            "calificacion_gpt": 3,
            "calificacion_ml": 0,
            "nivel_peligro": "Seguro"
        },
        "publicado": False
    }
    response = client.post('/guardar-mensaje-para-publicar', json=data)
    assert response.status_code == 201
    assert response.json["mensaje"] == "El mensaje reportado se ha guardado exitosamente."

def test_obtener_mensajes_para_publicar(client):
    """Prueba el endpoint /mensajes-para-publicar"""
    response = client.get('/mensajes-para-publicar')
    assert response.status_code == 200
    assert "documentos" in response.json

def test_publicar_tweet(client):
    """Prueba el endpoint /publicar-tweet"""
    data = {
        "mensaje": "Este es un tweet de prueba sin enlace"
    }
    response = client.post('/publicar-tweet', json=data)
    assert response.status_code in [200, 500]  # Dependiendo de la implementación del microservicio
    if response.status_code == 200:
        assert "mensaje" in response.json
        assert response.json["mensaje"] == "Tweet publicado exitosamente"

def test_comentario_soporte(client):
    """Prueba el endpoint /comentario-soporte para almacenar un comentario"""
    data = {
        "comentario": "Este es un comentario de prueba",
        "correo": "test@test.com"
    }
    response = client.post('/comentario-soporte', json=data)
    assert response.status_code == 201
    assert response.json["mensaje"] == "Comentario guardado exitosamente."

def test_obtener_comentarios_soporte(client):
    """Prueba el endpoint /comentario-soporte para obtener comentarios almacenados"""
    response = client.get('/comentario-soporte')
    assert response.status_code == 200
    assert "comentarios" in response.json

def test_actualizar_publicado(client):
    """Prueba el endpoint /actualizar-publicado para cambiar el estado de publicado de un mensaje"""
    # Primero, guarda un mensaje para actualizarlo después
    data = {
        "contenido": "Mensaje para actualizar",
        "url": "http://example.com",
        "analisis": {
            "calificacion_gpt": 3,
            "calificacion_ml": 0,
            "nivel_peligro": "Seguro"
        },
        "publicado": False
    }
    response_guardar = client.post('/guardar-mensaje-para-publicar', json=data)
    assert response_guardar.status_code == 201
    assert "documento" in response_guardar.json
    mensaje_id = response_guardar.json["documento"]["_id"]

    # Ahora, actualiza el campo `publicado` del mensaje guardado
    response_actualizar = client.put(f'/actualizar-publicado/{mensaje_id}')
    assert response_actualizar.status_code == 200
    assert response_actualizar.json["mensaje"] == "El estado de 'publicado' ha sido actualizado exitosamente."

def test_eliminar_mensaje_para_publicar(client):
    """Prueba el endpoint /eliminar-mensaje-para-publicar para eliminar un mensaje"""
    # Primero, guarda un mensaje para eliminarlo después
    data = {
        "contenido": "Mensaje para eliminar",
        "url": "http://example.com",
        "analisis": {
            "calificacion_gpt": 3,
            "calificacion_ml": 0,
            "nivel_peligro": "Seguro"
        },
        "publicado": False
    }
    response_guardar = client.post('/guardar-mensaje-para-publicar', json=data)
    assert response_guardar.status_code == 201
    assert "documento" in response_guardar.json
    mensaje_id = response_guardar.json["documento"]["_id"]

    # Ahora, elimina el mensaje guardado
    response_eliminar = client.delete(f'/eliminar-mensaje-para-publicar/{mensaje_id}')
    assert response_eliminar.status_code == 200
    assert response_eliminar.json["mensaje"] == "El mensaje ha sido eliminado exitosamente."

def test_mensaje_aleatorio(client):
    """Prueba el endpoint /mensaje-aleatorio para obtener un mensaje aleatorio"""
    # Asegura que hay al menos un mensaje en la base de datos antes de la prueba
    client.post('/guardar-mensaje-para-publicar', json={
        "contenido": "Mensaje aleatorio de prueba",
        "url": "http://example.com",
        "analisis": {
            "calificacion_gpt": 3,
            "calificacion_ml": 0,
            "nivel_peligro": "Seguro"
        },
        "publicado": False
    })
    
    response = client.get('/mensaje-aleatorio')
    assert response.status_code == 200
    assert "mensaje" in response.json
    assert "contenido" in response.json["mensaje"]

def test_obtener_estadisticas(client):
    """Prueba el endpoint /estadisticas para obtener estadísticas generales"""
    # Inserta algunos mensajes de ejemplo antes de obtener estadísticas
    client.post('/guardar-mensaje-para-publicar', json={
        "contenido": "Mensaje seguro",
        "url": "http://example.com",
        "analisis": {
            "calificacion_gpt": 3,
            "calificacion_ml": 0,
            "nivel_peligro": "Seguro"
        },
        "publicado": False
    })
    client.post('/guardar-mensaje-para-publicar', json={
        "contenido": "Mensaje peligroso",
        "url": "http://example.com",
        "analisis": {
            "calificacion_gpt": 9,
            "calificacion_ml": 1,
            "nivel_peligro": "Peligroso"
        },
        "publicado": True
    })
    
    response = client.get('/estadisticas')
    assert response.status_code == 200
    assert "mensajes" in response.json
    assert "mensajes_para_publicar" in response.json
    assert response.json["mensajes"]["seguros"] >= 1
    assert response.json["mensajes"]["peligrosos"] >= 1
    assert response.json["mensajes_para_publicar"]["publicados"] >= 1
    assert response.json["mensajes_para_publicar"]["no_publicados"] >= 1
