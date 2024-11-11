# Análisis de Mensajes con Modelo GPT - API en Flask

## Descripción

Este servicio proporciona una API para analizar mensajes y evaluar su potencial de phishing o autenticidad. Utiliza modelos de lenguaje y otros microservicios para identificar amenazas de phishing y verificar la legitimidad de mensajes. Este servicio se conecta a una base de datos MongoDB para almacenar análisis previos y está desplegado en **Render**.

## Endpoints

### 1. `GET /`

#### Descripción
Endpoint básico para verificar que el servicio esté funcionando.

#### Respuesta
```json
"hello, world!"
```

### 2. `GET /ping`

#### Descripción
Endpoint de prueba para verificar la disponibilidad de la API.

#### Respuesta
```json
{
    "message": "pong"
}
```

### 3. `POST /consultar-modelo`

#### Descripción
Analiza un mensaje para identificar si es peligroso, sospechoso o seguro, utilizando varios criterios de seguridad. Este análisis se hace combinando resultados de otros microservicios y modelos.

#### Solicitud
- URL: `/consultar-modelo`
- Método: `POST`
- Body: JSON con los campos `mensaje` y opcionalmente `numero_celular`.

```json
{
    "mensaje": "Texto del mensaje a analizar",
    "numero_celular": "+123456789"
}
```

#### Respuesta
Un JSON que contiene el análisis y puntaje de riesgo del mensaje.

```json
{
    "analisis_gpt": "Conclusión de seguridad del mensaje",
    "analisis_smishguard": "Seguro | Sospechoso | Peligroso",
    "enlace": "URL analizada",
    "resultado_url": "Seguro | Malicioso | Indeterminado",
    "resultado_ml": "No Spam | Spam",
    "mensaje_analizado": "Texto del mensaje",
    "numero_celular": "+123456789",
    "puntaje": 7
}
```

#### Errores
Si el campo `mensaje` está vacío o no se incluye:

```json
{
    "error": "El campo 'mensaje' es obligatorio."
}
```

## Pruebas y Resultados

### Pruebas Unitarias
Se realizaron pruebas unitarias para cada función individual del servicio utilizando pytest. Todas las pruebas unitarias pasaron correctamente, como se muestra en el resultado:

![Resultado de Pruebas Unitarias](tests/Resultado_prueba_unitaria.jpg)

### Pruebas de Integración
Se llevaron a cabo pruebas de integración para verificar la interacción entre múltiples servicios y microservicios. Todas las pruebas de integración también pasaron exitosamente:

![Resultado de Pruebas de Integración](tests/Resultado_prueba_integracion.jpg)

### Pruebas de la API
Las pruebas de la API confirmaron que todos los endpoints funcionan correctamente y responden con el formato JSON esperado:

![Resultado de Pruebas de la API](tests/Resultado_prueba_API.jpg)

### Pruebas de Carga
Se realizaron pruebas de carga utilizando Locust para simular múltiples usuarios concurrentes accediendo a la API. Los resultados mostraron que el servicio puede manejar la carga esperada sin tiempos de respuesta excesivos.

![Resultado de Pruebas de Carga](tests/Prueba_Carga_Back.html)

## Instalación y Ejecución Local

1. Clona el repositorio.

```bash
git clone <URL_del_repositorio>
cd <nombre_del_directorio>
```

2. Instala las dependencias necesarias.

```bash
pip install -r requirements.txt
```

3. Configura las variables de entorno en un archivo `.env` con las credenciales de MongoDB.

4. Ejecuta la aplicación.

```bash
python app.py
```

La API estará disponible en `http://127.0.0.1:5000`.

## Licencia

Este proyecto está licenciado bajo la MIT License.



