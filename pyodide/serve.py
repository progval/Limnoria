import sys
import glob
import socket
import http.server
import socketserver

WHEEL_PATH = max(glob.glob('dist/limnoria-*-py3-none-any.whl'))
CONF_PATH = 'pyodide/limnoria.conf'


class Handler(http.server.BaseHTTPRequestHandler):

    def end_headers(self):
        # Enable Cross-Origin Resource Sharing (CORS)
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html;charset=UTF-8')
            self.end_headers()
            with open('pyodide/index.html', 'rb') as fd:
                self.wfile.write(fd.read() % {b'WHEEL_PATH': WHEEL_PATH.encode()})
        elif self.path == '/' + WHEEL_PATH:
            self.send_response(200)
            self.send_header('Content-Type', 'application/wasm')
            with open(WHEEL_PATH, 'rb') as fd:
                self.wfile.write(fd.read())
        elif self.path == '/limnoria.conf':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            with open(CONF_PATH, 'rb') as fd:
                self.wfile.write(fd.read())
        elif self.path == '/favicon.ico':
            pass
        else:
            print('Unexpected URL', self.path)

class TCPv6Server(socketserver.TCPServer):
    address_family = socket.AF_INET6
    allow_reuse_address = True


if __name__ == '__main__':
    port = 8081
    with TCPv6Server(('::', port), Handler) as httpd:
        print('Serving at: http://[::1]:{}'.format(port))
        httpd.serve_forever()
