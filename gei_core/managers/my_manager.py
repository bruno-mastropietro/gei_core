from django.db import models

from gei_core.utils.api_utils import apply_includes_to_queryset


class DynamicIncludeQuerySet(models.QuerySet):
    def with_includes(self, includes: list, joins_map: dict):
        if joins_map:
            return apply_includes_to_queryset(self, includes, joins_map)
        return self

    def get_missing_ids(self, ids_list):
        ids_unicos = set(ids_list)
        ids_existentes = set(self.filter(id__in=ids_unicos).values_list("id", flat=True))

        return list(ids_unicos - ids_existentes)


class MyManager(models.Manager):
    def get_queryset(self):
        return DynamicIncludeQuerySet(self.model, using=self._db)

    def with_includes(self, includes: list, joins_map: dict):
        return self.get_queryset().with_includes(includes, joins_map)

    def get_all(self, *, includes: list = None, joins_map: dict = None):
        return self.get_queryset().with_includes(includes, joins_map)

    def get_missing_ids(self, ids_list):
        return self.get_queryset().get_missing_ids(ids_list)
