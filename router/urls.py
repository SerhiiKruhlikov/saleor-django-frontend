# router/urls.py
from django.urls import path, re_path
from .views import dynamic_router

app_name = "router"

urlpatterns = [
    re_path(r'^(?P<slug>[\w-]+)/filter/(?P<filter_path>.+)/$', dynamic_router, name='dynamic_router_with_filter'),
    path("<slug:slug>/", dynamic_router, name="dynamic_router"),
]
