[PT-BR]

# ⚡ FastFlow

A **FastFlow** é uma biblioteca de **aceleradores em Python** desenvolvida para simplificar e padronizar a integração entre serviços de dados, como **MinIO**, **bancos de dados (Oracle 11g, PostgreSQL)** e **sistemas de notificação (Telegram, e-mail)**.  

O projeto também oferece módulos de **manipulação de arquivos multiplataforma** e uma **camada de abstração de bancos de dados**, permitindo que pipelines de dados sejam desenvolvidos de forma ágil, segura e escalável.

---

## 🚀 Visão Geral

A biblioteca faz parte do Trabalho de Conclusão de Curso de **William Petterle Pfaltzgraff**, sob orientação do **Prof. Milton Ramirez** (UFRJ – Engenharia de Computação), e foi criada para atender às necessidades do **Laboratório da Matemática Aplicada (LabMA)**, mas projetada para uso genérico por outros desenvolvedores e pesquisadores.

A FastFlow foi pensada para ser usada em conjunto com orquestradores de fluxo de dados, como o **Prefect OSS**, servindo como base para automação de tarefas e pipelines de dados reprodutíveis.

---

## 🧠 Estrutura do Projeto
fastflow/
├── fastflow/
│ ├── src/
| | ├── fastflow/
│ │ | ├── core/
| | | | ├── config.py
│ │ | | ├── exceptions.py
│ │ | | ├── logging.py
│ │ | | └── types.py
│ │ | ├── db/
| | | | ├── clients/
| | | | | ├── __init__.py
| | | | | ├── base.py
| | | | | ├── oracle.py
| | | | | └── postgres.py
│ │ | | ├── __init__.py
| | | | └── manager.py
│ │ | ├── io/
| | | | ├── __init__.py
│ │ | | └── file_manager.py
│ │ | ├── messaging/
│ | | | ├── clients/
│ | | | | ├── __init__.py
│ | | | | ├── base.py
│ | | | | ├── email.py
│ | | | | └── telegram.py
│ | | | ├── __init__.py
│ │ | | └── messenger.py
│ │ | ├── storage/
│ | | | ├── __init__.py
│ | | | └── minio_manager.py
│ │ | ├── __init__.py
│ │ | └── version.py
| ├── tests/
| ├── .gitignore
| ├── .python-version
| ├── example.py
| ├── pyproject.toml
| └── README.md



---

## ⚙️ Instalação

Instale localmente via `pip`:

```bash
pip install fastflow
```



__________________________________________________________________________________________________________________________________________

[EN]

# ⚡ FastFlow

**FastFlow** is a **Python accelerators** library designed to simplify and standardize integration between data services such as **MinIO**, **databases (Oracle 11g, PostgreSQL)**, and **notification systems (Telegram, email)**.

The project also provides **cross-platform file manipulation modules** and a **database abstraction layer**, enabling the development of data pipelines in an agile, secure, and scalable manner.

---

## 🚀 Overview

The library is part of the Final Course Project by **William Petterle Pfaltzgraff**, under the guidance of **Prof. Milton Ramirez** (UFRJ – Computer Engineering), and was created to meet the needs of the **Laboratory of Applied Mathematics (LabMA)**, but designed for generic use by other developers and researchers.

FastFlow is intended to be used in conjunction with data flow orchestrators, such as **Prefect OSS**, serving as a foundation for task automation and reproducible data pipelines.

---

## 🧠 Project Structure

fastflow/
├── fastflow/
│ ├── src/
| | ├── fastflow/
│ │ | ├── core/
| | | | ├── config.py
│ │ | | ├── exceptions.py
│ │ | | ├── logging.py
│ │ | | └── types.py
│ │ | ├── db/
| | | | ├── clients/
| | | | | ├── __init__.py
| | | | | ├── base.py
| | | | | ├── oracle.py
| | | | | └── postgres.py
│ │ | | ├── __init__.py
| | | | └── manager.py
│ │ | ├── io/
| | | | ├── __init__.py
│ │ | | └── file_manager.py
│ │ | ├── messaging/
│ | | | ├── clients/
│ | | | | ├── __init__.py
│ | | | | ├── base.py
│ | | | | ├── email.py
│ | | | | └── telegram.py
│ | | | ├── __init__.py
│ │ | | └── messenger.py
│ │ | ├── storage/
│ | | | ├── __init__.py
│ | | | └── minio_manager.py
│ │ | ├── __init__.py
│ │ | └── version.py
| ├── tests/
| ├── .gitignore
| ├── .python-version
| ├── example.py
| ├── pyproject.toml
| └── README.md

---

## ⚙️ Installation

Install locally via `pip`:

```bash
pip install fastflow
```