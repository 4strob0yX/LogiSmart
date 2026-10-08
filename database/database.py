# ============================================================
# PERSISTENCIA Y SERVICIO DE BASE DE DATOS MONGODB
# ============================================================
# Módulo: database.py
# Gestiona colecciones, operaciones CRUD, agregaciones y
# tolerancia a fallos con modo offline/memoria transparente.
# ============================================================
import os
import sys
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import (
    MONGO_URI, MONGO_DB_NAME,
    COL_CAMIONES, COL_ACCESOS, COL_INCIDENTES,
    COL_RIESGOS, COL_EVAL_LLM
)



class BaseDeDatosLogiSmart:
    """
    Controlador de persistencia para LogiSmart. Soporta MongoDB Atlas,
    Compass local y almacenamiento en memoria de respaldo si no hay red.
    """

    def __init__(self):
        self.conectado = False
        self.usando_memoria = False
        self.error_conexion = None
        self.client = None
        self.db = None

        # Almacenamiento en memoria para modo fallback/offline
        self._memoria: Dict[str, List[Dict[str, Any]]] = {
            COL_CAMIONES: [],
            COL_ACCESOS: [],
            COL_INCIDENTES: [],
            COL_RIESGOS: [],
            COL_EVAL_LLM: []
        }

        self._iniciar_conexion()

    def _iniciar_conexion(self):
        """
        Intenta conectar:
        1. Primero a MongoDB Atlas (MONGO_URI)
        2. Si falla DNS/red, conecta a la instancia local de MongoDB (127.0.0.1:27017)
        3. Si ninguna está disponible, activa el mock en memoria transparente.
        """
        # Intento 1: MongoDB Atlas
        try:
            self.client = pymongo.MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000
            )
            self.client.admin.command('ping')
            self.db = self.client[MONGO_DB_NAME]
            self.conectado = True
            self.usando_memoria = False
            self.modo_conexion = "MongoDB Atlas En Vivo"
            self.error_conexion = None
            print(f"[MongoDB] Conectado exitosamente a MongoDB Atlas: {MONGO_DB_NAME}")
            return
        except Exception as e_atlas:
            pass

        # Intento 2: MongoDB Local en puerto 27017
        try:
            self.client = pymongo.MongoClient(
                "mongodb://127.0.0.1:27017/",
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000
            )
            self.client.admin.command('ping')
            self.db = self.client[MONGO_DB_NAME]
            self.conectado = True
            self.usando_memoria = False
            self.modo_conexion = "MongoDB Local (localhost:27017)"
            self.error_conexion = None
            print(f"[MongoDB] Conectado exitosamente a MongoDB Local (localhost:27017) -> DB: '{MONGO_DB_NAME}'")
            return
        except Exception as e_local:
            pass

        # Intento 3: Mock transparente en memoria
        self.conectado = False
        self.usando_memoria = True
        self.modo_conexion = "Almacenamiento Local en Memoria (Fallback)"
        self.error_conexion = "No se pudo conectar a Atlas ni a MongoDB Local"
        print("[MongoDB] Activando MOCK EN MEMORIA transparente.")

    def obtener_estado_conexion(self) -> Dict[str, Any]:
        """Informa si está usando MongoDB Atlas, Local o la réplica en memoria."""
        return {
            "conectado": self.conectado,
            "modo": getattr(self, "modo_conexion", "Almacenamiento en Memoria"),
            "db_name": MONGO_DB_NAME,
            "error": self.error_conexion
        }

    # ========================================================
    # 1. COLECCIÓN: CAMIONES (CRUD)
    # ========================================================

    def registrar_camion(self, datos: Dict[str, Any]) -> str:
        camion = {
            "_id": datos.get("camion_id") or str(uuid.uuid4())[:8].upper(),
            "camion_id": datos.get("camion_id") or f"CAM-{uuid.uuid4().hex[:4].upper()}",
            "placa": datos.get("placa", "").strip().upper(),
            "empresa": datos.get("empresa", "Logística Express"),
            "autorizacion": bool(datos.get("autorizacion", True)),
            "certificacion_conductor": bool(datos.get("certificacion_conductor", True)),
            "conductor_nombre": datos.get("conductor_nombre", "Operador Asignado"),
            "fecha_registro": datetime.now().isoformat()
        }

        if self.conectado:
            try:
                self.db[COL_CAMIONES].replace_one(
                    {"placa": camion["placa"]}, camion, upsert=True
                )
                return camion["_id"]
            except Exception:
                pass

        # Fallback en memoria
        existente = next((c for c in self._memoria[COL_CAMIONES] if c["placa"] == camion["placa"]), None)
        if existente:
            existente.update(camion)
        else:
            self._memoria[COL_CAMIONES].append(camion)
        return camion["_id"]

    def buscar_camion_por_placa(self, placa: str) -> Optional[Dict[str, Any]]:
        placa_limpia = placa.strip().upper()
        if self.conectado:
            try:
                doc = self.db[COL_CAMIONES].find_one({"placa": placa_limpia})
                if doc:
                    doc["_id"] = str(doc["_id"])
                    return doc
            except Exception:
                pass

        return next((c for c in self._memoria[COL_CAMIONES] if c["placa"] == placa_limpia), None)

    def listar_camiones(self) -> List[Dict[str, Any]]:
        if self.conectado:
            try:
                docs = list(self.db[COL_CAMIONES].find())
                for d in docs:
                    d["_id"] = str(d["_id"])
                return docs
            except Exception:
                pass
        return self._memoria[COL_CAMIONES]

    # ========================================================
    # 2. COLECCIÓN: ACCESOS (Bitácora inmutable de garita)
    # ========================================================

    def registrar_acceso(self, bitacora: Dict[str, Any]) -> str:
        registro = {
            "_id": str(uuid.uuid4()),
            "marca_de_tiempo": datetime.now().isoformat(),
            "camion_id": bitacora.get("camion_id", "DESCONOCIDO"),
            "placa": bitacora.get("placa", "N/A"),
            "operador": bitacora.get("operador", "Guardia de Garita"),
            # Vector proposicional
            "P": bool(bitacora.get("P", False)),
            "Q": bool(bitacora.get("Q", False)),
            "R": bool(bitacora.get("R", False)),
            "S": bool(bitacora.get("S", False)),
            "T": bool(bitacora.get("T", False)),
            "M": bool(bitacora.get("M", True)),
            # Resultados
            "resultado_A": bool(bitacora.get("resultado_A", False)),
            "resultado_E": bool(bitacora.get("resultado_E", False)),
            "semaforo": bitacora.get("semaforo", "ROJO"),
            "decision": bitacora.get("decision", "DENEGADO"),
            "explicacion_paso_a_paso": bitacora.get("explicacion_paso_a_paso", [])
        }

        if self.conectado:
            try:
                self.db[COL_ACCESOS].insert_one(registro)
                registro["_id"] = str(registro["_id"])
                return registro["_id"]
            except Exception:
                pass

        self._memoria[COL_ACCESOS].append(registro)
        return registro["_id"]

    def listar_accesos(self, limite: int = 50) -> List[Dict[str, Any]]:
        if self.conectado:
            try:
                docs = list(self.db[COL_ACCESOS].find().sort("marca_de_tiempo", -1).limit(limite))
                for d in docs:
                    d["_id"] = str(d["_id"])
                return docs
            except Exception:
                pass
        return sorted(self._memoria[COL_ACCESOS], key=lambda x: x["marca_de_tiempo"], reverse=True)[:limite]

    # ========================================================
    # 3. COLECCIÓN: INCIDENTES (Bandeja, Clasificación, Estados)
    # ========================================================

    def registrar_incidente(self, incidente: Dict[str, Any]) -> str:
        doc = {
            "_id": str(uuid.uuid4()),
            "correo_original": incidente.get("correo_original", ""),
            "categoria": incidente.get("categoria", "Control de Acceso"),
            "prioridad": incidente.get("prioridad", "MEDIA"),
            "datos_extraidos": incidente.get("datos_extraidos", {}),
            "resumen": incidente.get("resumen", ""),
            "estado": incidente.get("estado", "nuevo"),  # 'nuevo', 'en_atencion', 'cerrado'
            "requiere_revision_humana": bool(incidente.get("requiere_revision_humana", False)),
            "fecha_reporte": datetime.now().isoformat(),
            "semana_del_ano": datetime.now().isocalendar()[1]
        }

        if self.conectado:
            try:
                self.db[COL_INCIDENTES].insert_one(doc)
                doc["_id"] = str(doc["_id"])
                return doc["_id"]
            except Exception:
                pass

        self._memoria[COL_INCIDENTES].append(doc)
        return doc["_id"]

    def actualizar_estado_incidente(self, incidente_id: str, nuevo_estado: str, notas: Optional[str] = None) -> bool:
        if nuevo_estado not in ["nuevo", "en_atencion", "cerrado"]:
            return False

        update_dict = {"estado": nuevo_estado}
        if notas:
            update_dict["notas_seguimiento"] = notas

        if self.conectado:
            try:
                res = self.db[COL_INCIDENTES].update_one({"_id": incidente_id}, {"$set": update_dict})
                return res.modified_count > 0
            except Exception:
                pass

        for inc in self._memoria[COL_INCIDENTES]:
            if inc["_id"] == incidente_id:
                inc.update(update_dict)
                return True
        return False

    def listar_incidentes(self, filtro_estado: Optional[str] = None) -> List[Dict[str, Any]]:
        query = {"estado": filtro_estado} if filtro_estado else {}
        if self.conectado:
            try:
                docs = list(self.db[COL_INCIDENTES].find(query).sort("fecha_reporte", -1))
                for d in docs:
                    d["_id"] = str(d["_id"])
                return docs
            except Exception:
                pass

        lista = self._memoria[COL_INCIDENTES]
        if filtro_estado:
            lista = [i for i in lista if i.get("estado") == filtro_estado]
        return sorted(lista, key=lambda x: x.get("fecha_reporte", ""), reverse=True)

    # ========================================================
    # AGREGACIÓN OBLIGATORIA: INCIDENTES POR CATEGORÍA Y SEMANA
    # ========================================================

    def agregacion_incidentes_por_categoria_y_semana(self) -> List[Dict[str, Any]]:
        """
        Ejecuta el pipeline de agregación en MongoDB:
        Agrupa los incidentes por categoría y semana del año, calculando
        el total y el desglose de prioridades críticas.
        """
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "categoria": "$categoria",
                        "semana": "$semana_del_ano"
                    },
                    "total_incidentes": {"$sum": 1},
                    "criticos": {
                        "$sum": {
                            "$cond": [{"$eq": ["$prioridad", "CRITICA"]}, 1, 0]
                        }
                    },
                    "altos": {
                        "$sum": {
                            "$cond": [{"$eq": ["$prioridad", "ALTA"]}, 1, 0]
                        }
                    }
                }
            },
            {"$sort": {"_id.semana": -1, "total_incidentes": -1}}
        ]

        if self.conectado:
            try:
                resultados = list(self.db[COL_INCIDENTES].aggregate(pipeline))
                formateados = []
                for r in resultados:
                    formateados.append({
                        "categoria": r["_id"].get("categoria", "Sin Categoría"),
                        "semana": r["_id"].get("semana", 1),
                        "total_incidentes": r["total_incidentes"],
                        "criticos": r["criticos"],
                        "altos": r["altos"]
                    })
                return formateados
            except Exception:
                pass

        # Réplica algorítmica de la agregación en memoria
        conteo: Dict[Tuple, Dict[str, Any]] = {}
        for inc in self._memoria[COL_INCIDENTES]:
            cat = inc.get("categoria", "General")
            sem = inc.get("semana_del_ano", 40)
            llave = (cat, sem)
            if llave not in conteo:
                conteo[llave] = {"total_incidentes": 0, "criticos": 0, "altos": 0}
            conteo[llave]["total_incidentes"] += 1
            if inc.get("prioridad") == "CRITICA":
                conteo[llave]["criticos"] += 1
            elif inc.get("prioridad") == "ALTA":
                conteo[llave]["altos"] += 1

        resultado_mem = []
        for (cat, sem), datos in conteo.items():
            resultado_mem.append({
                "categoria": cat,
                "semana": sem,
                "total_incidentes": datos["total_incidentes"],
                "criticos": datos["criticos"],
                "altos": datos["altos"]
            })
        return sorted(resultado_mem, key=lambda x: x["total_incidentes"], reverse=True)

    # ========================================================
    # 4. COLECCIÓN: RIESGOS ÉTICOS (CRUD + Residual)
    # ========================================================

    def registrar_riesgo_etico(self, riesgo: Dict[str, Any]) -> str:
        doc = {
            "_id": riesgo.get("_id") or str(uuid.uuid4())[:8],
            "modulo": riesgo.get("modulo", "Control Central"),
            "descripcion": riesgo.get("descripcion", ""),
            "categoria": riesgo.get("categoria", "Ético"),
            "probabilidad": int(riesgo.get("probabilidad", 3)),       # 1 a 5
            "impacto": int(riesgo.get("impacto", 4)),                   # 1 a 5
            "riesgo_inherente_score": int(riesgo.get("probabilidad", 3)) * int(riesgo.get("impacto", 4)),
            "mitigacion": riesgo.get("mitigacion", ""),
            "probabilidad_residual": int(riesgo.get("probabilidad_residual", 1)),
            "impacto_residual": int(riesgo.get("impacto_residual", 2)),
            "riesgo_residual_score": int(riesgo.get("probabilidad_residual", 1)) * int(riesgo.get("impacto_residual", 2)),
            "historico": riesgo.get("historico", [f"Registrado {datetime.now().strftime('%Y-%m-%d')}"])
        }

        if self.conectado:
            try:
                self.db[COL_RIESGOS].replace_one({"_id": doc["_id"]}, doc, upsert=True)
                return doc["_id"]
            except Exception:
                pass

        existente = next((r for r in self._memoria[COL_RIESGOS] if r["_id"] == doc["_id"]), None)
        if existente:
            existente.update(doc)
        else:
            self._memoria[COL_RIESGOS].append(doc)
        return doc["_id"]

    def listar_riesgos_eticos(self) -> List[Dict[str, Any]]:
        if self.conectado:
            try:
                docs = list(self.db[COL_RIESGOS].find())
                for d in docs:
                    d["_id"] = str(d["_id"])
                return docs
            except Exception:
                pass
        return self._memoria[COL_RIESGOS]

    # ========================================================
    # 5. COLECCIÓN: EVALUACIONES LLM
    # ========================================================

    def registrar_evaluacion_llm(self, evaluacion: Dict[str, Any]) -> str:
        doc = {
            "_id": str(uuid.uuid4()),
            "prompt": evaluacion.get("prompt", ""),
            "respuesta": evaluacion.get("respuesta", {}),
            "modelo": evaluacion.get("modelo", "llama3.2"),
            "latencia_ms": evaluacion.get("latencia_ms", 0.0),
            "coincidio_con_reglas": bool(evaluacion.get("coincidio_con_reglas", True)),
            "fecha": datetime.now().isoformat()
        }

        if self.conectado:
            try:
                self.db[COL_EVAL_LLM].insert_one(doc)
                doc["_id"] = str(doc["_id"])
                return doc["_id"]
            except Exception:
                pass

        self._memoria[COL_EVAL_LLM].append(doc)
        return doc["_id"]

    def obtener_resumen_colecciones(self) -> Dict[str, Any]:
        """Devuelve el conteo y nombres de las 5 colecciones de MongoDB."""
        colecciones = [COL_CAMIONES, COL_ACCESOS, COL_INCIDENTES, COL_RIESGOS, COL_EVAL_LLM]
        resumen = {}
        for col in colecciones:
            if self.conectado:
                try:
                    resumen[col] = self.db[col].count_documents({})
                except Exception:
                    resumen[col] = len(self._memoria.get(col, []))
            else:
                resumen[col] = len(self._memoria.get(col, []))
        return resumen

    def obtener_documentos_coleccion(self, nombre_col: str, limite: int = 50) -> List[Dict[str, Any]]:
        """Devuelve los documentos de una colección en MongoDB."""
        if self.conectado:
            try:
                docs = list(self.db[nombre_col].find().sort([("_id", -1)]).limit(limite))
                for d in docs:
                    d["_id"] = str(d["_id"])
                return docs
            except Exception:
                pass
        return self._memoria.get(nombre_col, [])[:limite]


# Instancia singleton para acceso transversal en la app
db_servicio = BaseDeDatosLogiSmart()


if __name__ == "__main__":
    print("=== ESTADO DE MONGODB LOGISMART ===")
    print(db_servicio.obtener_estado_conexion())
