from fastflow.io import FileManager

# DB (fachada)
db = DBManager.from_config(engine="postgres", host="localhost", user="u", password="p", database="d")
rows = list(db.read("SELECT 1 AS ok"))
db.write("schema.tabela", data=[{"a": 1}], if_exists="append")
db.close()

# Mensageria (Telegram hoje, WhatsApp amanhã)
bot = Messenger.from_config(kind="telegram", token="XXX", chat_id="123")
bot.send("Pipeline finalizado com sucesso.")

# Storage (MinIO)
minio = MinioManager(endpoint="minio.local:9000", access_key="ak", secret_key="sk")
for obj in minio.list_files("bucket-dados", prefix="2025/"):
    print("obj:", obj)

# IO (arquivos)
FileManager.copy("data/raw", "data/processed")
