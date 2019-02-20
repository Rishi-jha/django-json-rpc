import sys
from uuid import uuid1
from jsonrpc._json import loads, dumps
from jsonrpc.exceptions import *
from jsonrpc._types import *
from django.conf import settings
from django.core import signals
from django.utils.encoding import smart_text
from django.core.serializers.json import DjangoJSONEncoder


def empty_dec(f):
    """
    An empty decorator
    :param f: function
    :return: function
    """
    return f


try:
    from django.views.decorators.csrf import csrf_exempt
except (NameError, ImportError):
    csrf_exempt = empty_dec


encode_kw = lambda to_encode: {str(key): value for key, value in to_encode.items()}


def trim_docstring(docstring):
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


def encode_kw11(to_encode):
    """
    The function to encode kwargs.
    :param: to_encode: kwargs to encode.
    :return: encoded kwargs: dict
    """
    encoded_kw = {}
    if not isinstance(to_encode, dict):
        return encoded_kw
    
    for k, v in to_encode.items():
        try:
            int(k)
        except ValueError:
            encoded_kw.update({k: v})
    return encoded_kw

def encode_arg11(to_encode):
    """
    The function to encode args.
    :param: to_encode: args to encode.
    :return: encoded args: dict
    """
    encoded_args = set()
    if isinstance(to_encode, list):
        return to_encode
    elif isinstance(to_encode, dict):
        _ = encode_kw(to_encode)
        for key in _.keys():
            try:
                int(key)
            except ValueError:
                pass
            else:
                encoded_args.add(str(key))
        
        encoded_args = [_[key] for key in sorted(encoded_args)]
        return encoded_args

def validate_params(method, attributes):
    """
    Function to validate parameters.
    :param method: Type of HTTP method.
    :param attributes: parameters.
    """
    print(method.json_arg_types.keys())
    if type(attributes['params']) == Object:
        keys = method.json_arg_types.keys()
        if len(keys) != len(attributes['params']):
            raise InvalidParamsError('Not enough params provided for '
                                     '{}'.format(
                                         method.json_sig))
        for key in keys:
            if not key in attributes['params']:
                print('\n\n\n\nSHITTER SHITTER', key, attributes, '\n\n\n\n')
                raise InvalidParamsError("{} is not a valid parameter for "
                                         "{}".format(key, method.json_sig))
            if not Any.kind(
                    attributes['params'][key])==method.json_arg_types[key]:
                raise InvalidParamsError('{} is not the correct type {} '
                                         'for {}'.format(
                                             type(attributes['params'][key]),
                                             method.json_arg_types[key],
                                             method.json_sig))
    elif type(attributes['params']) == Array:
        print(attributes)
        arg_types = list(method.json_arg_types.values())
        try:
            for index, arg in enumerate(attributes['params']):
                if not Any.kind(arg) == arg_types[index]:
                    raise InvalidParamsError('{} is not the correct type '
                                             '{} for {}'.format(
                                                 type(arg), arg_types[index],
                                                 method.json_sig))
        except IndexError:
            raise InvalidParamsError('Too many params provided for '
                                     '{}'.format(method.json_sig))
        else:
            if len(attributes['params']) != len(arg_types):
                raise InvalidParamsError('Not enough params provided '
                                         'for {}'.format(method.json_sig))


class JsonRpcSite(object):
    """A JSON-RPC Site"""

    def __init__(self, json_encoder=DjangoJSONEncoder):
        """
        Constructor for JsonRpcSite.
        :param json_encoder: type of Json Encoder. Default to DjangoJSONEncoder
        """
        self.urls = {}
        self.uuid = uuid1()
        self.version = '1.0'
        self.name = 'django-json-rpc'
        self.register('system.describe', self.describe)
        self.json_encoder = json_encoder
        self.available_versions = ['2.0', '1.1', '1.0']

    def _empty_response(self, version='1.0'):
        """
        Method to provide empty response
        :param version: Version of JSON RPC
        :return: Empty Response
        """
        response = {'id': None}
        if version == '2.0':
            response.update({'error': None, 'result': None, 'jsonrpc': version})
        if version == '1.1':
            response['version'] = version
        return response

    def _validate_get(self, request, method):
        """
        :param request: Request instance
        :param method: http method
        :return: tuple of "if request is valid and data.
        """
        if not request.method == "GET":
            return False, {}

        encoded_params = lambda req: {key: value[0] if len(value) == 1 else value for key, value in req}
        method = smart_text(method)
        if method in self.urls and getattr(self.urls[method], 'json_safe', False):
            data = {
                'params': encoded_params(request.GET.lists()),
                'method': method,
                'id': 'jsonrpc',
                'version': '1.1'
            }
            return True, data

    def _response_dict(self, request, data, is_batch=False, version='1.0',
                       json_encoder=None):
        """
        Method to get the response for the request.
        :param request: request for json rpc
        :param data: parameters associated with the request
        :param is_batch: defaults to false
        :param version: JSON RPC version
        :param json_encoder: Json Encoder
        :return: response, status code
        """
        json_encoder = json_encoder or self.json_encoder
        response = self._empty_response(version=version)

        def apply_version(function, req, param, version):
            if version == '1.1':
                return function(req, *encode_arg11(param),
                                **encode_kw(encode_kw11(param)))
            if isinstance(param, dict):
                return function(req, **encode_kw(param))
            return function(req, *param)

        try:
            if 'params' not in data:
                data['params'] = []
            if 'method' not in data:
                raise InvalidParamsError("Request requires str: 'method' and "
                                         "list: 'params'.")
            if data['method'] not in self.urls:
                raise MethodNotFoundError("Method not found, "
                                          "Available methods:\n\t{}".format(
                                              "\n\t".join(self.urls.keys())))

            v_key = ''
            if 'jsonrpc' in data:
                v_key = 'jsonrpc'
            elif 'version' in data:
                v_key = 'version'

            try:

                if str(data[v_key]) not in self.available_versions:
                    raise InvalidRequestError(
                        "JSON-RPC version {} not supported.Please raise bug @ "
                        "https://github.com/Rishi-jha/django-json-rpc".format(
                            data[v_key]))
                version = request.jsonrpc_version = response[v_key] = str(data['version'])
            except KeyError:
                request.jsonrpc_version = '1.0'

            method = self.urls[str(data['method'])]
            if getattr(method, 'json_validate', False):
                validate_params(method, data)

            if 'id' in data and data['id'] is not None:
                response['id'] = data['id']
                if version in ('1.1', '2.0') and 'error' in response:
                    response.pop('error')
            elif is_batch:
                raise InvalidRequestError("Not ok in batch format")

            _result = apply_version(method, request, data['params'], version)
            if not data.get('id'):
                return None, 204
            _result = list(_result) if isinstance(_result, tuple) else _result
            encoder = json_encoder()
            _builtin_types = set((dict, list, set, NoneType, bool, six.text_type) + six.integer_types + six.string_types)
            if not any(isinstance(_result, ty) for ty in _builtin_types):
                try:
                    encoder.default(_result)
                except KeyError:
                    raise TypeError("Return type not supported for {}".format(_result))

            response['result'] = _result
            status = 200

        except Error as e:
            response['error'] = e.json_rpc_format
            if version in ('1.1', '2.0') and 'result' in response:
                response.pop('result')
            status = e.status

        except Exception as e:

            signals.got_request_exception.send(sender=self.__class__,
                                               request=request)

            # Put stacktrace into the OtherError only if DEBUG is enabled
            if settings.DEBUG:
                other_error = OtherError(e)
            else:
                other_error = OtherError("Internal Server Error")

            response['error'] = other_error.json_rpc_format
            status = other_error.status
            if version in ('1.1', '2.0') and 'result' in response:
                response.pop('result')

        # Exactly one of result or error MUST be specified. It's not
        # allowed to specify both or none.
        if version in ('1.1', '2.0') and not response.get('error'):
            response.pop('error')

        return response, status

    @csrf_exempt
    def dispatch(self, request, method='', json_encoder=None):
        """
        dispatch method for registering apps
        :param request: Request to process
        :param method: type of method
        :param json_encoder: json encdoer
        :return: response
        """
        from django.http import HttpResponse
        json_encoder = json_encoder or self.json_encoder


        try:
            response = self._empty_response()
            if request.method.upper() == 'GET':
                is_valid, data = self._validate_get(request, method)
                if not is_valid:
                    raise InvalidRequestError("The method you are trying to "
                                              "access is not available by GET "
                                              "requests")
            elif not request.method.upper() == 'POST':
                raise RequestPostError
            else:
                try:
                    if hasattr(request, "body"):
                        data = loads(request.body.decode('utf-8'))
                    else:
                        data = loads(request.raw_post_data.decode('utf-8'))
                except:
                    raise InvalidRequestError
            if isinstance(data, list):
                response = [self._response_dict(request, data=d,
                                                is_batch=True,
                                                json_encoder=json_encoder)[0]
                            for d in data]
                status = 200
            else:
                response, status = self._response_dict(
                    request, data,
                    json_encoder=json_encoder)
                if response is None and not data.get('id'):
                    return HttpResponse('', status=status)

            json_rpc = dumps(response, cls=json_encoder)

        except Error as e:
            response['error'] = e.json_rpc_format
            status = e.status
            json_rpc = dumps(response, cls=json_encoder)
        except Exception as e:
            # exception missed by others
            signals.got_request_exception.send(sender=self.__class__,
                                               request=request)

            # Put stacktrace into the OtherError only if DEBUG is enabled
            if settings.DEBUG:
                other_error = OtherError(e)
            else:
                other_error = OtherError("Internal Server Error")

            response['result'] = None
            response['error'] = other_error.json_rpc_format
            status = other_error.status

            json_rpc = dumps(response, cls=json_encoder)

        return HttpResponse(json_rpc,
                            status=status,
                            content_type='application/json-rpc')


    def procedure_desc(self, key):
        """
        describing the procedure
        :param key: method name
        :return: dict
        """
        method = self.urls[key]
        return {
            'name': method.json_method,
            'summary': trim_docstring(method.__doc__),
            'idempotent': method.json_safe,
            'params': [{'type': str(Any.kind(t)),
                        'name': k} for k, t in method.json_arg_types.items()],
            'return': {'type': str(method.json_return_type)}
        }

    def service_desc(self):
        """
        Describing the service
        :return: dict
        """
        return {
            'sdversion': '1.0',
            'name': self.name,
            'id': 'urn:uuid:{}'.format(self.uuid),
            'summary': trim_docstring(self.__doc__),
            'version': self.version,
            'procs': [self.procedure_desc(key) for key in self.urls.keys()
                      if self.urls[key] != self.describe]
        }

    def describe(self, request):
        return self.service_desc()

    def register(self, name, method):
        self.urls[smart_text(name)] = method



jsonrpc_site = JsonRpcSite()
