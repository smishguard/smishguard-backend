class Analisis:
    def __init__(self, id_analisis, id_mensaje, resultado, detalles):
        self.id_analisis = id_analisis
        self.id_mensaje = id_mensaje
        self.resultado = resultado
        self.detalles = detalles

    def __str__(self):
        return f'Analisis(ID: {self.id_analisis}, ID_Mensaje: {self.id_mensaje}, ID_Analisis: {self.resultado}, Contenido: {self.detalles})'

    def to_dict(self):
        return {
            "id_analisis": self.id_analisis,
            "id_mensaje": self.id_mensaje,
            "resultado": self.resultado,
            "detalles": self.detalles
        }
