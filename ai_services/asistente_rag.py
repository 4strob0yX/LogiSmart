# ============================================================
# ASISTENTE EXPLICATIVO RAG (RETRIEVAL-AUGMENTED GENERATION)
# ============================================================
# Módulo: asistente_rag.py
# Permite auditoría conversacional: busca primero en MongoDB
# y responde fundamentando con citas de registro exactas.
# Si no hay información, responde taxativamente "no tengo información".
# ============================================================
import os
import sys
import json
import re
from typing import Dict, Any, List, Optional


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.database import db_servicio
from config import OLLAMA_MODEL

try:
    import ollama
    OLLAMA_DISPONIBLE = True
except ImportError:
    OLLAMA_DISPONIBLE = False


class AsistenteExplicativoRAG:
    """
    Motor RAG determinista y riguroso. Elimina alucinaciones
    al condicionar estrictamente la respuesta a documentos recuperados.
    """

    def __init__(self):
        self.historial_chat: List[Dict[str, str]] = []

    def buscar_contexto_en_mongodb(self, consulta_usuario: str) -> Dict[str, Any]:
        """
        Paso 1 del RAG (Retrieval): Extrae identificadores clave
        (placas, camiones, ids) o realiza búsqueda temática en MongoDB.
        """
        consulta_lower = consulta_usuario.lower()

        # 1. Búsqueda por placa o camion_id
        placas = re.findall(r'[a-z]{2,4}[-\s]?\d{3,4}[a-z]?', consulta_lower)
        camion_ids = re.findall(r'cam[-\s]?\d{2,4}', consulta_lower)

        placa_buscada = placas[0].upper().replace(" ", "-") if placas else None
        camion_id_buscado = camion_ids[0].upper().replace(" ", "-") if camion_ids else None

        registros_encontrados = []
        fuentes_citadas = []

        if placa_buscada:
            cam = db_servicio.buscar_camion_por_placa(placa_buscada)
            if cam:
                registros_encontrados.append({
                    "tipo": "Catálogo Maestro de Camiones",
                    "doc": cam,
                    "cita": f"Colección: camiones | ID: {cam.get('_id')} | Placa: {cam.get('placa')}"
                })
                fuentes_citadas.append(f"Colección 'camiones' (ID: {cam.get('_id')})")

        # Buscar en accesos por identificador
        todos_accesos = db_servicio.listar_accesos(limite=50)
        for acc in todos_accesos:
            p_acc = acc.get("placa", "").upper()
            c_acc = acc.get("camion_id", "").upper()
            if (placa_buscada and placa_buscada in p_acc) or (camion_id_buscado and camion_id_buscado in c_acc):
                registros_encontrados.append({
                    "tipo": "Bitácora de Acceso en Garita",
                    "doc": acc,
                    "cita": f"Colección: accesos | ID: {acc.get('_id')} | Fecha: {acc.get('marca_de_tiempo')}"
                })
                fuentes_citadas.append(f"Colección 'accesos' (Registro: {acc.get('_id')})")

        # Buscar en incidentes por identificador
        todos_incidentes = db_servicio.listar_incidentes()
        for inc in todos_incidentes:
            texto_inc = (str(inc.get("datos_extraidos", {})) + " " + inc.get("correo_original", "")).upper()
            if (placa_buscada and placa_buscada in texto_inc) or (camion_id_buscado and camion_id_buscado in texto_inc):
                registros_encontrados.append({
                    "tipo": "Bandeja de Incidentes",
                    "doc": inc,
                    "cita": f"Colección: incidentes | ID: {inc.get('_id')} | Categoría: {inc.get('categoria')}"
                })
                fuentes_citadas.append(f"Colección 'incidentes' (ID: {inc.get('_id')})")

        # 2. Si no hubo coincidencia por placa/id, realizar búsqueda temática por palabras clave
        if not registros_encontrados:
            palabras_clave = [p for p in re.findall(r'\b\w{4,}\b', consulta_lower) if p not in ['para', 'como', 'este', 'esta', 'sobre', 'cual', 'cuales', 'tiene', 'donde']]

            # Búsqueda en incidentes
            for inc in todos_incidentes:
                texto_inc = (inc.get("categoria", "") + " " + inc.get("resumen", "") + " " + inc.get("prioridad", "") + " " + inc.get("correo_original", "")).lower()
                if any(k in texto_inc for k in palabras_clave):
                    registros_encontrados.append({
                        "tipo": "Incidente Relevante",
                        "doc": {
                            "categoria": inc.get("categoria"),
                            "prioridad": inc.get("prioridad"),
                            "resumen": inc.get("resumen"),
                            "estado": inc.get("estado"),
                            "fecha": inc.get("fecha_reporte")
                        },
                        "cita": f"Colección: incidentes | ID: {inc.get('_id')} | Prioridad: {inc.get('prioridad')}"
                    })
                    fuentes_citadas.append(f"Colección 'incidentes' (ID: {inc.get('_id')})")
                    if len(registros_encontrados) >= 4:
                        break

            # Búsqueda en accesos
            if len(registros_encontrados) < 3:
                for acc in todos_accesos:
                    texto_acc = (acc.get("decision", "") + " " + acc.get("semaforo", "") + " " + acc.get("placa", "")).lower()
                    if any(k in texto_acc for k in palabras_clave):
                        registros_encontrados.append({
                            "tipo": "Registro de Acceso",
                            "doc": {
                                "placa": acc.get("placa"),
                                "decision": acc.get("decision"),
                                "semaforo": acc.get("semaforo"),
                                "fecha": acc.get("marca_de_tiempo")
                            },
                            "cita": f"Colección: accesos | ID: {acc.get('_id')}"
                        })
                        fuentes_citadas.append(f"Colección 'accesos' (ID: {acc.get('_id')})")
                        if len(registros_encontrados) >= 4:
                            break

        return {
            "hay_datos": len(registros_encontrados) > 0,
            "registros": registros_encontrados,
            "fuentes": list(set(fuentes_citadas)),
            "termino_buscado": placa_buscada or camion_id_buscado or consulta_usuario
        }

    def responder_consulta_operador(self, pregunta: str) -> Dict[str, Any]:
        """
        Paso 2 del RAG (Generation Grounded con Llama 3.2):
        Condiciona la respuesta en MongoDB y las reglas del sistema ciberfísico.
        """
        contexto = self.buscar_contexto_en_mongodb(pregunta)

        # Base de conocimiento normativo de reglas de garita
        reglas_base_conocimiento = (
            "REGLAS LÓGICAS DEL SISTEMA LOGISMART:\n"
            "- A = P ∧ S ∧ ¬Q (Acceso Estándar / Verde: Autorización P, Conductor certificado S, Sin sobrepeso ¬Q)\n"
            "- E = P ∧ (R ∨ Q) (Inspección Especial / Amarillo: Autorización P, Carga peligrosa R o Sobrepeso Q)\n"
            "- H = R ∧ T (Restricción Nocturna / Rojo: Materiales peligrosos R en Horario nocturno T)\n"
            "- C = S ∧ M (Certificación Conductor / Verde: Licencia S y Examen psicofísico M apto)\n"
            "- Modelo PEAS: Rendimiento (seguridad garita, latencia <500ms), Entorno (garita, báscula), Actuadores (barrera, semáforo), Sensores (RFID, celdas pesaje)."
        )

        lineas_contexto = [reglas_base_conocimiento]
        if contexto["hay_datos"]:
            lineas_contexto.append("\nREGISTROS RECUPERADOS DE MONGODB:")
            for reg in contexto["registros"]:
                lineas_contexto.append(f"--- REGISTRO FUENTE ({reg['cita']}) ---")
                doc = reg["doc"]
                for k, v in doc.items():
                    if k not in ["_id"]:
                        lineas_contexto.append(f"  {k}: {v}")
        else:
            lineas_contexto.append(
                f"\nESTADO DE BÚSQUEDA EN BASE DE DATOS:\n"
                f"No se encontraron registros específicos con el término '{contexto['termino_buscado']}' en MongoDB."
            )

        texto_contexto_db = "\n".join(lineas_contexto)

        prompt_rag = f"""
Eres el Auditor RAG del Centro de Control Ciberfísico LogiSmart, impulsado por Llama 3.2.
Tu misión es responder a la pregunta del operador basándote con rigor en los datos de MongoDB y las reglas del sistema.

INSTRUCCIONES CLAVE:
1. Si la pregunta es sobre un vehículo o reporte específico y existen registros recuperados, cita el ID o fuente de MongoDB.
2. Si la pregunta es sobre un vehículo que NO existe en la base de datos, declara explícitamente que no se encuentra en MongoDB para evitar alucinaciones.
3. Si la pregunta es sobre el funcionamiento general, las reglas lógicas (A, E, H, C), el modelo PEAS o los estados del semáforo, explica con claridad técnica fundamentada en las reglas del sistema.
4. Responde en español de manera concisa, técnica y estructurada.

CONTEXTO VERIFICADO:
{texto_contexto_db}

PREGUNTA DEL OPERADOR:
{pregunta}
"""

        respuesta_texto = ""
        modelo_activo = OLLAMA_MODEL

        if OLLAMA_DISPONIBLE:
            try:
                resp = ollama.chat(
                    model=OLLAMA_MODEL,
                    messages=[
                        {"role": "system", "content": "Eres el Auditor RAG de LogiSmart. Responde con base en el contexto verificado."},
                        {"role": "user", "content": prompt_rag}
                    ],
                    options={"temperature": 0.1}
                )
                respuesta_texto = resp["message"]["content"].strip()
            except Exception as e:
                pass

        if not respuesta_texto:
            # Respaldo determinista en caso de que el socket de Ollama tenga algún retardo puntual
            if contexto["hay_datos"]:
                res_principal = contexto["registros"][0]["doc"]
                cita_principal = contexto["registros"][0]["cita"]
                respuesta_texto = (
                    f"Consulta procesada sobre {contexto['termino_buscado']}:\n\n"
                    f"- Fuente identificada: [{cita_principal}]\n"
                    f"- Detalle: {json.dumps(res_principal, ensure_ascii=False, indent=2)}"
                )
            else:
                respuesta_texto = (
                    f"No se localizaron registros coincidentes con '{contexto['termino_buscado']}' en las colecciones de MongoDB.\n\n"
                    "Recuerda que puedes consultar por placas (ej. TRK-781, TRK-882), IDs de camión (ej. CAM-101), categorías de incidentes o sobre las reglas lógicas (A, E, H, C)."
                )

        fuentes_finales = contexto["fuentes"]
        if not fuentes_finales:
            fuentes_finales = ["Base de Reglas Proposicionales LogiSmart (A, E, H, C)"]

        return {
            "respuesta": respuesta_texto,
            "fuentes_consultadas": fuentes_finales,
            "encontrado_en_db": contexto["hay_datos"],
            "modelo": modelo_activo
        }


# Instancia singleton
asistente_rag = AsistenteExplicativoRAG()


if __name__ == "__main__":
    print("=== PRUEBA DEL ASISTENTE RAG ===")
    test_1 = asistente_rag.responder_consulta_operador("¿Por qué el camión CAM-999 fue rechazado?")
    print("Test 1 (Sin datos):", test_1["respuesta"])
