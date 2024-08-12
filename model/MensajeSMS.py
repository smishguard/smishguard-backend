class MensajeSMS:
    def __init__(self, id_mensaje, contenido, fechaHora, remitente):
        self.id_mensaje = id_mensaje
        self.contenido = contenido
        self.fechaHora = fechaHora
        self.remitente = remitente

    def __str__(self):
        return f'MensajeSMS(ID: {self.id_mensaje}, Contendio: {self.contenido}, fechaHora: {self.fechaHora}, Remitente: {self.remitente})'

    def to_dict(self):
        return {
            "id_mensaje": self.id_mensaje,
            "contenido": self.contenido,
            "fechaHora": self.fechaHora.isoformat(),
            "remitente": self.remitente
        }
