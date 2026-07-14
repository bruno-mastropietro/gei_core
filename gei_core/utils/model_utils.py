import importlib
import re
from typing import Any, Type, TYPE_CHECKING

from django.apps import apps

if TYPE_CHECKING:
    from gei_core.models.my_model import MyModel

def load_model(model_name: str, app_label: str) -> Type['MyModel']:
    """
    Carga un modelo de Django dinámicamente para evitar importaciones circulares.
    Uso: load_model('EscuelaModel') o load_model('EscuelaModel', 'otra_app')
    """
    return apps.get_model(app_label, model_name)

def _camel_to_snake(name: str) -> str:
    """Convierte de CamelCase a snake_case (ej: SupervisionService -> supervision_service)"""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def load_service(service_name: str, app_label: str) -> Type[Any]:
    """
    Carga un Service dinámicamente infiriendo su ruta.

    Uso:
    SupervisionService = load_service('SupervisionService', 'escuela')
    """
    # 1. Inferimos el nombre del archivo
    module_name = _camel_to_snake(service_name)

    # 2. Armamos la ruta del import basándonos en tu estructura
    # Si tus apps no están dentro de una carpeta "apps", quita el "apps." del string.
    module_path = f"apps.{app_label}.services.{module_name}"

    # 3. Importamos y devolvemos la clase
    module = importlib.import_module(module_path)
    return getattr(module, service_name)
