import importlib
from functools import lru_cache

from django.conf import settings
from django.core.cache import cache
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response


@lru_cache(maxsize=None)
def obtener_serializer_por_convencion(entidad):
    """
    Busca dinámicamente la clase 'Create' en todas las apps.
    Ej: Si entidad="carrera", buscará en apps.*.serializers.carrera_serializer.Create
    """
    entidad_limpia = entidad.lower()

    nuestras_apps = [app for app in settings.INSTALLED_APPS if app.startswith("apps.")]
    for app in nuestras_apps:
        module_path = f"{app}.serializers.{entidad_limpia}_serializer"
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, "Create"):
                return module.Create
        except ModuleNotFoundError:
            continue
    return None


def extraer_esquema_serializador(serializer_instance):
    """
    Función recursiva que mapea los campos de un serializador.
    Si encuentra un sub-serializador, se mete adentro para extraer sus campos.
    """
    campos_frontend = {}
    for nombre_campo, campo in serializer_instance.fields.items():
        info_campo = {
            "type": campo.__class__.__name__,
            "required": campo.required,
            "read_only": campo.read_only,
            "max_length": getattr(campo, "max_length", None),
        }

        if hasattr(campo, "choices"):
            info_campo["choices"] = [{"value": valor, "label": etiqueta} for valor, etiqueta in campo.choices.items()]

        if isinstance(campo, serializers.Serializer):
            info_campo["type"] = "NestedSerializer"
            info_campo["nested_fields"] = extraer_esquema_serializador(campo)

        campos_frontend[nombre_campo] = info_campo

    return campos_frontend


@api_view(["GET"])
def get_global_schema(request, entidad):
    """
    Devuelve la estructura de los campos para el Frontend.
    Usa caché para evitar recalcular la estructura en cada recarga de página.
    """
    cache_key = f"{entidad}_esquema"
    esquema_guardado = cache.get(cache_key)
    if esquema_guardado:
        return Response(esquema_guardado)

    serializer_class = obtener_serializer_por_convencion(entidad)
    if not serializer_class:
        return Response({"error": f"Entidad '{entidad}' no encontrada o no tiene un serializer válido."}, status=404)

    serializer_instance = serializer_class()
    campos_frontend = extraer_esquema_serializador(serializer_instance)

    respuesta_final = {"entidad": entidad.capitalize(), "campos": campos_frontend}

    cache.set(cache_key, respuesta_final, timeout=86400)

    return Response(respuesta_final)
