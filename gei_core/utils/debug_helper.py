from pprint import pprint

from django.db.models import ForeignKey, ManyToManyField, OneToOneField
from django.forms.models import model_to_dict


def lq(queryset):
    print(queryset.query)


def lqs(queryset):
    pprint(list(queryset.values()), sort_dicts=False)


def lqs2(queryset):
    # Convierte un queryset a una lista de diccionarios, incluyendo los campos relacionados.
    lista = [get_all_fields_and_related_values(obj) for obj in queryset]
    pprint(
        lista,
        indent=2,
        sort_dicts=False,
    )


def lqs3(queryset):
    data = serialize_queryset(queryset)
    pprint(data, sort_dicts=False, indent=2, width=500)


def get_all_fields_and_related_values(instance):
    # Devuelve un diccionario con todos los campos y sus valores,
    # incluyendo los campos relacionados (ForeignKey, OneToOneField, ManyToManyField).

    data = model_to_dict(instance, fields=[field.name for field in instance._meta.fields])

    # AÃ±adir los campos relacionados
    for field in instance._meta.get_fields():
        if isinstance(field, ForeignKey) or isinstance(field, OneToOneField):
            related_instance = getattr(instance, field.name, None)
            if related_instance:
                data[f"{field.name}_id"] = related_instance.id
                data[field.name] = str(related_instance)
        elif isinstance(field, ManyToManyField):
            related_instances = getattr(instance, field.name).all()
            data[field.name] = [str(related_instance) for related_instance in related_instances]

    return data


def serialize_queryset(queryset):
    # Serializa un queryset, incluyendo las relaciones de cada instancia.
    return [serialize_instance(instance) for instance in queryset]


def serialize_instance(instance):
    # Serializa una instancia de un modelo, incluyendo sus relaciones.
    data = model_to_dict(instance, fields=[field.name for field in instance._meta.fields])

    for field in instance._meta.get_fields():
        if isinstance(field, ForeignKey) or isinstance(field, OneToOneField):
            related_instance = getattr(instance, field.name, None)
            if related_instance:
                data[field.name] = serialize_instance(related_instance)
        elif isinstance(field, ManyToManyField):
            related_instances = getattr(instance, field.name).all()
            data[field.name] = [serialize_instance(related_instance) for related_instance in related_instances]

    return data
