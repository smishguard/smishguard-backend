import pytest
from app import app

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_consumir_servicios(client, mocker):
    mocker.patch('requests.post', return_value=MockResponse({'result': 'ok'}, 200))
    mocker.patch('requests.get', return_value=MockResponse({'result': 'ok'}, 200))
    
    response = client.post('/consumir_servicios', json={
        'chatgpt': {'prompt': 'Hello'},
        'ml': {'data': [1, 2, 3]},
        'virustotal': {'file_id': 'example_id'}
    })
    
    assert response.status_code == 200
    assert 'chatgpt' in response.json
    assert 'ml' in response.json
    assert 'virustotal' in response.json

def test_almacenar_datos(client, mocker):
    mocker.patch('firebase_admin.firestore.client')
    response = client.post('/almacenar_datos', json={'example_key': 'example_value'})
    assert response.status_code == 200
    assert 'id' in response.json

def test_consumir_twitter(client, mocker):
    mocker.patch('requests.get', return_value=MockResponse({'result': 'ok'}, 200))
    response = client.get('/consumir_twitter')
    assert response.status_code == 200
    assert 'result' in response.json

class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data
