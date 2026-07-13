# core/utils/url_helpers.py
from django.urls import path


def generar_urls(view_module, pk_name):
    """
    Toma un módulo de vistas generado por 'my_views' y devuelve
    la lista de paths estándar de Django.
    """
    return [
        path("listar/", view_module.get_all),
        path("listar_datatable/", view_module.get_datatable),
        path("crear/", view_module.post_one),
        path(f"ver/<int:{pk_name}>/", view_module.get_one),
        path(f"editar/<int:{pk_name}>/", view_module.put_one),
        path(f"eliminar/<int:{pk_name}>/", view_module.delete_one),
        path("array_control/", view_module.get_array_control),
    ]
