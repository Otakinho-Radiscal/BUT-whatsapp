import time

from waha_client import enviar_mensagem
from conditions import condicao_atendida #ainda vai ser implementado não funciona nessa versão

CONTATO = "5511999999999@c.us"  #numero template não funciona
INTERVALO_SEGUNDOS = 30


def main() -> None:
    print("Bot iniciado. Verificando condições...")
    while True:
        if condicao_atendida(): #envia mensagem dentro do intervalo de tempo que foi setado assim que a condição bater
            enviar_mensagem(CONTATO, "Condição atingida!")
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    main()