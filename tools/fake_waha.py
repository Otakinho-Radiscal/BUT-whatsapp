import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LATENCIA_MIN = 0.1  #segundos
LATENCIA_MAX = 0.5
TAXA_ERRO = 0.0    #sem erros

lock = threading.Lock()
total = 0


class FakeWaha(BaseHTTPRequestHandler):
    def do_POST(self):
        global total
        tamanho = int(self.headers.get("Content-Length", 0))
        dados = json.loads(self.rfile.read(tamanho) or b"{}")
        time.sleep(random.uniform(LATENCIA_MIN, LATENCIA_MAX))

        if self.path != "/api/sendText":
            status = 404
        elif random.random() < TAXA_ERRO:
            status = 500
        else:
            status = 201

        with lock:
            total += 1
            if total % 50 == 0:
                print(f"{total} requisições recebidas")

        print(f"[fake] {dados.get('chatId')} -> {dados.get('text')}")
        corpo = json.dumps({"fake": True}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *args):
        pass  #silencia o log padrão de cada requisição


if __name__ == "__main__":
    print("Fake WAHA rodando em http://localhost:4000")
    ThreadingHTTPServer(("localhost", 4000), FakeWaha).serve_forever()
