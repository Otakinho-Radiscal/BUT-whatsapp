import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ARQUIVO_DB = Path(__file__).resolve().parent.parent / "database" / "contatos_whatsapp.db"


def main() -> None:
    if not ARQUIVO_DB.exists():
        raise SystemExit("Banco não encontrado. Rode tools/criar_banco.py primeiro.")

    conn = sqlite3.connect(ARQUIVO_DB)
    print("Cadastro de contatos. Deixe o número vazio para terminar.")
    try:
        while True:
            numero = input("Número (+DDI DDD número, sem espaços): ").strip()
            if not numero:
                break
            nome = input("Nome: ").strip() or None
            resposta = input("Essa pessoa sabe do teste e concordou? (sim/não): ")
            autorizou = resposta.strip().lower() in ("sim", "s")

            try:
                if autorizou:
                    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    conn.execute(
                        "INSERT INTO contatos_whatsapp "
                        "(nome, numero, origem, consentimento, consentimento_em) "
                        "VALUES (?, ?, 'teste', 'autorizado', ?)",
                        (nome, numero, agora),
                    )
                else:
                    conn.execute(
                        "INSERT INTO contatos_whatsapp (nome, numero, origem) "
                        "VALUES (?, ?, 'teste')",
                        (nome, numero),
                    )
                conn.commit()
                print("  cadastrado.")
            except sqlite3.IntegrityError:
                print("  rejeitado: número em formato inválido ou já cadastrado.")

        total = conn.execute("SELECT COUNT(*) FROM contatos_whatsapp").fetchone()[0]
        aptos = conn.execute("SELECT COUNT(*) FROM contatos_autorizados").fetchone()[0]
        print(f"Total no banco: {total} | aptos a receber (autorizados): {aptos}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()