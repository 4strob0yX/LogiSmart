# ============================================================
# EVALUACIÓN ÉTICA Y MATRIZ DE RIESGOS DE IA
# ============================================================
# Módulo: matriz_riesgos.py
# Modela riesgos inherentes y residuales de la implementación:
# alucinaciones, sesgo en lenguaje informal, privacidad y sobreautomatización.
# ============================================================
import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.database import db_servicio


# Los 4 riesgos éticos obligatorios de nuestra propia implementación
RIESGOS_ETICOS_INICIALES = [
    {
        "_id": "RIESGO-001",
        "modulo": "Clasificador LLM (Ollama / Llama3.2)",
        "descripcion": "Alucinación en clasificación de incidentes: el modelo inventa placas, reduce prioridad de químicos o interpreta erróneamente un incidente crítico.",
        "categoria": "Alucinación y Confiabilidad",
        "probabilidad": 4,  # Escala 1 (Raro) a 5 (Muy Frecuente)
        "impacto": 5,       # Escala 1 (Insignificante) a 5 (Catastrófico)
        "mitigacion": "Salida forzada con JSON Schema y Pydantic, verificación cruzada contra motor determinista de reglas y principio de prevalencia de seguridad.",
        "probabilidad_residual": 1,
        "impacto_residual": 2,
        "historico": ["Evaluado en fase de diseño v1.0", "Mitigación con Pydantic y Fallback aplicada v2.0"]
    },
    {
        "_id": "RIESGO-002",
        "modulo": "Procesador de Lenguaje Natural (Correos)",
        "descripcion": "Sesgo ante lenguaje informal y faltas de ortografía: reportes de choferes o guardias con modismos locales o errores tipográficos clasificados como de menor prioridad.",
        "categoria": "Sesgo y Equidad Lingüística",
        "probabilidad": 4,
        "impacto": 4,
        "mitigacion": "Normalización previa de texto, heurística por expresiones regulares tolerante a variantes ortográficas ('bascula' / 'báscula', 'toneladas' / 'tons') y dataset de calibración diverso.",
        "probabilidad_residual": 2,
        "impacto_residual": 2,
        "historico": ["Identificado durante pruebas con personal de garita", "Reglas ampliadas con sinónimos v2.1"]
    },
    {
        "_id": "RIESGO-003",
        "modulo": "Base de Datos MongoDB y Garita",
        "descripcion": "Vulneración de privacidad y fuga de datos sensibles: exposición de nombres de choferes, historiales médicos (aptitud M) y patrones de traslado de carga valiosa.",
        "categoria": "Privacidad y Protección de Datos",
        "probabilidad": 3,
        "impacto": 5,
        "mitigacion": "Almacenamiento disociado, controles de acceso por rol en MongoDB, minimización de datos (solo almacenar bandera booleana M en lugar del expediente clínico completo).",
        "probabilidad_residual": 1,
        "impacto_residual": 2,
        "historico": ["Alineado con directrices LFPDPPP y buenas prácticas ISO 27001"]
    },
    {
        "_id": "RIESGO-004",
        "modulo": "Control de Acceso Físico (Garita y Semáforo)",
        "descripcion": "Dependencia excesiva de la automatización (Automation Bias): guardias de seguridad dejan de supervisar visualmente y abren o niegan el paso ciegamente según el semáforo del sistema.",
        "categoria": "Factores Humanos y Sobreautomatización",
        "probabilidad": 5,
        "impacto": 4,
        "mitigacion": "Diseño Human-in-the-Loop obligatorio: el sistema sugiere y explica pero exige confirmación del guardia en casos de bandera 'requiere_revision_humana'; auditorías aleatorias.",
        "probabilidad_residual": 2,
        "impacto_residual": 2,
        "historico": ["Recomendación de seguridad patrimonial implementada en la GUI"]
    }
]


class GestorRiesgosEticos:
    """
    Gestiona la matriz de riesgos, calcula matrices de severidad
    y genera datos vectoriales para gráficas de calor y dispersión.
    """

    def __init__(self):
        pass

    def inicializar_riesgos_si_vacio(self):
        """Carga los riesgos iniciales en MongoDB si aún no existen."""
        actuales = db_servicio.listar_riesgos_eticos()
        if not actuales:
            for r in RIESGOS_ETICOS_INICIALES:
                db_servicio.registrar_riesgo_etico(r)

    def registrar_o_actualizar_riesgo(
        self,
        modulo: str,
        descripcion: str,
        categoria: str,
        probabilidad: int,
        impacto: int,
        mitigacion: str,
        probabilidad_residual: int,
        impacto_residual: int,
        riesgo_id: Optional[str] = None
    ) -> str:
        datos = {
            "_id": riesgo_id,
            "modulo": modulo,
            "descripcion": descripcion,
            "categoria": categoria,
            "probabilidad": int(probabilidad),
            "impacto": int(impacto),
            "mitigacion": mitigacion,
            "probabilidad_residual": int(probabilidad_residual),
            "impacto_residual": int(impacto_residual),
            "historico": [f"Actualizado el {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
        }
        return db_servicio.registrar_riesgo_etico(datos)

    def obtener_todos(self) -> List[Dict[str, Any]]:
        self.inicializar_riesgos_si_vacio()
        return db_servicio.listar_riesgos_eticos()

    def calcular_estadisticas_riesgo(self) -> Dict[str, Any]:
        """
        Calcula la reducción promedio de riesgo antes y después de la mitigación.
        """
        riesgos = self.obtener_todos()
        if not riesgos:
            return {"total": 0, "promedio_inherente": 0, "promedio_residual": 0, "reduccion_porcentual": 0}

        total_inherente = sum(r.get("riesgo_inherente_score", r["probabilidad"] * r["impacto"]) for r in riesgos)
        total_residual = sum(r.get("riesgo_residual_score", r.get("probabilidad_residual", 1) * r.get("impacto_residual", 1)) for r in riesgos)

        prom_inh = total_inherente / len(riesgos)
        prom_res = total_residual / len(riesgos)
        reduccion = ((prom_inh - prom_res) / prom_inh * 100) if prom_inh > 0 else 0

        # Conteo por nivel de severidad residual
        criticos = sum(1 for r in riesgos if r.get("riesgo_residual_score", 0) >= 15)
        altos = sum(1 for r in riesgos if 10 <= r.get("riesgo_residual_score", 0) < 15)
        moderados = sum(1 for r in riesgos if 5 <= r.get("riesgo_residual_score", 0) < 10)
        bajos = sum(1 for r in riesgos if r.get("riesgo_residual_score", 0) < 5)

        return {
            "total_riesgos": len(riesgos),
            "promedio_inherente": round(prom_inh, 2),
            "promedio_residual": round(prom_res, 2),
            "reduccion_porcentual": round(reduccion, 1),
            "distribucion_residual": {
                "criticos": criticos,
                "altos": altos,
                "moderados": moderados,
                "bajos": bajos
            }
        }


# Instancia singleton
gestor_riesgos = GestorRiesgosEticos()


if __name__ == "__main__":
    gestor_riesgos.inicializar_riesgos_si_vacio()
    print("=== ESTADÍSTICAS DE RIESGOS ÉTICOS ===")
    print(gestor_riesgos.calcular_estadisticas_riesgo())
