import pytest
import mongomock
from app import app
from unittest.mock import patch, MagicMock
import asyncio
from datetime import datetime, timedelta


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_db():
    with patch("app.db", mongomock.MongoClient().db) as mocked_db:
        yield mocked_db

@pytest.mark.asyncio
async def test_hello_world(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.data.decode() == 'hello, world!'

@pytest.mark.asyncio
async def test_ping(client):
    response = client.get('/ping')
    assert response.status_code == 200
    assert response.json == {"message": "pong"}

@pytest.mark.asyncio
async def test_consultar_modelo(mock_db, client):
    mock_db['Mensajes'].insert_one({
        "contenido": "test message",
        "numero_celular": "123456789",
        "analisis": {
            "fecha_analisis": (datetime.utcnow() - timedelta(days=20)).isoformat() + 'Z',
            "justificacion_gpt": "Sample GPT analysis",
            "nivel_peligro": "Seguro",
            "resultado_url": "Seguro",
            "resultado_ml": "No Spam",
            "ponderado": 5
        },
        "url": "http://example.com"
    })
    data = {"mensaje": "test message", "numero_celular": "123456789"}
    
    response = await client.post('/consultar-modelo', json=data)
    assert response.status_code == 200
    assert "analisis_gpt" in response.json

@pytest.mark.asyncio
async def test_mensajes_para_publicar(mock_db, client):
    mock_db['MensajesParaPublicar'].insert_one({"contenido": "test message", "publicado": False})
    response = client.get('/mensajes-para-publicar')
    assert response.status_code == 200
    assert "documentos" in response.json

def test_guardar_mensaje_para_publicar(mock_db, client):
    data = {
        "contenido": "Nuevo mensaje",
        "url": "http://test.com",
        "analisis": {"nivel_peligro": "Seguro"},
        "publicado": False
    }
    response = client.post('/guardar-mensaje-para-publicar', json=data)
    assert response.status_code == 201
    assert response.json["mensaje"] == "El mensaje reportado se ha guardado exitosamente."

def test_actualizar_publicado(mock_db, client):
    mensaje_id = mock_db['MensajesParaPublicar'].insert_one({"contenido": "test", "publicado": False}).inserted_id
    response = client.put(f'/actualizar-publicado/{mensaje_id}')
    assert response.status_code == 200
    assert response.json["mensaje"] == "El estado de 'publicado' ha sido actualizado exitosamente."

def test_eliminar_mensaje(mock_db, client):
    mensaje_id = mock_db['MensajesParaPublicar'].insert_one({"contenido": "test"}).inserted_id
    response = client.delete(f'/eliminar-mensaje-para-publicar/{mensaje_id}')
    assert response.status_code == 200
    assert response.json["mensaje"] == "El mensaje ha sido eliminado exitosamente."

def test_comentario_soporte(mock_db, client):
    data = {"comentario": "Test comentario", "correo": "test@test.com"}
    response = client.post('/comentario-soporte', json=data)
    assert response.status_code == 201
    assert response.json["mensaje"] == "Comentario guardado exitosamente."

def test_obtener_todos_comentarios_soporte(mock_db, client):
    mock_db['ComentariosSoporte'].insert_one({"comentario": "test", "correo": "test@test.com"})
    response = client.get('/comentario-soporte')
    assert response.status_code == 200
    assert "comentarios" in response.json

def test_eliminar_comentario(mock_db, client):
    comentario_id = mock_db['ComentariosSoporte'].insert_one({"comentario": "test"}).inserted_id
    response = client.delete(f'/eliminar-comentario-soporte/{comentario_id}')
    assert response.status_code == 200
    assert response.json["mensaje"] == "El comentario ha sido eliminado exitosamente."

def test_numeros_bloqueados(mock_db, client):
    data = {"numero": "123456789", "correo": "test@test.com"}
    response = client.post('/numeros-bloqueados', json=data)
    assert response.status_code == 201
    assert response.json["mensaje"] == "Número bloqueado guardado exitosamente."

def test_obtener_numeros_bloqueados(mock_db, client):
    mock_db['NumerosBloqueadosUsuarios'].insert_one({"numero": "123456789", "correo": "test@test.com"})
    response = client.get('/numeros-bloqueados/test@test.com')
    assert response.status_code == 200
    assert "numeros" in response.json

def test_eliminar_numero_bloqueado(mock_db, client):
    mock_db['NumerosBloqueadosUsuarios'].insert_one({"numero": "123456789", "correo": "test@test.com"})
    response = client.delete('/numeros-bloqueados/test@test.com/123456789')
    assert response.status_code == 200
    assert response.json["mensaje"] == "Número bloqueado eliminado exitosamente."
