from django.urls import path

#from jsonrpc.views import browse
from jsonrpc.site import jsonrpc_site

urlpatterns = [
  path(r'^json/browse/$', 'jsonrpc.views.browse', name='jsonrpc_browser'),
  path(r'^json/$', jsonrpc_site.dispatch, name='jsonrpc_mountpoint'),
  path(r'^json/(?P<method>[a-zA-Z0-9.-_]+)$', jsonrpc_site.dispatch),
]
