from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class MockPrinterHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            safe_name = data.get('emp_name', '').encode('ascii', 'replace').decode()

            print("\n" + "="*40)
            print(">>> SUCCESS: WEBHOOK RECEIVED!")
            print(f"ID: {data.get('employee_id')} | Name: {safe_name}")
            print("="*40 + "\n")
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            with open("mock_error.txt", "w") as f:
                f.write(str(e))

def run(port=5006):
    server_address = ('', port)
    httpd = HTTPServer(server_address, MockPrinterHandler)
    print(f"Mock Printer at port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
