import pytest
import mongomock
from unittest.mock import patch
from app import app
from datetime import datetime, timedelta

# Configura el cliente de prueba para la aplicación Flask
@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

# Usa mongomock para simular la base de datos MongoDB
@pytest.fixture
def mock_db():
    with patch("app.db", mongomock.MongoClient().db) as mocked_db:
        yield mocked_db

# Prueba de integración para el flujo completo de guardar y consultar un mensaje
def test_guardar_y_consultar_mensaje(mock_db, client):
    # Paso 1: Guardar un mensaje en la base de datos
    data_guardar = {
        "contenido": "Este es un mensaje de prueba",
        "url": "http://example.com",
        "analisis": {
            "calificacion_gpt": 3,
            "calificacion_ml": 0,
            "nivel_peligro": "Seguro"
        },
        "publicado": False
    }
    response_guardar = client.post("/guardar-mensaje-para-publicar", json=data_guardar)
    assert response_guardar.status_code == 201
    assert response_guardar.json["mensaje"] == "El mensaje reportado se ha guardado exitosamente."

    # Paso 2: Consultar el mensaje recién guardado
    response_consultar = client.get("/mensajes-para-publicar")
    assert response_consultar.status_code == 200
    assert len(response_consultar.json["documentos"]) > 0
    assert response_consultar.json["documentos"][0]["contenido"] == data_guardar["contenido"]

# Prueba de integración para verificar la eliminación de un mensaje
def test_eliminar_mensaje(mock_db, client):
    # Inserta un mensaje en la base de datos simulada
    mensaje_id = mock_db['MensajesParaPublicar'].insert_one({
        "contenido": "Mensaje a eliminar",
        "publicado": False
    }).inserted_id

    # Eliminar el mensaje
    response = client.delete(f"/eliminar-mensaje-para-publicar/{mensaje_id}")
    assert response.status_code == 200
    assert response.json["mensaje"] == "El mensaje ha sido eliminado exitosamente."

    # Verificar que el mensaje no está en la base de datos
    mensaje = mock_db['MensajesParaPublicar'].find_one({"_id": mensaje_id})
    assert mensaje is None

# Prueba de integración para el endpoint de /consultar-modelo
def test_consultar_modelo(mock_db, client):
    # Inserta un mensaje en la base de datos para que sea encontrado
    mock_db['Mensajes'].insert_one({
        "contenido": "Mensaje para analizar",
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
    # Datos de la solicitud para el análisis
    data = {"mensaje": "Mensaje para analizar", "numero_celular": "123456789"}
    
    # Simular una solicitud POST al endpoint /consultar-modelo
    response = client.post("/consultar-modelo", json=data)
    assert response.status_code == 200
    assert response.json["analisis_gpt"] == "Sample GPT analysis"
    assert response.json["analisis_smishguard"] == "Seguro"

# Prueba de integración para simular el almacenamiento de un comentario de soporte
def test_comentario_soporte(mock_db, client):
    data = {"comentario": "Comentario de prueba", "correo": "test@test.com"}
    response = client.post("/comentario-soporte", json=data)
    assert response.status_code == 201
    assert response.json["mensaje"] == "Comentario guardado exitosamente."

    # Verificar que el comentario esté en la base de datos simulada
    comentario = mock_db['ComentariosSoporte'].find_one({"comentario": "Comentario de prueba"})
    assert comentario is not None
    assert comentario["correo"] == "test@test.com"

# Prueba de integración para almacenar y consultar un número bloqueado
def test_numeros_bloqueados(mock_db, client):
    data_bloquear = {"numero": "123456789", "correo": "test@test.com"}
    response_bloquear = client.post('/numeros-bloqueados', json=data_bloquear)
    assert response_bloquear.status_code == 201
    assert response_bloquear.json["mensaje"] == "Número bloqueado guardado exitosamente."

    # Verificar que el número bloqueado esté en la base de datos simulada
    numero_bloqueado = mock_db['NumerosBloqueadosUsuarios'].find_one({"numero": "123456789"})
    assert numero_bloqueado is not None

    # Consultar el número bloqueado
    response_consultar = client.get('/numeros-bloqueados/test@test.com')
    assert response_consultar.status_code == 200
    assert len(response_consultar.json["numeros"]) > 0
    assert response_consultar.json["numeros"][0]["numero"] == "123456789"

# Prueba de integración para el endpoint de mensaje aleatorio
def test_mensaje_aleatorio(mock_db, client):
    # Insertar varios mensajes en la base de datos simulada
    mock_db['Mensajes'].insert_many([
        {"contenido": "Mensaje 1"},
        {"contenido": "Mensaje 2"},
        {"contenido": "Mensaje 3"}
    ])

    # Llamar al endpoint de mensaje aleatorio
    response = client.get("/mensaje-aleatorio")
    assert response.status_code == 200
    assert "mensaje" in response.json
    assert "contenido" in response.json["mensaje"]

# Prueba de integración para el endpoint de estadísticas
def test_obtener_estadisticas(mock_db, client):
    # Insertar datos en la colección Mensajes
    mock_db['Mensajes'].insert_many([
        {"analisis": {"nivel_peligro": "Seguro"}},
        {"analisis": {"nivel_peligro": "Sospechoso"}},
        {"analisis": {"nivel_peligro": "Peligroso"}},
        {"analisis": {"nivel_peligro": "Seguro"}}
    ])
    # Insertar datos en la colección MensajesParaPublicar
    mock_db['MensajesParaPublicar'].insert_many([
        {"publicado": True},
        {"publicado": False}
    ])

    # Llamar al endpoint de estadísticas
    response = client.get("/estadisticas")
    assert response.status_code == 200
    assert "mensajes" in response.json
    assert "mensajes_para_publicar" in response.json
    assert response.json["mensajes"]["seguros"] == 2
    assert response.json["mensajes"]["sospechosos"] == 1
    assert response.json["mensajes"]["peligrosos"] == 1
    assert response.json["mensajes_para_publicar"]["publicados"] == 1
    assert response.json["mensajes_para_publicar"]["no_publicados"] == 1
