from functools import wraps

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from gei_core.utils.queryset_filters import queryset_filters


class LimitPagePagination(PageNumberPagination):
    page_query_param = "page"
    page_size_query_param = "limit"
    page_size = 20
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )


def datatable(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        joins_map = kwargs.get("joins_map", {})
        queryset = func(request, *args, **kwargs)
        if isinstance(queryset, Response):
            return queryset

        queryset = queryset_filters(queryset, request.data, joins_map)

        paginator = LimitPagePagination()
        request.query_params._mutable = True
        if "page" in request.data:
            request.query_params[paginator.page_query_param] = request.data["page"]
        if "limit" in request.data:
            request.query_params[paginator.page_size_query_param] = request.data["limit"]
        request.query_params._mutable = False

        paginated_queryset = paginator.paginate_queryset(queryset, request)

        return paginated_queryset, paginator

    return wrapper
