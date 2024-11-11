import pytest
import mongomock
from unittest.mock import patch
from app import app

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_db():
    with patch("app.db", mongomock.MongoClient().db) as mocked_db:
        yield mocked_db

def test_ping(client):
    response = client.get('/ping')
    assert response.status_code == 200
    assert response.json == {"message": "pong"}

def test_guardar_mensaje_para_publicar(client, mock_db):
    mock_db['MensajesParaPublicar'].delete_many({})
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
    # No se verifica "documento_id" ya que el servicio no lo devuelve

def test_actualizar_publicado(client, mock_db):
    mock_db['MensajesParaPublicar'].delete_many({})
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
    # Recuperar el ID manualmente de la base de datos simulada
    mensaje_id = mock_db['MensajesParaPublicar'].find_one({"contenido": "Mensaje para actualizar"})["_id"]

    response_actualizar = client.put(f'/actualizar-publicado/{mensaje_id}')
    assert response_actualizar.status_code == 200
    assert response_actualizar.json["mensaje"] == "El estado de 'publicado' ha sido actualizado exitosamente."

def test_eliminar_mensaje_para_publicar(client, mock_db):
    mock_db['MensajesParaPublicar'].delete_many({})
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
    mensaje_id = mock_db['MensajesParaPublicar'].find_one({"contenido": "Mensaje para eliminar"})["_id"]

    response_eliminar = client.delete(f'/eliminar-mensaje-para-publicar/{mensaje_id}')
    assert response_eliminar.status_code == 200
    assert response_eliminar.json["mensaje"] == "El mensaje ha sido eliminado exitosamente."

def test_mensaje_aleatorio(client, mock_db):
    mock_db['Mensajes'].delete_many({})
    mock_db['Mensajes'].insert_one({
        "contenido": "Mensaje aleatorio de prueba",
        "analisis": {"nivel_peligro": "Seguro"}
    })

    response = client.get('/mensaje-aleatorio')
    assert response.status_code == 200
    assert "mensaje" in response.json
    assert response.json["mensaje"]["contenido"] == "Mensaje aleatorio de prueba"

def test_obtener_estadisticas(client, mock_db):
    mock_db['Mensajes'].delete_many({})
    mock_db['MensajesParaPublicar'].delete_many({})

    mock_db['Mensajes'].insert_many([
        {"contenido": "Mensaje seguro", "analisis": {"nivel_peligro": "Seguro"}},
        {"contenido": "Mensaje peligroso", "analisis": {"nivel_peligro": "Peligroso"}}
    ])
    mock_db['MensajesParaPublicar'].insert_many([
        {"contenido": "Publicado", "publicado": True},
        {"contenido": "No Publicado", "publicado": False}
    ])

    response = client.get('/estadisticas')
    assert response.status_code == 200
    assert response.json["mensajes"]["seguros"] == 1
    assert response.json["mensajes"]["peligrosos"] == 1
    assert response.json["mensajes_para_publicar"]["publicados"] == 1
    assert response.json["mensajes_para_publicar"]["no_publicados"] == 1
