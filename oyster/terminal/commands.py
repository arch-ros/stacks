import zmq
import json

_context = None
_sockets = {}

def set_context(context):
    global _context
    _context = context

# Socket commands

def _create_socket(type):
    if type == 'REQ':
        return _context.socket(zmq.REQ)
    elif type == 'REP':
        return _context.socket(zmq.REP)
    elif type == 'PUB':
        return _context.socket(zmq.PUB)
    elif type == 'SUB':
        return _context.socket(zmq.SUB)
    return None

def bind_socket(name, type, endpoint):
    sock = _create_socket(type)
    sock.bind(endpoint)
    _sockets[name] = sock

def connect_socket(name, type, endpoint):
    sock = _create_socket(type)
    sock.connect(endpoint)
    _sockets[name] = sock

def require_socket(name, type):
    # Fail if a socket doesn't exist
    pass

def get_socket(name):
    return _sockets[name]

# Now querying commands
def query_name(package_name):
    query = {
        'type':'query',
        'payload': [{
            'info':{
                'name':'{}'.format(package_name)
            }
            }]
    }

    # Connect to the server and make the query
    req_sock = get_socket('query')

    json_query = json.dumps(query)
    req_sock.send_json(json_query)
    json_result = json.loads(req_sock.recv_json())

    print('\n'.join(json_result.keys()))
