from django.db import IntegrityError, transaction
from django.db.models import UniqueConstraint
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError


class MyService:
    """
    Servicio genérico del cual deben heredar todos los servicios de la app.
    Requiere que las clases hijas definan el atributo `model`.
    """

    model = None

    @classmethod
    def _handle_integrity_error(cls, error: IntegrityError):
        error_msg = str(error)

        if cls.model:
            # Buscamos en las restricciones complejas (UniqueConstraint de la clase Meta)
            for constraint in cls.model._meta.constraints:
                if isinstance(constraint, UniqueConstraint) and constraint.name in error_msg:
                    raise ValidationError({"error": f"Ya existe un registro con esta combinación de datos ({', '.join(constraint.fields)})."})

            # Buscamos en los campos simples con unique=True
            for field in cls.model._meta.fields:
                if getattr(field, "unique", False):
                    if f"Key ({field.column})=" in error_msg or f"{cls.model._meta.db_table}_{field.column}_key" in error_msg:
                        raise ValidationError({"error": f"Ya existe un registro con este valor ({field.name})."})

        # Si no reconoció ni constraint complejo ni campo único, deja que suba el error 500
        raise error

    @classmethod
    def get_all(cls, *, includes: list = None, joins_map: dict = None):
        if not cls.model:
            raise ValueError("El servicio hijo debe definir un atributo 'model'.")
        return cls.model.objects.get_all(includes=includes, joins_map=joins_map)

    @classmethod
    def get_one(cls, pk: int, *, includes: list = None, joins_map: dict = None):
        queryset = cls.get_all(includes=includes, joins_map=joins_map)
        return get_object_or_404(queryset, pk=pk)

    @classmethod
    @transaction.atomic
    def create_one(cls, **kwargs):
        try:
            return cls.model.objects.create(**kwargs)
        except IntegrityError as e:
            cls._handle_integrity_error(e)

    @classmethod
    @transaction.atomic
    def update_one(cls, pk: int, **kwargs):
        instance = cls.get_one(pk=pk)

        for attr, value in kwargs.items():
            setattr(instance, attr, value)

        try:
            instance.save()
            return instance
        except IntegrityError as e:
            cls._handle_integrity_error(e)

    @classmethod
    def delete_one(cls, pk: int):
        instance = cls.get_one(pk=pk)
        instance.delete()
        return True
