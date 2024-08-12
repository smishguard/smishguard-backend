class Alerta:
    def __init__(self, id_tweet, id_mensaje, id_analisis, contenido, fechaHora):
        self.id_tweet = id_tweet
        self.id_mensaje = id_mensaje
        self.id_analisis = id_analisis
        self.contenido = contenido
        self.fechaHora = fechaHora

    def __str__(self):
        return f'Alerta(ID: {self.id_tweet}, ID_Mensaje: {self.id_mensaje}, ID_Analisis: {self.id_analisis}, Contenido: {self.contenido}, fechaHora: {self.fechaHora}, Remitente: {self.remitente})'

    def to_dict(self):
        return {
            "id_mensaje": self.id_tweet,
            "id_mensaje": self.id_mensaje,
            "id_analisis": self.id_analisis,
            "contenido": self.contenido,
            "fechaHora": self.fechaHora.isoformat()
        }
