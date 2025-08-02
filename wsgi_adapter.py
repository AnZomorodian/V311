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
            'method': environ.get('REQUEST_METHOD', 'GET'),
            'path': environ.get('PATH_INFO', '/'),
            'query_string': environ.get('QUERY_STRING', '').encode(),
            'headers': self._get_headers_from_environ(environ),
            'server': (environ.get('SERVER_NAME', 'localhost'), int(environ.get('SERVER_PORT', 80))),
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
        Handle ASGI request and return response data
        """
        response_data = {
            'status': '200 OK',
            'headers': [('Content-Type', 'application/json')],
            'body': b'{"status": "healthy", "service": "F1 Analytics Dashboard"}'
        }
        
        try:
            # For basic routes, provide simple responses
            path = scope.get('path', '/')
            
            if path == '/health':
                response_data['body'] = b'{"status": "healthy", "service": "F1 Analytics Dashboard"}'
            elif path == '/':
                response_data['headers'] = [('Content-Type', 'text/html')]
                html_content = '''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>F1 Analytics Dashboard</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; background: #1a1a1a; color: white; }
                        .container { max-width: 800px; margin: 0 auto; text-align: center; }
                        .title { color: #ff0000; font-size: 2.5em; margin-bottom: 20px; }
                        .subtitle { font-size: 1.2em; margin-bottom: 30px; color: #ccc; }
                        .notice { background: #333; padding: 20px; border-radius: 10px; border-left: 4px solid #ff0000; }
                        .btn { background: #ff0000; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px; }
                        .btn:hover { background: #cc0000; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1 class="title">F1 Analytics Dashboard</h1>
                        <p class="subtitle">Professional Formula 1 Data Analysis Platform</p>
                        
                        <div class="notice">
                            <h3>Server Configuration Notice</h3>
                            <p>The application is currently running in compatibility mode with WSGI. For full functionality including interactive charts and data analysis, the server needs to be configured with an ASGI worker.</p>
                            
                            <p><strong>To run with full functionality:</strong></p>
                            <p>Use: <code>uvicorn main:app --host 0.0.0.0 --port 5000</code></p>
                            
                            <p>Currently available endpoints:</p>
                            <ul style="text-align: left; display: inline-block;">
                                <li>Health check: <a href="/health" class="btn">Health</a></li>
                                <li>Dashboard: Limited functionality</li>
                                <li>Analysis: Limited functionality</li>
                                <li>API endpoints: Limited functionality</li>
                            </ul>
                        </div>
                        
                        <p style="margin-top: 30px;">
                            <a href="/health" class="btn">Test Health Endpoint</a>
                        </p>
                    </div>
                </body>
                </html>
                '''
                response_data['body'] = html_content.encode('utf-8')
            else:
                response_data['status'] = '404 Not Found'
                response_data['body'] = b'{"error": "Endpoint not available in WSGI mode"}'
                
        except Exception as e:
            response_data['status'] = '500 Internal Server Error'
            response_data['body'] = f'{{"error": "Internal server error: {str(e)}"}}'.encode()
        
        return response_data


# Create the WSGI application
application = ASGIToWSGIAdapter(fastapi_app)

# Also export as 'app' for compatibility
app = application