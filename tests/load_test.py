from locust import HttpUser, TaskSet, task, between

class UserBehavior(TaskSet):
    
    @task(1)
    def ping(self):
        self.client.get("/ping")
    
    @task(3)
    def consultar_modelo(self):
        data = {
            "mensaje": "Este es un mensaje de prueba",
            "numero_celular": "123456789"
        }
        self.client.post("/consultar-modelo", json=data)
    
    @task(2)
    def guardar_mensaje_para_publicar(self):
        data = {
            "contenido": "Contenido de prueba",
            "url": "http://example.com",
            "analisis": {
                "calificacion_gpt": 3,
                "calificacion_ml": 0,
                "nivel_peligro": "Seguro"
            },
            "publicado": False
        }
        self.client.post("/guardar-mensaje-para-publicar", json=data)

    @task(2)
    def obtener_mensajes_para_publicar(self):
        self.client.get("/mensajes-para-publicar")
    
    @task(1)
    def publicar_tweet(self):
        data = {
            "mensaje": "Este es un tweet de prueba sin enlace"
        }
        self.client.post("/publicar-tweet", json=data)

    @task(1)
    def mensaje_aleatorio(self):
        self.client.get("/mensaje-aleatorio")

    @task(1)
    def obtener_estadisticas(self):
        self.client.get("/estadisticas")

class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 3)  # Espera entre 1 y 3 segundos entre cada tarea
