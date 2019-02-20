import threading

from django.contrib.auth.models import User
from django.core import management

from jsonrpc._json import loads, dumps
from six.moves.urllib import request as urllib_request
from six.moves.urllib import parse as urllib_parse

from jsonrpc.proxy import ServiceProxy

TEST_DEFAULTS = {
    'ROOT_URLCONF': 'test.jsontesturls',
    'DEBUG': True,
    'DEBUG_PROPAGATE_EXCEPTIONS': True,
    'DATETIME_FORMAT': 'N j, Y, P',
    'USE_I18N': False,
    'INSTALLED_APPS': (
        'jsonrpc',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions'),
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'test.sqlite3',
        },
    },
    'MIDDLEWARE_CLASSES': (
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
    ),
    'AUTHENTICATION_BACKENDS': ('django.contrib.auth.backends.ModelBackend',),
    'TEMPLATE_LOADERS': (
        'django.template.loaders.filesystem.load_template_source',
        'django.template.loaders.app_directories.load_template_source'),
}

from django.conf import settings
settings.configure(**TEST_DEFAULTS)

import django
if hasattr(django, 'setup'):
    # Run django.setup() for Django>=1.7
    django.setup()

def _call(host, req):
    return loads(urllib_request.urlopen(host, dumps(req).encode('utf-8')).read().decode('utf-8'))


class JsonServer(object):
    def _thread_body(self):
        try:
            from wsgiref.simple_server import make_server
            from django.core.handlers.wsgi import WSGIHandler
            management.call_command('migrate', interactive=False)
            try:
                User.objects.create_user(username='rishi', email='rishijha424@gmail.com', password='password').save()
            except Exception:
                pass

            http = make_server('', 8999, WSGIHandler())
            print('Server created. continue={0}'.format(self.continue_serving))
            self.event.set() # notify parent thread that the server is ready to serve requests
            while self.continue_serving:
                print('Waiting for request!')
                http.handle_request()
                self.n_requests += 1
                print('Handled {0} requests!'.format(self.n_requests))
            print('Got server stop! requests={0}'.format(self.n_requests))
            http.server_close()
            print('Server closed!')
        except Exception as e:
            import traceback
            traceback.print_exc()
            print('Error starting server: {0}'.format(e))
        finally:
            if not self.event.is_set():
                self.event.set()

    def start(self):
        print('Starting Server...')
        self.continue_serving = True
        self.n_requests = 0
        self.event = threading.Event()
        self.t = threading.Thread(target=self._thread_body)
        self.t.start()
        self.event.wait()
        return self

    def stop(self):
        print('Stopping Server...')
        self.continue_serving = False
        try:
            proxy = ServiceProxy('http://127.0.0.1:8999/json/', version=2.0)
            proxy.jsonrpc.test(string='Hello')['result']
        except: # doesnt matter if this fails
            pass
        self.t.join(2.0)
        return self

