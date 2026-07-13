from functools import wraps

from django.db.models import QuerySet
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.utils.api_utils import parse_includes


def my_api_view(methods, serializer_class=None):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # 1. Inyectamos dependencias
            includes = parse_includes(request)
            joins_map = serializer_class.get_joins() if serializer_class else {}

            kwargs["includes"] = includes
            kwargs["joins_map"] = joins_map

            # 2. Ejecutamos la vista
            result = func(request, *args, **kwargs)

            # La vista devolvió un Response manual (Ej: 201 Created)
            if isinstance(result, Response):
                return result

            # --- ARMAMOS EL CONTEXTO UNA SOLA VEZ ---
            # Le pasamos el request al serializador para que pueda leer body, headers, etc.
            serializer_context = {
                "includes": includes,
                "joins_map": joins_map,
                "request": request,
            }

            # CASO A: Es un resultado de Datatable (Tupla: QuerySet paginado + Paginador)
            if isinstance(result, tuple) and len(result) == 2 and hasattr(result[1], "get_paginated_response"):
                paginated_qs, paginator = result
                data = serializer_class(paginated_qs, many=True, context=serializer_context).data
                return paginator.get_paginated_response(data)

            # CASO B: Es un resultado estándar (Un objeto o una lista)
            if serializer_class:
                # Si es una lista o un QuerySet, many=True. Si es uno solo, many=False.
                is_many = isinstance(result, (list, QuerySet))
                data = serializer_class(result, many=is_many, context=serializer_context).data
                return Response(data)

            # CASO C: Fallback puro
            return Response(result)

        return api_view(methods)(wrapper)

    return decorator
