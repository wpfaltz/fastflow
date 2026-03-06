[PT-BR]

# ⚡ FastFlow

A **FastFlow** é uma biblioteca de **aceleradores em Python** desenvolvida para simplificar e padronizar a integração entre serviços de dados, como **MinIO**, **bancos de dados (Oracle 11g, PostgreSQL)** e **sistemas de notificação (Telegram, e-mail)**.

O projeto também oferece módulos de **manipulação de arquivos multiplataforma** (local e remoto via SSH/SFTP), uma **camada de abstração de bancos de dados**, um **sistema de hooks** extensível para injeção de contexto e identidade, e uma **engine de orquestração** que integra de forma transparente com o **Prefect OSS**.

---

## 🚀 Visão Geral

A biblioteca faz parte do Trabalho de Conclusão de Curso de **William Petterle Pfaltzgraff** (UFRJ – Engenharia de Computação), sob orientação do **Prof. Flávio Luis de Mello** , e foi criada para atender às necessidades do **Laboratório da Matemática Aplicada (LabMA)**, mas projetada para uso genérico por outros desenvolvedores e pesquisadores.

A FastFlow foi pensada para ser usada em conjunto com orquestradores de fluxo de dados, como o **Prefect OSS**, servindo como base para automação de tarefas e pipelines de dados reprodutíveis.

### Principais funcionalidades

- **Banco de Dados** — Interface unificada para PostgreSQL e Oracle, com suporte a leitura, escrita e operações de merge (UPSERT).
- **Mensageria** — Envio de notificações via Telegram e e-mail, com arquitetura extensível para outros canais.
- **Storage** — Integração com MinIO (compatível com S3) para listagem e download de objetos.
- **I/O de Arquivos** — Gerenciamento de arquivos local (copiar, mover, excluir, listar) e remoto via SSH/SFTP.
- **Engine** — Decorators `build_flow` e `ff_task` que encapsulam flows e tasks do Prefect com contexto FastFlow.
- **Hooks** — Sistema de plugins que injetam automaticamente tags de ambiente, identidade do usuário, sistema operacional e secrets do Key Vault.
- **Configuração** — Utilitários para leitura de variáveis de ambiente com suporte a `.env`.

---

## ⚙️ Instalação

### Requisitos

- Python **≥ 3.10**

### Instalação completa

```bash
pip install fastflow
```

### Instalação a partir do código-fonte

```bash
git clone <repositório>
cd fastflow
pip install -e .
```

---

## 🔧 Configuração

### Variáveis de Ambiente

A FastFlow pode carregar variáveis de ambiente automaticamente a partir de um arquivo `.env`:

```python
from fastflow import configure_environment

# Modo "auto": carrega .env se existir, senão usa variáveis do SO
configure_environment(mode="auto")

# Modo "dotenv": exige o arquivo .env
configure_environment(mode="dotenv", dotenv_path=".env", override=False)

# Modo "os" (padrão): usa apenas variáveis do sistema operacional
configure_environment(mode="os")
```

### Variáveis de Ambiente Utilizadas pela FastFlow

| Variável | Descrição |
|---|---|
| `FASTFLOW_SERVER_HOST` | Hostname do servidor de produção (usado pelos hooks `env_hook`, `os_user_hook`, `host_tag_hook`) |
| `FASTFLOW_SERVER_USER_TAG` | Nome de usuário a ser tagueado quando em servidor (hook `os_user_hook`) |
| `FASTFLOW_AUTH_SERVER_URL` | URL do servidor de autenticação JWT (hooks `server_identity_hook`, `keyvault_hook`) |
| `FASTFLOW_AUTH_TOKEN_DIR` | Diretório de cache de tokens JWT (padrão: `~/.fastflow/tokens`) |
| `FASTFLOW_AUTH_REQUIRE` | Se `"1"` / `"true"`, torna autenticação obrigatória |
| `FASTFLOW_JWT` | Caminho para arquivo JWT ou token direto (usado pelo `keyvault_hook`) |

---

## 🧠 Estrutura do Projeto

```
fastflow/
├── __init__.py
├── version.py
├── py.typed
├── core/
│   └── config.py              # Utilitários de leitura de variáveis de ambiente
├── db/
│   ├── __init__.py
│   ├── manager.py             # Fachada de alto nível para bancos de dados
│   └── clients/
│       ├── __init__.py
│       ├── base.py            # DBManager com seleção dinâmica de engine
│       ├── oracle.py          # Client Oracle (oracledb)
│       └── postgres.py        # Client PostgreSQL (psycopg2)
├── engine/
│   ├── __init__.py
│   ├── flow.py                # Decorator build_flow (flow Prefect + hooks)
│   ├── runtime.py             # Contexto de execução (ContextVar)
│   └── task.py                # Decorator ff_task (task adaptativa)
├── hooks/
│   ├── __init__.py
│   ├── env.py                 # Hook de tag de ambiente (PRD/DEV)
│   ├── identity.py            # Hooks de identidade (OS user + JWT)
│   ├── keyvault.py            # Hook de secrets via Key Vault
│   ├── system.py              # Hook de tag de sistema operacional
│   └── tagging.py             # Hook de tag de hostname
├── io/
│   ├── __init__.py
│   ├── file_manager.py        # Gerenciamento de arquivos local
│   └── remote_manager.py      # Gerenciamento de arquivos remoto (SSH/SFTP)
├── messaging/
│   ├── __init__.py
│   └── clients/
│       ├── __init__.py
│       ├── base.py            # Classe-base abstrata (ABC) de mensageria
│       ├── email.py           # Client de e-mail (SMTP)
│       └── telegram.py        # Client Telegram (python-telegram-bot)
├── storage/
│   ├── __init__.py
│   └── minio_manager.py      # Integração com MinIO (S3-compatible)
├── utils/
│   ├── __init__.py
│   └── env.py                # Configuração de ambiente (.env / dotenv)
├── test_flows/
│   └── example.py
├── tests/
├── pyproject.toml
└── README.md
```

---

## 📦 Módulos

### `core.config` — Configuração de Variáveis de Ambiente

Fornece funções utilitárias para leitura segura de variáveis de ambiente com tipagem:

- **`env(key, default)`** — Obtém uma variável de ambiente como `str`. Levanta `RuntimeError` se não existir e não houver valor padrão.
- **`env_bool(key, default)`** — Interpreta uma variável como booleano (`"1"`, `"true"`, `"yes"` → `True`).
- **`env_int(key, default)`** — Converte uma variável para inteiro.

---

### `db` — Camada de Abstração de Bancos de Dados

Oferece uma interface unificada para PostgreSQL e Oracle, com suporte a:

- **Leitura** (`read`) — Execução de queries SQL ou `SELECT * FROM <tabela>`, retornando listas de dicionários.
- **Merge** (`merge`) — Operações de UPSERT (`INSERT ... ON CONFLICT` no PostgreSQL, `MERGE INTO` no Oracle) ou REPLACE (`DELETE` + `INSERT`).
- **Gerenciamento de conexão** — Lazy connection, fechamento explícito.

**Classes principais:**
- **`DBManager`** (em `db/clients/base.py`) — Interface de alto nível que seleciona o client automaticamente pelo nome do engine.
- **`PostgresClient`** — Client PostgreSQL baseado em `psycopg2`.
- **`OracleClient`** — Client Oracle baseado em `oracledb`.

---

### `engine` — Motor de Orquestração (Prefect)

Integra a FastFlow com o Prefect OSS, oferecendo decorators que adicionam contexto, hooks e tags automaticamente:

- **`build_flow`** — Fábrica de decoradores para flows. Executa hooks em sequência, define contexto FastFlow e envolve a função em um flow Prefect com tags.
- **`ff_task`** — Decorator para tasks que se adapta ao contexto: dentro de um flow Prefect, roda como Prefect Task (com retries, tracking); fora, executa como função normal.
- **`get_context`** / **`get_secret`** — Acesso ao contexto e secrets carregados durante a execução do flow.

---

### `hooks` — Sistema de Plugins de Contexto

Hooks são funções executadas antes do flow que injetam informações no estado de execução:

| Hook | Descrição |
|---|---|
| `env_hook` | Adiciona tag `env:PRD` ou `env:DEV` com base no hostname |
| `os_user_hook` | Adiciona tag `user:<usuario>` com base no usuário do SO |
| `os_hook` | Adiciona tag `os:<sistema>-<versão>` (ex.: `os:windows-11`) |
| `host_tag_hook` | Adiciona tag `host:<hostname>` ou alias do servidor |
| `server_identity_hook` | Autentica via JWT com login no navegador e polling |
| `keyvault_hook` | Busca secrets no Key Vault e injeta no contexto em memória |

---

### `io` — Gerenciamento de Arquivos

#### `FileManager` (local)

Operações multiplataforma de arquivo com interfaces simples e decoradas como Prefect Tasks:

- `copy`, `move`, `delete` — Operações básicas com suporte a `overwrite`.
- `list_dir` — Listagem de diretório (recursiva opcional).
- `exists`, `size`, `modification_time` — Verificações e metadados.
- `get_file_owner` — Identifica o proprietário do arquivo (Windows via `pywin32`, Unix via `pwd`).

#### `RemoteFileManager` (SSH/SFTP)

Operações de arquivo em servidores remotos via `paramiko`:

- `connect` / `disconnect` — Gerenciamento de conexão SSH.
- `copy` (upload), `download`, `delete`, `exists`, `list_dir` — Operações SFTP.

---

### `messaging` — Sistema de Notificações

Interface unificada para envio de mensagens, extensível para múltiplos canais:

- **`BaseMessenger`** — Classe-base abstrata (ABC) que define a interface e atributos comuns (`recipient`, `send`) para todos os clients de mensageria.
- **`TelegramClient`** — Client para envio de mensagens via Telegram, utilizando `python-telegram-bot`. Lê o token do bot da variável de ambiente `TELEGRAM_BOT_TOKEN`. O método `send` é decorado com `@ff_task`.
- **`EmailClient`** — Client para envio de e-mails via SMTP com TLS. Recebe configurações de servidor, credenciais e destinatário no construtor.

---

### `storage` — Armazenamento de Objetos (MinIO)

Integração com MinIO (compatível com Amazon S3):

- **`MinioManager`** — Client para listagem de objetos e download de arquivos de buckets MinIO.

---

### `utils` — Utilitários

- **`configure_environment`** — Carrega variáveis de ambiente a partir de arquivo `.env` com três modos: `"os"`, `"dotenv"` e `"auto"`.

---

## 📖 Exemplos de Uso

### 1. Pipeline completo com flow, hooks e tasks

```python
from fastflow import (
    build_flow, ff_task,
    DBManager, FileManager, TelegramClient, MinioManager,
)
from fastflow.hooks import env_hook, os_user_hook, os_hook, host_tag_hook

# Definir tasks
@ff_task(name="extrair_dados")
def extrair_dados():
    db = DBManager("postgres")
    db.connector(user="user", password="pass", database="meu_db", host="db-host")
    dados = db.read(query="SELECT * FROM vendas WHERE ano = 2025")
    db.close()
    return dados

@ff_task(name="processar_dados")
def processar_dados(dados):
    # lógica de transformação
    return [row for row in dados if row["valor"] > 100]

@ff_task(name="notificar")
def notificar(total):
    bot = TelegramClient(recipient="CHAT_ID", bot_token="BOT_TOKEN")
    bot.send(f"Pipeline concluído! {total} registros processados.")

# Definir flow com hooks
@build_flow(
    name="pipeline-vendas",
    flow_id="vendas-2025",
    hooks=[
        env_hook(),
        os_user_hook(),
        os_hook(),
        host_tag_hook(),
    ],
)
def pipeline_vendas():
    dados = extrair_dados()
    processados = processar_dados(dados)
    notificar(len(processados))

# Executar
pipeline_vendas()
```

### 2. Operações com banco de dados

```python
from fastflow import DBManager

# PostgreSQL
db = DBManager("postgres")
db.connector(user="admin", password="secret", database="analytics", host="pg-server")

# Leitura
resultados = db.read(query="SELECT id, nome FROM clientes WHERE ativo = true")

# Merge (UPSERT)
import pandas as pd
novos_dados = pd.DataFrame([
    {"id": 1, "nome": "João", "email": "joao@example.com"},
    {"id": 2, "nome": "Maria", "email": "maria@example.com"},
])
db._client.merge(
    table="clientes",
    data=novos_dados,
    key_columns=["id"],
    update_columns=["nome", "email"],
    mode="merge",  # ou "replace"
)
db.close()
```

### 3. Gerenciamento de arquivos locais

```python
from fastflow import FileManager

# Copiar diretório
FileManager.copy("data/raw", "data/backup")

# Mover arquivo
FileManager.move("data/temp/resultado.csv", "data/processed/resultado.csv")

# Listar conteúdo recursivamente
for arquivo in FileManager.list_dir("data/processed", recursive=True):
    print(arquivo)

# Verificar tamanho e proprietário
tamanho = FileManager.size("data/processed/resultado.csv")
dono = FileManager.get_file_owner("data/processed/resultado.csv")
print(f"Tamanho: {tamanho} bytes | Proprietário: {dono}")
```

### 4. Transferência de arquivos via SSH/SFTP

```python
from fastflow import RemoteFileManager

remote = RemoteFileManager(host="192.168.1.100", username="deploy", password="secret")
remote.connect()

# Upload
remote.copy("data/relatorio.pdf", "/home/deploy/relatorios/relatorio.pdf")

# Download
remote.download("/var/log/app.log", "logs/app.log")

# Listar e verificar
arquivos = remote.list_dir("/home/deploy/relatorios")
print(arquivos)
print(remote.exists("/home/deploy/relatorios/relatorio.pdf"))

remote.disconnect()
```

### 5. Armazenamento com MinIO

```python
from fastflow import MinioManager

minio = MinioManager(
    endpoint="minio.local:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False,
)

# Listar objetos
for obj in minio.list_files("bucket-dados", prefix="2025/03/"):
    print(obj)

# Download
minio.download("bucket-dados", "2025/03/relatorio.csv", "data/relatorio.csv")
```

### 6. Hooks e contexto de execução

```python
from fastflow import build_flow, ff_task
from fastflow.hooks import env_hook, server_identity_hook, keyvault_hook
from fastflow.engine import get_context, get_secret

@build_flow(
    name="flow-com-secrets",
    hooks=[
        env_hook(),
        server_identity_hook(),
        keyvault_hook(secrets=["DB_PASSWORD", "API_KEY"]),
    ],
)
def flow_com_secrets():
    # Acessar secrets carregados pelo keyvault_hook
    ctx = get_context()
    db_password = get_secret("DB_PASSWORD")
    api_key = get_secret("API_KEY")
    print(f"Usuário: {ctx.get('user_email')}")
    # ... usar secrets no pipeline
```

---

---

[EN]

# ⚡ FastFlow

**FastFlow** is a **Python accelerators library** designed to simplify and standardize integration between data services such as **MinIO**, **databases (Oracle 11g, PostgreSQL)**, and **notification systems (Telegram, email)**.

The project also provides **cross-platform file manipulation modules** (local and remote via SSH/SFTP), a **database abstraction layer**, an extensible **hook system** for context and identity injection, and an **orchestration engine** that integrates seamlessly with **Prefect OSS**.

---

## 🚀 Overview

The library is part of the Final Course Project by **William Petterle Pfaltzgraff** (UFRJ – Computer Engineering), under the guidance of **Prof. Flávio Luis de Mello** , and was created to meet the needs of the **Laboratory of Applied Mathematics (LabMA)**, but designed for generic use by other developers and researchers.

FastFlow is intended to be used in conjunction with data flow orchestrators, such as **Prefect OSS**, serving as a foundation for task automation and reproducible data pipelines.

### Key Features

- **Database** — Unified interface for PostgreSQL and Oracle with read, write, and merge (UPSERT) support.
- **Messaging** — Send notifications via Telegram and email, with an extensible architecture for other channels.
- **Storage** — MinIO integration (S3-compatible) for object listing and download.
- **File I/O** — Local file management (copy, move, delete, list) and remote via SSH/SFTP.
- **Engine** — `build_flow` and `ff_task` decorators that wrap Prefect flows and tasks with FastFlow context.
- **Hooks** — Plugin system that automatically injects environment tags, user identity, OS information, and Key Vault secrets.
- **Configuration** — Utilities for reading environment variables with `.env` support.

---

## ⚙️ Installation

### Requirements

- Python **≥ 3.10**

### Full Installation

```bash
pip install fastflow
```

### Installation with Optional Extras

```bash
# Database only (Oracle + PostgreSQL)
pip install fastflow[db]

# Messaging only (Telegram)
pip install fastflow[messaging]

# Prefect only (orchestration engine)
pip install fastflow[prefect]

# Development tools (pytest, ruff, mypy)
pip install fastflow[dev]
```

### Installation from Source

```bash
git clone <repository>
cd fastflow
pip install -e .
```

---

## 🔧 Configuration

### Environment Variables

FastFlow can automatically load environment variables from a `.env` file:

```python
from fastflow import configure_environment

# "auto" mode: loads .env if it exists, otherwise uses OS variables
configure_environment(mode="auto")

# "dotenv" mode: requires the .env file
configure_environment(mode="dotenv", dotenv_path=".env", override=False)

# "os" mode (default): uses only operating system environment variables
configure_environment(mode="os")
```

### Environment Variables Used by FastFlow

| Variable | Description |
|---|---|
| `FASTFLOW_SERVER_HOST` | Production server hostname (used by `env_hook`, `os_user_hook`, `host_tag_hook`) |
| `FASTFLOW_SERVER_USER_TAG` | User name to tag when running on server (`os_user_hook`) |
| `FASTFLOW_AUTH_SERVER_URL` | JWT authentication server URL (`server_identity_hook`, `keyvault_hook`) |
| `FASTFLOW_AUTH_TOKEN_DIR` | JWT token cache directory (default: `~/.fastflow/tokens`) |
| `FASTFLOW_AUTH_REQUIRE` | If `"1"` / `"true"`, makes authentication mandatory |
| `FASTFLOW_JWT` | Path to JWT file or direct token (used by `keyvault_hook`) |

---

## 🧠 Project Structure

```
fastflow/
├── __init__.py
├── version.py
├── py.typed
├── core/
│   └── config.py              # Environment variable reading utilities
├── db/
│   ├── __init__.py
│   ├── manager.py             # High-level database facade
│   └── clients/
│       ├── __init__.py
│       ├── base.py            # DBManager with dynamic engine selection
│       ├── oracle.py          # Oracle client (oracledb)
│       └── postgres.py        # PostgreSQL client (psycopg2)
├── engine/
│   ├── __init__.py
│   ├── flow.py                # build_flow decorator (Prefect flow + hooks)
│   ├── runtime.py             # Execution context (ContextVar)
│   └── task.py                # ff_task decorator (adaptive task)
├── hooks/
│   ├── __init__.py
│   ├── env.py                 # Environment tag hook (PRD/DEV)
│   ├── identity.py            # Identity hooks (OS user + JWT)
│   ├── keyvault.py            # Key Vault secrets hook
│   ├── system.py              # Operating system tag hook
│   └── tagging.py             # Hostname tag hook
├── io/
│   ├── __init__.py
│   ├── file_manager.py        # Local file management
│   └── remote_manager.py      # Remote file management (SSH/SFTP)
├── messaging/
│   ├── __init__.py
│   └── clients/
│       ├── __init__.py
│       ├── base.py            # Abstract base class (ABC) for messaging
│       ├── email.py           # Email client (SMTP)
│       └── telegram.py        # Telegram client (python-telegram-bot)
├── storage/
│   ├── __init__.py
│   └── minio_manager.py      # MinIO integration (S3-compatible)
├── utils/
│   ├── __init__.py
│   └── env.py                # Environment configuration (.env / dotenv)
├── test_flows/
│   └── example.py
├── tests/
├── pyproject.toml
└── README.md
```

---

## 📦 Modules

### `core.config` — Environment Variable Configuration

Provides utility functions for safe, typed reading of environment variables:

- **`env(key, default)`** — Gets an environment variable as `str`. Raises `RuntimeError` if not set and no default provided.
- **`env_bool(key, default)`** — Interprets a variable as boolean (`"1"`, `"true"`, `"yes"` → `True`).
- **`env_int(key, default)`** — Converts a variable to integer.

---

### `db` — Database Abstraction Layer

Provides a unified interface for PostgreSQL and Oracle, supporting:

- **Read** (`read`) — SQL query execution or `SELECT * FROM <table>`, returning lists of dictionaries.
- **Merge** (`merge`) — UPSERT operations (`INSERT ... ON CONFLICT` in PostgreSQL, `MERGE INTO` in Oracle) or REPLACE (`DELETE` + `INSERT`).
- **Connection management** — Lazy connection, explicit close.

**Main classes:**
- **`DBManager`** (in `db/clients/base.py`) — High-level interface that automatically selects the client by engine name.
- **`PostgresClient`** — PostgreSQL client based on `psycopg2`.
- **`OracleClient`** — Oracle client based on `oracledb`.

---

### `engine` — Orchestration Engine (Prefect)

Integrates FastFlow with Prefect OSS, providing decorators that automatically add context, hooks, and tags:

- **`build_flow`** — Flow decorator factory. Executes hooks sequentially, sets FastFlow context, and wraps the function in a Prefect flow with tags.
- **`ff_task`** — Task decorator that adapts to context: inside a Prefect flow, runs as a Prefect Task (with retries, tracking); outside, executes as a regular function.
- **`get_context`** / **`get_secret`** — Access to context and secrets loaded during flow execution.

---

### `hooks` — Context Plugin System

Hooks are functions executed before the flow that inject information into the execution state:

| Hook | Description |
|---|---|
| `env_hook` | Adds `env:PRD` or `env:DEV` tag based on hostname |
| `os_user_hook` | Adds `user:<username>` tag based on OS user |
| `os_hook` | Adds `os:<system>-<version>` tag (e.g., `os:windows-11`) |
| `host_tag_hook` | Adds `host:<hostname>` tag or server alias |
| `server_identity_hook` | Authenticates via JWT with browser login and polling |
| `keyvault_hook` | Fetches secrets from Key Vault and injects into in-memory context |

---

### `io` — File Management

#### `FileManager` (local)

Cross-platform file operations with simple interfaces decorated as Prefect Tasks:

- `copy`, `move`, `delete` — Basic operations with `overwrite` support.
- `list_dir` — Directory listing (optional recursive).
- `exists`, `size`, `modification_time` — Checks and metadata.
- `get_file_owner` — Identifies file owner (Windows via `pywin32`, Unix via `pwd`).

#### `RemoteFileManager` (SSH/SFTP)

File operations on remote hosts via `paramiko`:

- `connect` / `disconnect` — SSH connection management.
- `copy` (upload), `download`, `delete`, `exists`, `list_dir` — SFTP operations.

---

### `messaging` — Notification System

Unified interface for sending messages, extensible to multiple channels:

- **`BaseMessenger`** — Abstract base class (ABC) that defines common attributes (`recipient`, `send`) for all messaging clients.
- **`TelegramClient`** — Client for sending messages via Telegram using `python-telegram-bot`. Reads the bot token from the `TELEGRAM_BOT_TOKEN` environment variable. The `send` method is decorated with `@ff_task`.
- **`EmailClient`** — Client for sending emails via SMTP with TLS. Receives server settings, credentials, and recipient in the constructor.

---

### `storage` — Object Storage (MinIO)

MinIO integration (Amazon S3-compatible):

- **`MinioManager`** — Client for listing objects and downloading files from MinIO buckets.

---

### `utils` — Utilities

- **`configure_environment`** — Loads environment variables from a `.env` file with three modes: `"os"`, `"dotenv"`, and `"auto"`.

---

## 📖 Usage Examples

### 1. Complete Pipeline with Flow, Hooks, and Tasks

```python
from fastflow import (
    build_flow, ff_task,
    DBManager, FileManager, TelegramClient, MinioManager,
)
from fastflow.hooks import env_hook, os_user_hook, os_hook, host_tag_hook

# Define tasks
@ff_task(name="extract_data")
def extract_data():
    db = DBManager("postgres")
    db.connector(user="user", password="pass", database="my_db", host="db-host")
    data = db.read(query="SELECT * FROM sales WHERE year = 2025")
    db.close()
    return data

@ff_task(name="process_data")
def process_data(data):
    # transformation logic
    return [row for row in data if row["amount"] > 100]

@ff_task(name="notify")
def notify(total):
    bot = TelegramClient(recipient="CHAT_ID", bot_token="BOT_TOKEN")
    bot.send(f"Pipeline completed! {total} records processed.")

# Define flow with hooks
@build_flow(
    name="sales-pipeline",
    flow_id="sales-2025",
    hooks=[
        env_hook(),
        os_user_hook(),
        os_hook(),
        host_tag_hook(),
    ],
)
def sales_pipeline():
    data = extract_data()
    processed = process_data(data)
    notify(len(processed))

# Execute
sales_pipeline()
```

### 2. Database Operations

```python
from fastflow import DBManager

# PostgreSQL
db = DBManager("postgres")
db.connector(user="admin", password="secret", database="analytics", host="pg-server")

# Read
results = db.read(query="SELECT id, name FROM clients WHERE active = true")

# Merge (UPSERT)
import pandas as pd
new_data = pd.DataFrame([
    {"id": 1, "name": "John", "email": "john@example.com"},
    {"id": 2, "name": "Mary", "email": "mary@example.com"},
])
db._client.merge(
    table="clients",
    data=new_data,
    key_columns=["id"],
    update_columns=["name", "email"],
    mode="merge",  # or "replace"
)
db.close()
```

### 3. Local File Management

```python
from fastflow import FileManager

# Copy directory
FileManager.copy("data/raw", "data/backup")

# Move file
FileManager.move("data/temp/result.csv", "data/processed/result.csv")

# List contents recursively
for file in FileManager.list_dir("data/processed", recursive=True):
    print(file)

# Check size and owner
size = FileManager.size("data/processed/result.csv")
owner = FileManager.get_file_owner("data/processed/result.csv")
print(f"Size: {size} bytes | Owner: {owner}")
```

### 4. File Transfer via SSH/SFTP

```python
from fastflow import RemoteFileManager

remote = RemoteFileManager(host="192.168.1.100", username="deploy", password="secret")
remote.connect()

# Upload
remote.copy("data/report.pdf", "/home/deploy/reports/report.pdf")

# Download
remote.download("/var/log/app.log", "logs/app.log")

# List and check
files = remote.list_dir("/home/deploy/reports")
print(files)
print(remote.exists("/home/deploy/reports/report.pdf"))

remote.disconnect()
```

### 5. Object Storage with MinIO

```python
from fastflow import MinioManager

minio = MinioManager(
    endpoint="minio.local:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False,
)

# List objects
for obj in minio.list_files("data-bucket", prefix="2025/03/"):
    print(obj)

# Download
minio.download("data-bucket", "2025/03/report.csv", "data/report.csv")
```

### 6. Hooks and Execution Context

```python
from fastflow import build_flow, ff_task
from fastflow.hooks import env_hook, server_identity_hook, keyvault_hook
from fastflow.engine import get_context, get_secret

@build_flow(
    name="flow-with-secrets",
    hooks=[
        env_hook(),
        server_identity_hook(),
        keyvault_hook(secrets=["DB_PASSWORD", "API_KEY"]),
    ],
)
def flow_with_secrets():
    # Access secrets loaded by keyvault_hook
    ctx = get_context()
    db_password = get_secret("DB_PASSWORD")
    api_key = get_secret("API_KEY")
    print(f"User: {ctx.get('user_email')}")
    # ... use secrets in pipeline
```

---
