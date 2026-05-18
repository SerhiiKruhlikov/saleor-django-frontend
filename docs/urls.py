# docs/urls.py
from django.urls import re_path
from django.views.static import serve as static_serve
from django.http import HttpResponseRedirect
from django.conf import settings


def docs_index(request, lang):
    """Redirect from /docs/<lang>/ to /docs/<lang>/index.html"""
    return HttpResponseRedirect(f'/docs/{lang}/index.html')


urlpatterns = [
    # Redirect from /docs/ to the default language
    re_path(r'^$', lambda request: HttpResponseRedirect('/docs/en/')),
    # Redirect from /docs/<lang>/ to index.html
    re_path(r'^(?P<lang>uk|en|es)/$', docs_index),
    # Serve all other files
    re_path(r'^(?P<path>.*)$', static_serve, {
        'document_root': settings.BASE_DIR / 'docs' / '_build' / 'html',
    }),
]
