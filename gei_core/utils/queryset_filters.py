from django.db.models import CharField, F, Q, Value
from django.db.models.functions import Concat


def queryset_filters(queryset, data, joins_map=None):
    """
    Aplica la lógica de concats, where, where_or, search y sort al queryset.
    Devuelve el queryset filtrado sin paginar.
    """
    concats = data.get("concats", {})
    joins_map = joins_map or {}

    def resolver_ruta_orm(campo):
        if isinstance(concats, dict) and campo in concats:
            return campo
        if "." in campo:
            entidad, atributo = campo.split(".", 1)
            if entidad in joins_map:
                mapping = joins_map[entidad]
                orm_path = mapping[0] if isinstance(mapping, tuple) else mapping
                return f"{orm_path}__{atributo}"
            return campo.replace(".", "__")
        return campo

    # --- 1. CONCATS ---
    if isinstance(concats, dict) and concats:
        for alias, config in concats.items():
            fields = config.get("fields", [])
            separator = config.get("separator", "")
            if not fields:
                continue

            concat_args = []
            for i, f_name in enumerate(fields):
                orm_path_original = f_name
                if "." in f_name:
                    entidad, atributo = f_name.split(".", 1)
                    if entidad in joins_map:
                        mapping = joins_map[entidad]
                        m_path = mapping[0] if isinstance(mapping, tuple) else mapping
                        orm_path_original = f"{m_path}__{atributo}"
                    else:
                        orm_path_original = f_name.replace(".", "__")

                concat_args.append(F(orm_path_original))
                if i < len(fields) - 1:
                    concat_args.append(Value(separator))

            queryset = queryset.annotate(**{alias: Concat(*concat_args, output_field=CharField())})

    # --- 2. FILTROS EXACTOS (WHERE) ---
    where_params = data.get("where", {})
    if isinstance(where_params, dict) and where_params:
        django_where_filters = {}
        for campo, valor in where_params.items():
            if valor is None or valor == "" or (isinstance(valor, (list, tuple)) and len(valor) == 0):
                continue
            campo_django = resolver_ruta_orm(campo)
            if isinstance(valor, (list, tuple)):
                django_where_filters[f"{campo_django}__in"] = valor
            else:
                django_where_filters[campo_django] = valor
        if django_where_filters:
            queryset = queryset.filter(**django_where_filters)

    # --- 3. FILTROS CONDICIONALES OR ---
    where_or_params = data.get("where_or", {})
    if isinstance(where_or_params, dict) and where_or_params:
        django_or_filters = Q()
        has_or_filters = False
        for campo, valor in where_or_params.items():
            if valor is None or valor == "" or (isinstance(valor, (list, tuple)) and len(valor) == 0):
                continue
            campo_django = resolver_ruta_orm(campo)
            if isinstance(valor, (list, tuple)):
                condicion = Q(**{f"{campo_django}__in": valor})
            else:
                condicion = Q(**{campo_django: valor})

            if not has_or_filters:
                django_or_filters = condicion
                has_or_filters = True
            else:
                django_or_filters |= condicion
        if has_or_filters:
            queryset = queryset.filter(django_or_filters)

    # --- 4. BÚSQUEDAS TIPO LIKE ---
    search_params = data.get("searchParams", {})
    if isinstance(search_params, dict) and search_params:
        django_filters = {}
        for campo, valor in search_params.items():
            if valor is not None and valor != "":
                campo_django = resolver_ruta_orm(campo)
                django_filters[f"{campo_django}__icontains"] = valor
        if django_filters:
            queryset = queryset.filter(**django_filters)

    # --- 5. ORDENAMIENTO ---
    sort_params = data.get("sort")
    if sort_params:
        sort_list = [sort_params] if isinstance(sort_params, str) else sort_params
        translated_sort = []
        for sort_field in sort_list:
            prefix = "-" if sort_field.startswith("-") else ""
            clean_field = sort_field.lstrip("-")
            campo_django = resolver_ruta_orm(clean_field)
            translated_sort.append(f"{prefix}{campo_django}")
        if translated_sort:
            queryset = queryset.order_by(*translated_sort)

    return queryset
