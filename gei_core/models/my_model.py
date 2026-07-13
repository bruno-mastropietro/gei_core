from django.db import models

from core.managers.my_manager import MyManager


class MyModel(models.Model):
    """
    Modelo base del cual heredarán todos los modelos del sistema.
    Inyecta automáticamente el manager dinámico.
    """

    objects = MyManager()

    class Meta:
        abstract = True
        ordering = ["id"]
