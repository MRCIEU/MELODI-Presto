from django.contrib import admin
from django.urls import path
from django.conf.urls import url, include
from rest_framework import routers
from rest_framework.documentation import include_docs_urls

# from rest_framework_swagger.views import get_swagger_view
from rest_framework.schemas import get_schema_view
from rest_framework import permissions
from django.views.generic import TemplateView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
import config

from . import views

# https://github.com/axnsan12/drf-yasg
schema_view = get_schema_view(
    openapi.Info(
        title="MELODI Presto API",
        default_version="v0.1",
        description="MELODI Presto API",
        contact=openapi.Contact(email="ben.elsworth@bristol.ac.uk"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    url=config.api_url,
)

# schema_view = get_swagger_view(title='textBase API')

router = routers.DefaultRouter()

urlpatterns = [
    # home of app and api
    path("", views.index, name="index"),
    ### web app ###
    #path("admin/", admin.site.urls),
    path(r"app/", views.app, name="app"),
    path(r"about/", views.about, name="about"),
    path(r"app/enrich/", views.enrich, name="enrich"),
    path(r"app/overlap/", views.overlap, name="overlap"),
    path(r"app/sentence/", views.sentence, name="sentence"),
    path(r"app/sentence/<str:pmid>/", views.sentence, name="sentence-p"),
    ### API ###
    # https://github.com/axnsan12/drf-yasg
    url(
        r"^docs(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    url(
        r"^docs/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    url(
        r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
    # status
    url(r"api/status/", views.StatusView, name="status-get-np"),
    url(r"api/overlap/", views.OverlapPostView, name="overlap-post"),
    url(r"api/sentence/", views.SentencePostView, name="sentence-post"),
    url(r"api/enrich/", views.EnrichPostView, name="enrich-post"),
    #url(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
]
