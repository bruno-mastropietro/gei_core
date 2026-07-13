from django.utils.module_loading import import_string
from rest_framework import serializers


class MySerializer(serializers.ModelSerializer):
    """
    Serializer genérico para expansiones explícitas y estrictas.
    Soporta saltarse niveles intermedios si el usuario no los pidió.
    """

    @property
    def default_joins(self):
        """
        Formato:
        {
            'palabra_url': ('campo_id_a_borrar_si_existe', ClaseSerializer, 'camino__orm__django', es_prefetch:bool)
        }
        """
        return {}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        includes = self.context.get("includes", [])

        for include_name, config in self.default_joins.items():

            if len(config) == 4:
                id_field, serializer_class, orm_path, is_prefetch = config
            else:
                id_field, serializer_class, orm_path = config
                is_prefetch = False

            if include_name in includes:

                if id_field:
                    data.pop(id_field, None)

                current_obj = instance
                for attr in orm_path.split("__"):
                    if current_obj:
                        current_obj = getattr(current_obj, attr, None)

                if current_obj is not None:
                    if isinstance(serializer_class, str):
                        serializer_class = import_string(serializer_class)

                    nested_context = self.context.copy()
                    prefix = f"{include_name}__"
                    nested_context["includes"] = [inc[len(prefix) :] for inc in includes if inc.startswith(prefix)]

                    # Si el objeto resultante es un Manager (ej: edificio.escuelas),
                    # tenemos que llamar a .all() y pasarle many=True al serializador
                    if hasattr(current_obj, "all"):
                        data[include_name] = serializer_class(current_obj.all(), many=True, context=nested_context).data
                    else:
                        data[include_name] = serializer_class(current_obj, context=nested_context).data
                else:
                    data[include_name] = None

        request = self.context.get("request")
        if request and hasattr(request, "data"):
            concats = request.data.get("concats", {})
            if isinstance(concats, dict):
                for alias in concats.keys():
                    if hasattr(instance, alias):
                        data[alias] = getattr(instance, alias, None)

        return data

    @classmethod
    def get_joins(cls) -> dict:
        """
        Extrae el diccionario { 'palabra_url': ('camino__orm', is_prefetch) }
        para que apply_includes_to_queryset sepa cómo optimizar.
        """
        dummy_instance = cls()
        joins_dict = {}
        for include_name, config in dummy_instance.default_joins.items():
            # Desempaquetamos de forma segura (soporta 3 o 4 elementos)
            if len(config) == 4:
                _, _, orm_path, is_prefetch = config
            else:
                _, _, orm_path = config
                is_prefetch = False  # Por defecto asumimos ForeignKey normal

            joins_dict[include_name] = (orm_path, is_prefetch)

        return joins_dict


class JsonfieldHandler:
    """
    Intercepta los datos planos (x_data.dato) y los anida
    antes de la validación.
    """

    def to_internal_value(self, data):
        datos_crudos = data.dict() if hasattr(data, "dict") else data

        datos_expandidos = {}
        for llave, valor in datos_crudos.items():
            if "." in llave:
                padre, hijo = llave.split(".", 1)
                if padre not in datos_expandidos:
                    datos_expandidos[padre] = {}
                datos_expandidos[padre][hijo] = valor
            else:
                datos_expandidos[llave] = valor

        return super().to_internal_value(datos_expandidos)
