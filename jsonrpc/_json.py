import json

try:
    json.dumps
    json.loads
except AttributeError:
    try:  # monkey patching for python-json package
        json.dumps = lambda obj, *args, **kwargs: json.write(obj)
        json.loads = lambda str, *args, **kwargs: json.read(str)
    except AttributeError:
        raise ImportError('Could not load an appropriate JSON library '
                          'currently supported are simplejson, '
                          'python3.7 json and python-json')

loads = json.loads
dumps = json.dumps
