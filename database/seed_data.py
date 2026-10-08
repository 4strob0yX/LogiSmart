# ============================================================
# SCRIPT DE POBLACIÓN DE DATOS DEMO (SEED DATA)
# ============================================================
# Módulo: seed_data.py
# Llena automáticamente las 5 colecciones de MongoDB con datos
# representativos para la entrega y exposición en vivo.
# ============================================================
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.database import db_servicio
from ai_services.matriz_riesgos import gestor_riesgos
from experiments.benchmark_30_correos import DATASET_30_CORREOS
from logic.motor_reglas import motor_logica


CAMIONES_DEMO = [
    {
        "camion_id": "CAM-101",
        "placa": "TRK-781",
        "empresa": "Transportes del Norte S.A.",
        "autorizacion": True,
        "certificacion_conductor": True,
        "conductor_nombre": "Jorge Mendoza López"
    },
    {
        "camion_id": "CAM-102",
        "placa": "TRK-882",
        "empresa": "Químicos y Solventes del Bajío",
        "autorizacion": True,
        "certificacion_conductor": False,  # Licencia vencida
        "conductor_nombre": "Carlos Méndez Reyes"
    },
    {
        "camion_id": "CAM-103",
        "placa": "NL-4512",
        "empresa": "Logística y Cargas Rápidas",
        "autorizacion": True,
        "certificacion_conductor": True,
        "conductor_nombre": "Roberto Garza Villarreal"
    },
    {
        "camion_id": "CAM-104",
        "placa": "XA-9921",
        "empresa": "Minerales y Agregados Pesados",
        "autorizacion": False,  # Sin permiso de entrada
        "certificacion_conductor": True,
        "conductor_nombre": "Fernando Salazar Soto"
    },
    {
        "camion_id": "CAM-105",
        "placa": "ED-883",
        "empresa": "Autotransportes Toluca Express",
        "autorizacion": True,
        "certificacion_conductor": True,
        "conductor_nombre": "Juan Pablo Morales"
    },
    {
        "camion_id": "CAM-106",
        "placa": "GT-1182",
        "empresa": "Distribuidora de Alimentos del Centro",
        "autorizacion": True,
        "certificacion_conductor": True,
        "conductor_nombre": "Miguel Ángel Cruz"
    },
    {
        "camion_id": "CAM-107",
        "placa": "JAL-309",
        "empresa": "Cargas Industriales de Occidente",
        "autorizacion": False,
        "certificacion_conductor": False,
        "conductor_nombre": "Esteban Domínguez"
    },
    {
        "camion_id": "CAM-108",
        "placa": "PUE-774",
        "empresa": "Petroquímica de Puebla",
        "autorizacion": True,
        "certificacion_conductor": True,
        "conductor_nombre": "Arturo Benítez Vega"
    }
]


def poblar_datos_completos():
    print("\n" + "=" * 60)
    print("      INICIALIZANDO POBLACIÓN DE DATOS DEMO (LOGISMART)")
    print("=" * 60)

    # 1. Camiones
    print("\n[1/5] Registrando catálogo de camiones en MongoDB...")
    for cam in CAMIONES_DEMO:
        db_servicio.registrar_camion(cam)
    print(f" -> {len(CAMIONES_DEMO)} camiones registrados.")

    # 2. Bitácora de Accesos
    print("\n[2/5] Generando bitácora de accesos históricos...")
    casos_acceso = [
        ("CAM-101", "TRK-781", True, False, False, True, False, True),   # A=True -> Verde
        ("CAM-102", "TRK-882", True, True, False, True, False, True),    # Q=True -> Amarillo (Inspección)
        ("CAM-103", "NL-4512", True, False, True, True, False, True),    # R=True -> Amarillo (Peligroso)
        ("CAM-104", "XA-9921", False, True, False, True, False, True),   # P=False -> Rojo
        ("CAM-105", "ED-883", True, False, False, False, False, True),   # S=False -> Rojo
        ("CAM-106", "GT-1182", True, False, True, True, True, True),     # R=True y T=True -> Rojo (Nocturno)
        ("CAM-107", "JAL-309", False, False, False, False, False, False),# Todo False -> Rojo
        ("CAM-108", "PUE-774", True, False, False, True, False, True)    # Verde
    ]

    for cam_id, placa, P, Q, R, S, T, M in casos_acceso:
        eval_res = motor_logica.evaluar_acceso(P, Q, R, S, T, M)
        db_servicio.registrar_acceso({
            "camion_id": cam_id,
            "placa": placa,
            "operador": "Oficial Martínez (Garita 1)",
            "P": P, "Q": Q, "R": R, "S": S, "T": T, "M": M,
            "resultado_A": eval_res["evaluacion_reglas"]["A_acceso_estandar"],
            "resultado_E": eval_res["evaluacion_reglas"]["E_inspeccion_especial"],
            "semaforo": eval_res["semaforo"],
            "decision": eval_res["decision"],
            "explicacion_paso_a_paso": eval_res["explicacion_paso_a_paso"]
        })
    print(f" -> {len(casos_acceso)} registros de acceso generados.")

    # 3. Incidentes con los 30 correos
    print("\n[3/5] Poblando colección de incidentes con dataset clasificado...")
    estados_muestra = ["nuevo", "en_atencion", "cerrado", "nuevo", "en_atencion"]
    for idx, item in enumerate(DATASET_30_CORREOS):
        estado_asignado = estados_muestra[idx % len(estados_muestra)]
        db_servicio.registrar_incidente({
            "correo_original": item["correo"],
            "categoria": item["categoria_esperada"],
            "prioridad": item["etiqueta_real"].value,
            "datos_extraidos": {
                "fuente": "Dataset Etiquetado Manual",
                "muestra_id": item["id"]
            },
            "resumen": item["correo"][:140],
            "estado": estado_asignado,
            "requiere_revision_humana": item["etiqueta_real"] in ["ALTA", "CRITICA"]
        })
    print(f" -> {len(DATASET_30_CORREOS)} incidentes cargados en la base de datos.")

    # 4. Riesgos Éticos
    print("\n[4/5] Registrando matriz de riesgos éticos iniciales...")
    gestor_riesgos.inicializar_riesgos_si_vacio()
    print(" -> 4 riesgos éticos fundamentales registrados con residuales.")

    # 5. Evaluaciones LLM de demostración
    print("\n[5/5] Registrando bitácora de evaluaciones de LLM...")
    db_servicio.registrar_evaluacion_llm({
        "prompt": "Análisis inicial de garita: camión con sospecha de fuga de químicos.",
        "respuesta": {"prioridad": "CRITICA", "categoria": "Materiales Peligrosos"},
        "modelo": "llama3.2",
        "latencia_ms": 420.5,
        "coincidio_con_reglas": True
    })
    print(" -> Evaluaciones LLM inicializadas.")

    print("\n" + "=" * 60)
    print("  ✓ POBLACIÓN DE DATOS DEMOSTRATIVOS FINALIZADA CON ÉXITO")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    poblar_datos_completos()
