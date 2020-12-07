from django.http import HttpResponse


class HttpResponseNoContent(HttpResponse):
    status_code = 204
