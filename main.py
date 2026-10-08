# ============================================================
# LOGISMART PYTHON SUITE - PUNTO DE ENTRADA PRINCIPAL
# ============================================================
# Módulo: main.py
# Ejecuta la demostración de consola completa y ofrece
# la opción de iniciar la Interfaz Gráfica interactiva.
# ============================================================

import sys
import os

from logic.peas_model import AgentePEASFormal
from logic.motor_reglas import motor_logica
from ai_services.clasificador_hibrido import clasificador_hibrido
from database.database import db_servicio
from ai_services.matriz_riesgos import gestor_riesgos
from database.seed_data import poblar_datos_completos



def ejecutar_demostracion_suite():
    print("\n" + "=" * 65)
    print("        LOGISMART PYTHON SUITE - SISTEMA INTEGRADO DE IA")
    print("=" * 65)

    # 1. PEAS
    print("\n>>> [1/5] MODELO PEAS FORMAL DEL AGENTE")
    agente = AgentePEASFormal()
    agente.imprimir_resumen()

    # 2. MOTOR DE REGLAS LÓGICAS PROPOSICIONALES
    print("\n>>> [2/5] MOTOR DE REGLAS Y EXPLICACIÓN CAUSAL")
    resultado = motor_logica.evaluar_acceso(
        P=True, Q=False, R=True, S=True, T=False, M=True
    )
    print(f"Decisión: {resultado['decision']} | Semáforo: {resultado['semaforo']}")
    print("Explicación paso a paso:")
    for paso in resultado["explicacion_paso_a_paso"]:
        print(f"  • {paso}")

    # Reto de contradicciones
    analisis = motor_logica.detectar_redundancias_y_contradicciones()
    print(f"Análisis de teoremas y colisiones: {analisis['colisiones_detectadas']} colisiones resueltas por principio de seguridad.")

    # 3. BASE DE DATOS MONGODB Y SEED DATA
    print("\n>>> [3/5] PERSISTENCIA EN MONGODB")
    estado = db_servicio.obtener_estado_conexion()
    print(f"Estado de conexión: {estado['modo']} (Base de datos: {estado['db_name']})")
    poblar_datos_completos()

    # 4. CLASIFICADOR HÍBRIDO CON VALIDACIÓN PYDANTIC
    print("\n>>> [4/5] CLASIFICADOR HÍBRIDO (REGLAS + LLM)")
    correo_prueba = (
        "URGENTE: Unidad CAM-102 con placas TRK-882 llegó con peso de 49,500 kg "
        "y sospecha de derrame de solvente industrial inflamable. Chofer con licencia vencida."
    )
    res_clasif = clasificador_hibrido.procesar_incidente_completo(correo_prueba)
    print(f"Categoría Final: {res_clasif.categoria_final}")
    print(f"Prioridad Final: {res_clasif.prioridad_final.value}")
    print(f"Discrepancia detectada: {res_clasif.discrepancia_detectada}")
    print(f"Requiere Revisión Humana: {res_clasif.requiere_revision_humana}")
    print(f"Fuente Decisiva: {res_clasif.fuente_decisiva}")
    print(f"Latencia: {res_clasif.latencia_ms} ms")

    # 5. MATRIZ DE RIESGOS ÉTICOS
    print("\n>>> [5/5] MATRIZ DE RIESGOS ÉTICOS DE NUESTRA IMPLEMENTACIÓN")
    stats = gestor_riesgos.calcular_estadisticas_riesgo()
    print(f"Total Riesgos: {stats['total_riesgos']}")
    print(f"Score Promedio Inherente: {stats['promedio_inherente']} / 25")
    print(f"Score Promedio Residual: {stats['promedio_residual']} / 25")
    print(f"Reducción Porcentual de Riesgo: {stats['reduccion_porcentual']}%")

    print("\n" + "=" * 65)
    print("  ✓ DEMOSTRACIÓN COMPLETADA CON ÉXITO")
    print("=" * 65)
    print("\nPara iniciar la Interfaz Gráfica interactiva ejecuta:")
    print("  python3 app_gui.py\n")


if __name__ == "__main__":
    ejecutar_demostracion_suite()