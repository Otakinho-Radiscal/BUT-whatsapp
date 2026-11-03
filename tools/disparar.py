import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

URL = "http://127.0.0.1:4000/api/sendText"

def enviar(numero: int) -> tuple[bool, float]:
    inicio = time.perf_counter()
    try:
        resposta = requests.post(
            URL,
            json={
                "session": "default",
                "chatId": f"550000{numero:06d}@c.us",
                "text": f'será se trava esse bot aqui ?',
            },
            timeout=10,
        )
        ok = resposta.status_code == 201
    except requests.RequestException:
        ok = False
    return ok, time.perf_counter() - inicio
    

def main() -> None:
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    threads = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    print(f"enviando umas {total} mensagens com {threads} threads será se vai travar tudo ?")
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=threads) as pool:
        resultados = list(pool.map(enviar, range(1, total + 1)))
        duração = time.perf_counter() - inicio
        
        sucessos = sum(1 for ok, _ in resultados if ok)
        latencia = [t for _, t in resultados]
        
        print(f"Tempo total:   {duração:.2f}s")
    print(f"Sucessos:      {sucessos}")
    print(f"Falhas:        {total - sucessos}")
    print(f"Latência média: {sum(latencia) / total:.3f}s")
    print(f"Latência máxima: {max(latencia):.3f}s")

if __name__ == "__main__":
    main()