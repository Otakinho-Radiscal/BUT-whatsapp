import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_SQL = RAIZ / "database" / "contatos_whatsapp.sql"
ARQUIVO_DB = RAIZ / "database" / "contatos_whatsapp.db"

def main() -> None:
    if ARQUIVO_DB.exists():
        raise SystemExit(f"{ARQUIVO_DB.name} já existe. Apague o arquivo se quiser recriar.")

    script = ARQUIVO_SQL.read_text(encoding="utf-8")
    conn = sqlite3.connect(ARQUIVO_DB)
    try:
        conn.executescript(script)
        objetos = conn.execute(
            "SELECT type, name FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
    finally:
        conn.close()

    print("Banco criado. Objetos:")
    for tipo, nome in objetos:
        print(f"  {tipo}: {nome}")


if __name__ == "__main__":
    main()