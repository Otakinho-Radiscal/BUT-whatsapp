# BUT-whatsapp

![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/docker-WAHA-2496ED?logo=docker&logoColor=white)
![SQLite](https://img.shields.io/badge/sqlite-banco%20local-003B57?logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-orange)

Bot de WhatsApp em Python com atendimento automático por palavra-chave e envio de avisos vindos do NTS (reservas e karaokê).

## Índice

- [Sobre](#sobre)
- [Funcionalidades](#funcionalidades)
- [Tecnologias](#tecnologias)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Como usar](#como-usar)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Testes](#testes)
- [Contribuindo](#contribuindo)
- [Aviso](#aviso)
- [Licença](#licença)

## Sobre

O bot conversa com clientes pelo WhatsApp usando o [WAHA](https://waha.devlike.pro), que roda em Docker e expõe uma API HTTP. O WAHA avisa o bot de cada mensagem recebida por webhook, e o bot responde pelo `POST /api/sendText`.

Os textos ficam todos num arquivo só (`bot/templates.json`), e os contatos, o consentimento e o andamento das conversas ficam num banco SQLite local.

## Funcionalidades

- Atendimento automático por palavra-chave, com menu, instruções e comprovante
- Comprovante com código único por cliente
- `ATENDENTE` pausa o bot na conversa e passa para a equipe
- `SAIR` descadastra o cliente, inclusive com o bot pausado
- Avisos do NTS (reserva pendente, confirmada ou cancelada, vez no karaokê) só para contatos autorizados
- Envio um de cada vez, com intervalo entre as mensagens
- Webhook com assinatura HMAC, sem respostas duplicadas e sem responder mensagens antigas
- Scripts para testar tudo sem WhatsApp

## Tecnologias

- [Python](https://www.python.org) 3.11+
- [WAHA](https://waha.devlike.pro) (engine NOWEB) em [Docker](https://www.docker.com)
- SQLite
- [requests](https://pypi.org/project/requests/) e [python-dotenv](https://pypi.org/project/python-dotenv/)

## Pré-requisitos

- Python 3.11 ou mais novo
- Docker e Docker Compose
- Um número de WhatsApp de teste

## Instalação

```bash
git clone https://github.com/Otakinho-Radiscal/BUT-whatsapp.git
cd BUT-whatsapp

python -m venv venv
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

Suba o WAHA e crie o banco:

```bash
docker compose up -d
python tools/criar_banco.py
```

Depois, inicie a sessão e leia o QR code pelo dashboard do WAHA em `http://localhost:3000`.

## Configuração

Copie o modelo e preencha os valores:

```bash
cp .env.example .env
```

| Variável | Descrição | Padrão |
|---|---|---|
| `WAHA_URL` | Endereço do WAHA | `http://localhost:3000` |
| `WAHA_SESSION` | Nome da sessão no WAHA | `default` |
| `WAHA_API_KEY` | Chave da API do WAHA | — |
| `NTS_URL` | Endereço do NTS | `http://127.0.0.1:8000` |
| `NTS_TOKEN` | Token do NTS | — |
| `NTS_DRY_RUN` | `1` só mostra o que enviaria, `0` envia | `1` |
| `WEBHOOK_HOST` | Endereço onde o webhook escuta | `127.0.0.1` |
| `WEBHOOK_PORTA` | Porta do webhook | `5005` |
| `WEBHOOK_HMAC_KEY` | Chave que confirma que o POST veio do WAHA | — |
| `BOT_DB` | Outro arquivo de banco (ex.: cópia para testes) | `database/contatos_whatsapp.db` |

Para gerar a `WEBHOOK_HMAC_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Os textos do bot, o nome da casa, a palavra-chave e o prefixo do comprovante ficam em `bot/templates.json`.

## Como usar

Atendimento automático:

```bash
python bot/webhook.py
```

Avisos do NTS (em modo demonstração enquanto `NTS_DRY_RUN=1`):

```bash
python bot/nts_consumer.py
```

### Comandos do atendimento

| Cliente envia | Bot responde |
|---|---|
| Palavra-chave (ex.: `PROMOEXEMPLO`) | Registra o consentimento e envia o menu |
| `2` | Explica como salvar o contato |
| `1` | Registra a declaração e envia o comprovante |
| `ATENDENTE` | Pausa o bot e passa a conversa para a equipe |
| `SAIR` | Descadastra o cliente |
| Outro texto | Orienta; após 3 tentativas seguidas, para de responder |

## Estrutura do projeto

```
BUT-whatsapp/
├── bot/
│   ├── main.py            # ponto de partida (em construção)
│   ├── webhook.py         # recebe mensagens do WAHA e responde
│   ├── atendimento.py     # fluxo da conversa
│   ├── banco.py           # acesso ao SQLite
│   ├── templates.json     # textos do bot
│   ├── templates.py       # leitura e preenchimento dos textos
│   ├── nts_consumer.py    # consumidor da fila do NTS
│   ├── envio.py           # fila única de envio, com intervalo
│   └── waha_client.py     # cliente HTTP do WAHA
├── database/              # banco SQLite (fora do git)
├── tools/                 # scripts de apoio e de teste
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Testes

Os testes rodam sem WhatsApp e sem mexer no banco original.

```bash
python tools/teste_templates.py          # textos e campos do templates.json
python tools/teste_banco_atendimento.py  # funções do banco, numa cópia
python tools/teste_atendimento.py        # conversa completa, numa cópia
```

Teste pelo webhook com um cliente simulado, usando uma cópia do banco:

```powershell
# terminal 1
Copy-Item database\contatos_whatsapp.db database\teste_atendimento.db
$env:BOT_DB = "database/teste_atendimento.db"
$env:WAHA_URL = "http://127.0.0.1:4000"
python bot/webhook.py

# terminal 2
python tools/cliente_falso.py
```

## Contribuindo

1. Crie uma branch a partir da `DEV`: `git switch -c feature/nome-da-feature`
2. Faça commits pequenos e com mensagens claras
3. Confira que `.env` e arquivos `.db` não entraram no commit
4. Envie a branch e abra um Pull Request para a `DEV`

## Aviso

O WAHA não é a API oficial do WhatsApp, e o número pode ser banido. Use um número de teste, envie pouco e só para quem pediu para receber.

## Licença

A definir.
