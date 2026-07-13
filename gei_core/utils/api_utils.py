def parse_includes(request) -> list:
    """
    Extrae el parámetro include soportando tanto comas como variables repetidas.
    Soporta: ?include=a,b y también ?include=a&include=b
    """
    # getlist atrapa todos los ?include= de la URL y los mete en una lista.
    includes_raw = request.GET.getlist("include")

    parsed_includes = []
    for item in includes_raw:
        # Por si el item vino con comas (ej: "localidad,departamento"), lo dividimos
        parsed_includes.extend([i.strip().lower() for i in item.split(",") if i.strip()])

    # Usamos set() y list() para eliminar duplicados por si el frontend mandó lo mismo dos veces
    return list(set(parsed_includes))


def apply_includes_to_queryset(queryset, includes: list, rel_map: dict):
    """
    Aplica select_related o prefetch_related al queryset
    basado en la configuración del diccionario rel_map.
    """
    if not includes or not rel_map:
        return queryset

    selects = []
    prefetches = []

    for inc in includes:
        if inc in rel_map:
            orm_path, is_prefetch = rel_map[inc]
            if is_prefetch:
                prefetches.append(orm_path)
            else:
                selects.append(orm_path)

    if selects:
        queryset = queryset.select_related(*selects)
    if prefetches:
        queryset = queryset.prefetch_related(*prefetches)

    return queryset
