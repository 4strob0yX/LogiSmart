# ============================================================
# CONFIGURACIÓN GENERAL DEL SISTEMA LOGISMART
# ============================================================
# Gestiona las variables de entorno, credenciales de MongoDB
# y parámetros del modelo LLM (Ollama).
# ============================================================

import os
from datetime import datetime

# ------------------------------------------------------------
# 1. PARÁMETROS DE MONGODB (Atlas / Local / Fallback)
# ------------------------------------------------------------
# Credenciales del clúster académico de la práctica:
MONGO_USER = os.getenv("MONGO_USER", "hector1985")
MONGO_PASS = os.getenv("MONGO_PASS", "Aime131985")
MONGO_CLUSTER = os.getenv("MONGO_CLUSTER", "utvt.qqqotrr.net")
MONGO_DB_NAME = os.getenv("MONGO_DB", "samuelD73SixSeven")

# Cadena de conexión URI a MongoDB Atlas
MONGO_URI = os.getenv(
    "MONGO_URI",
    f"mongodb+srv://{MONGO_USER}:{MONGO_PASS}@{MONGO_CLUSTER}/{MONGO_DB_NAME}?retryWrites=true&w=majority&appName=Cluster0"
)

# Nombres de las 5 colecciones mínimas requeridas:
COL_CAMIONES = "camiones"
COL_ACCESOS = "accesos"
COL_INCIDENTES = "incidentes"
COL_RIESGOS = "riesgos_eticos"
COL_EVAL_LLM = "evaluaciones_llm"

# ------------------------------------------------------------
# 2. PARÁMETROS DEL LLM (Ollama)
# ------------------------------------------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT_SEC = 8

# ------------------------------------------------------------
# 3. PARÁMETROS DEL SISTEMA LOGÍSTICO
# ------------------------------------------------------------
PESO_MAXIMO_PERMITIDO_KG = 40000.0  # 40 Toneladas (NOM-012-SCT)
HORARIO_NOCTURNO_INICIO = 22        # 10:00 PM
HORARIO_NOCTURNO_FIN = 5            # 05:00 AM
VERSION_SISTEMA = "2.4.0-Enterprise"
