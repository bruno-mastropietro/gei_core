import re
from types import SimpleNamespace

from django.db.models import CharField, F, Q, Value
from django.db.models.functions import Concat, Replace
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.decorators.datatable import datatable
from core.decorators.my_api_view import my_api_view
from core.utils.debug_helper import lq, lqs2
from core.utils.queryset_filters import queryset_filters


def my_views(service_class, serializer_class, create_serializer, update_serializer, pk_name):
    """
    Fábrica de vistas funcionales. Genera el CRUD estándar y un listado de datatable para cualquier entidad
    basándose en el MyService y los serializers proporcionados.
    """

    @my_api_view(["POST"], serializer_class=serializer_class)
    def get_all(request, includes, joins_map):
        queryset = service_class.get_all(includes=includes, joins_map=joins_map)
        filtered_queryset = queryset_filters(queryset, request.data, joins_map)
        return filtered_queryset

    @my_api_view(["POST"], serializer_class=serializer_class)
    @datatable
    def get_datatable(request, includes, joins_map):
        return service_class.get_all(includes=includes, joins_map=joins_map)

    @my_api_view(["GET"], serializer_class=serializer_class)
    def get_one(request, includes, joins_map, **kwargs):
        pk = kwargs.get(pk_name)
        return service_class.get_one(pk=pk, includes=includes, joins_map=joins_map)

    @my_api_view(["POST"])
    def post_one(request, includes, joins_map):
        serializer = create_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = service_class.create_one(**serializer.validated_data)

        data = serializer_class(instance, context={"includes": includes}).data
        return Response(data, status=status.HTTP_201_CREATED)

    @my_api_view(["PUT", "PATCH"])
    def put_one(request, includes, joins_map, **kwargs):
        pk = kwargs.get(pk_name)
        serializer = update_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        instance = service_class.update_one(pk=pk, **serializer.validated_data)
        data = serializer_class(instance, context={"includes": includes}).data
        return Response(data, status=status.HTTP_200_OK)

    @my_api_view(["DELETE"])
    def delete_one(request, includes, joins_map, **kwargs):
        pk = kwargs.get(pk_name)
        service_class.delete_one(pk=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @api_view(["GET"])
    def get_schema(request):
        """
        Devuelve la estructura de los campos para que el Frontend dibuje el formulario.
        """
        serializer_instance = create_serializer()
        campos_frontend = {}
        for nombre_campo, campo in serializer_instance.fields.items():
            campos_frontend[nombre_campo] = {
                "type": campo.__class__.__name__,
                "required": campo.required,
                "read_only": campo.read_only,
                "allow_null": getattr(campo, "allow_null", False),
                "max_length": getattr(campo, "max_length", None),
            }
        return Response({"entidad": service_class.model.__name__.replace("Model", ""), "campos": campos_frontend})

    @api_view(["GET"])
    def get_array_control(request):
        fields_param = request.GET.get("fields", "id:descripcion")
        separator = request.GET.get("separator", request.GET.get("separetor", " "))

        # 1. Separamos el "key" de los "values"
        if ":" in fields_param:
            key_field, val_fields_str = fields_param.split(":", 1)
            value_fields = [f.strip() for f in val_fields_str.split(",") if f.strip()]
        else:
            key_field = "id"
            value_fields = [f.strip() for f in fields_param.split(",") if f.strip() and f.strip() != "id"]

        key_field = key_field.strip()

        # Obtener campos válidos base del modelo
        valid_fields = [f.name for f in service_class.model._meta.get_fields()]

        # NUEVO VALIDADOR DE PUNTOS: Acepta campos directos o relaciones válidas (ej: carrera.descripcion)
        def es_campo_valido(campo):
            clean_field = campo.lstrip("-")  # Por si viene de un sort futuro
            if "." in clean_field:
                partes = clean_field.split(".")
                # Verifica si el primer eslabón de la cadena (ej: 'carrera') es una relación válida
                return partes[0] in valid_fields
            return clean_field in valid_fields

        safe_key = key_field if es_campo_valido(key_field) else "id"
        safe_value_fields = [f for f in value_fields if es_campo_valido(f)]

        if not safe_value_fields:
            safe_value_fields = ["descripcion"] if "descripcion" in valid_fields else [valid_fields[1]]

        # Campos que le vamos a pedir al .values() reemplazando puntos por guiones bajos
        fetch_fields = [safe_key.replace(".", "__")] + [f.replace(".", "__") for f in safe_value_fields]

        queryset = service_class.model.objects.all()

        # Si detectamos que piden algo con puntos (ej: 'carrera.descripcion'),
        # le metemos un select_related('carrera') automático para que la BD haga el JOIN
        relaciones_a_cargar = set()
        for f in [safe_key] + safe_value_fields:
            if "." in f:
                # Si es 'carrera.nivel.descripcion', se convierte en 'carrera__nivel'
                relaciones_a_cargar.add("__".join(f.split(".")[:-1]))

        if relaciones_a_cargar:
            queryset = queryset.select_related(*relaciones_a_cargar)

        filter_data = {}
        where_dict = {}

        for w in request.GET.getlist("where"):
            if "=" in w:
                campo, valor = w.split("=", 1)
                where_dict[campo.strip()] = valor.strip().rstrip("/")

        for w_in in request.GET.getlist("where_in"):
            if "=" in w_in:
                campo, valores_str = w_in.split("=", 1)
                valores_str_limpio = valores_str.strip().rstrip("/")
                lista_valores = [v.strip() for v in valores_str_limpio.split(",") if v.strip()]
                where_dict[campo.strip()] = lista_valores

        if where_dict:
            filter_data["where"] = where_dict
            queryset = queryset_filters(queryset, filter_data)

        # HELPER MODIFICADO: Ahora busca las llaves con '__' que devolvió el .values()
        def transform_item(item):
            key_orm = safe_key.replace(".", "__")
            str_valores = []
            for f in safe_value_fields:
                f_orm = f.replace(".", "__")
                if item.get(f_orm) is not None:
                    str_valores.append(str(item[f_orm]))

            return {"key": item.get(key_orm), "value": separator.join(str_valores)}

        # --- MODO BÚSQUEDA Q ---
        q = request.GET.get("q")
        search_field = request.GET.get("search_field", ",".join(safe_value_fields))

        if q:
            clean_q = re.sub(r"[\s/\-]", "", q)
            search_fields_list = [f.strip() for f in search_field.split(",")]
            safe_search_fields = [f for f in search_fields_list if es_campo_valido(f)]

            if safe_search_fields:
                if len(safe_search_fields) == 1:
                    base_expr = F(safe_search_fields[0].replace(".", "__"))
                else:
                    concat_args = []
                    for i, f_name in enumerate(safe_search_fields):
                        concat_args.append(F(f_name.replace(".", "__")))
                        if i < len(safe_search_fields) - 1:
                            concat_args.append(Value(separator))
                    base_expr = Concat(*concat_args, output_field=CharField())

                cleaned_expr = Replace(base_expr, Value(" "), Value(""))
                cleaned_expr = Replace(cleaned_expr, Value("/"), Value(""))
                cleaned_expr = Replace(cleaned_expr, Value("-"), Value(""))
                cleaned_expr = Replace(cleaned_expr, Value("."), Value(""))
                cleaned_expr = Replace(cleaned_expr, Value(","), Value(""))
                cleaned_expr = Replace(cleaned_expr, Value(":"), Value(""))
                cleaned_expr = Replace(cleaned_expr, Value("º"), Value(""))
                cleaned_expr = Replace(cleaned_expr, Value("_"), Value(""))

                queryset = queryset.annotate(_search_clean=cleaned_expr).filter(_search_clean__icontains=clean_q)

        # --- LÍMITE Y EXTRACCIÓN ---
        try:
            limit = int(request.GET.get("limit", 50))
        except ValueError:
            limit = 50

        raw_data = list(queryset.values(*fetch_fields).order_by().distinct()[:limit])
        data = [transform_item(item) for item in raw_data]

        # --- PINNED_ID ---
        pinned_id = request.GET.get("pinned_id")
        if pinned_id:
            try:
                elemento_existente = next((item for item in data if str(item.get("key")) == str(pinned_id)), None)
                if elemento_existente:
                    data.remove(elemento_existente)
                    data.insert(0, elemento_existente)
                else:
                    pinned_raw = service_class.model.objects.filter(id=pinned_id).values(*fetch_fields).first()
                    if pinned_raw:
                        data.insert(0, transform_item(pinned_raw))
            except ValueError:
                pass

        return Response(data)

    return SimpleNamespace(
        get_all=get_all,
        get_datatable=get_datatable,
        get_one=get_one,
        post_one=post_one,
        put_one=put_one,
        delete_one=delete_one,
        get_schema=get_schema,
        get_array_control=get_array_control,
    )
