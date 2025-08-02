"""
WSGI adapter for FastAPI application
This allows FastAPI to run with gunicorn's WSGI worker as a temporary workaround
"""

import asyncio
from typing import Any, Callable, Dict, List, Tuple
from main import app as fastapi_app


class ASGIToWSGIAdapter:
    """
    Adapter that allows ASGI applications to run on WSGI servers
    This is a simplified adapter for basic functionality
    """
    
    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    def __call__(self, environ: Dict[str, Any], start_response: Callable) -> List[bytes]:
        """
        WSGI application callable
        """
        try:
            # Create an event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Build ASGI scope from WSGI environ
            scope = self._build_scope(environ)
            
            # Handle the request
            response_data = loop.run_until_complete(self._handle_request(scope))
            
            # Start WSGI response
            status = response_data.get('status', '200 OK')
            headers = response_data.get('headers', [])
            start_response(status, headers)
            
            # Return response body
            body = response_data.get('body', b'FastAPI app running via WSGI adapter')
            return [body]
            
        except Exception as e:
            # Fallback error response
            start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
            return [f'Error: {str(e)}'.encode()]
        finally:
            if 'loop' in locals():
                loop.close()

    def _build_scope(self, environ: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert WSGI environ to ASGI scope
        """
        return {
            'type': 'http',
            'asgi': {'version': '3.0', 'spec_version': '2.1'},
            'http_version': '1.1',
            'method': environ.get('REQUEST_METHOD', 'GET').upper(),
            'scheme': environ.get('wsgi.url_scheme', 'http'),
            'path': environ.get('PATH_INFO', '/'),
            'raw_path': environ.get('PATH_INFO', '/').encode(),
            'query_string': environ.get('QUERY_STRING', '').encode(),
            'root_path': '',
            'headers': self._get_headers_from_environ(environ),
            'server': (environ.get('SERVER_NAME', 'localhost'), int(environ.get('SERVER_PORT', 80))),
            'client': (environ.get('REMOTE_ADDR', '127.0.0.1'), int(environ.get('REMOTE_PORT', 0))),
        }

    def _get_headers_from_environ(self, environ: Dict[str, Any]) -> List[Tuple[bytes, bytes]]:
        """
        Extract headers from WSGI environ
        """
        headers = []
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].replace('_', '-').lower()
                headers.append((header_name.encode(), value.encode()))
        return headers

    async def _handle_request(self, scope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle ASGI request by actually calling the FastAPI application
        """
        response_data = {
            'status': '200 OK',
            'headers': [('Content-Type', 'application/json')],
            'body': b'{"status": "healthy", "service": "F1 Analytics Dashboard"}'
        }
        
        try:
            # Create proper ASGI message system
            messages = []
            
            # Receive function to capture messages
            async def receive():
                return {'type': 'http.request', 'body': b'', 'more_body': False}
            
            # Send function to capture response
            async def send(message):
                messages.append(message)
            
            # Call the actual FastAPI application
            await self.asgi_app(scope, receive, send)
            
            # Process the response messages
            status_code = 200
            headers = []
            body = b''
            
            for message in messages:
                if message['type'] == 'http.response.start':
                    status_code = message['status']
                    headers = message.get('headers', [])
                elif message['type'] == 'http.response.body':
                    body += message.get('body', b'')
            
            # Convert status code to status string
            status_text = f"{status_code} {self._get_status_text(status_code)}"
            
            # Convert headers format
            wsgi_headers = []
            for header in headers:
                if isinstance(header, (list, tuple)) and len(header) == 2:
                    name = header[0].decode() if isinstance(header[0], bytes) else str(header[0])
                    value = header[1].decode() if isinstance(header[1], bytes) else str(header[1])
                    wsgi_headers.append((name, value))
            
            response_data = {
                'status': status_text,
                'headers': wsgi_headers,
                'body': body
            }
                
        except Exception as e:
            response_data['status'] = '500 Internal Server Error'
            response_data['headers'] = [('Content-Type', 'application/json')]
            response_data['body'] = f'{{"error": "Internal server error: {str(e)}"}}'.encode()
        
        return response_data
    
    def _get_status_text(self, status_code: int) -> str:
        """Get status text for HTTP status code"""
        status_texts = {
            200: 'OK',
            201: 'Created',
            204: 'No Content',
            301: 'Moved Permanently',
            302: 'Found',
            304: 'Not Modified',
            400: 'Bad Request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Not Found',
            405: 'Method Not Allowed',
            500: 'Internal Server Error',
            502: 'Bad Gateway',
            503: 'Service Unavailable'
        }
        return status_texts.get(status_code, 'Unknown')


# Create the WSGI application
application = ASGIToWSGIAdapter(fastapi_app)

# Also export as 'app' for compatibility
app = application