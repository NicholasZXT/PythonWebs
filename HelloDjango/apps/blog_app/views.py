from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views import View

# Create your views here.


def index(request):
    return HttpResponse("Hello to Blog Application.")

