from rest_framework.pagination import CursorPagination


class NewestFirstPagination(CursorPagination):
    ordering = "-created_at"
    page_size = 20
    max_page_size = 50
    page_size_query_param = "page_size"
