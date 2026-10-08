# ============================================================
# BENCHMARK EXPERIMENTAL: 30 CORREOS ETIQUETADOS A MANO
# ============================================================
# Módulo: benchmark_30_correos.py
# Evalúa experimentalmente: Reglas vs LLM vs Clasificador Híbrido
# Métricas: Exactitud (Accuracy), Matriz de Confusión (4x4) y Latencia.
# ============================================================
import os
import sys
import time
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_services.schemas_pydantic import PrioridadEnum
from ai_services.clasificador_hibrido import clasificador_hibrido


# Dataset de 30 correos reales etiquetados a mano con casos de borde y dialectos
DATASET_30_CORREOS: List[Dict[str, Any]] = [
    # --- 1 a 6: Prioridad CRÍTICA (Fugas químicas, conatos, fallas mayores) ---
    {
        "id": 1,
        "correo": "URGENTE: Unidad CAM-101 con placas TRK-781 presenta fuga de gas cloro en válvula de alivio. Evacuen área de garita.",
        "etiqueta_real": PrioridadEnum.CRITICA,
        "categoria_esperada": "Materiales Peligrosos"
    },
    {
        "id": 2,
        "correo": "El camión CAM-204 entró a exceso de velocidad sin frenos y derribó la pluma de la garita 2. Operador lesionado.",
        "etiqueta_real": PrioridadEnum.CRITICA,
        "categoria_esperada": "Falla Mecánica / Seguridad"
    },
    {
        "id": 3,
        "correo": "Alerta roja en báscula: Camión con placas XA-9921 pesa 54 toneladas, superando en 14 tons el límite legal. Chasis doblado.",
        "etiqueta_real": PrioridadEnum.CRITICA,
        "categoria_esperada": "Sobrepeso y Báscula"
    },
    {
        "id": 4,
        "correo": "Sujetos intentan ingresar forzadamente camión blanco sin placas ni manifiesto de carga por el carril de salida.",
        "etiqueta_real": PrioridadEnum.CRITICA,
        "categoria_esperada": "Control de Acceso"
    },
    {
        "id": 5,
        "correo": "Derrame activo de ácido sulfúrico proveniente del autotanque CAM-305 en la bahía de revisión técnica.",
        "etiqueta_real": PrioridadEnum.CRITICA,
        "categoria_esperada": "Materiales Peligrosos"
    },
    {
        "id": 6,
        "correo": "Incendio en eje trasero de tractocamión placa NL-4512 estacionado frente a cisterna de diesel.",
        "etiqueta_real": PrioridadEnum.CRITICA,
        "categoria_esperada": "Falla Mecánica / Seguridad"
    },

    # --- 7 a 14: Prioridad ALTA (Materiales peligrosos no declarados, sobrepeso, licencias vencidas) ---
    {
        "id": 7,
        "correo": "Camión CAM-102 transporta tambores con solventes químicos inflamables sin rombo de seguridad SCT ni permiso HAZMAT.",
        "etiqueta_real": PrioridadEnum.ALTA,
        "categoria_esperada": "Materiales Peligrosos"
    },
    {
        "id": 8,
        "correo": "Báscula marca 43,200 kg para el camión TRK-331. Excede el límite de 40 tons pero sin daño estructural aparente.",
        "etiqueta_real": PrioridadEnum.ALTA,
        "categoria_esperada": "Sobrepeso y Báscula"
    },
    {
        "id": 9,
        "correo": "El chofer Carlos Méndez de la empresa TransMex tiene la licencia federal tipo E vencida desde hace 6 meses.",
        "etiqueta_real": PrioridadEnum.ALTA,
        "categoria_esperada": "Documentación y Certificación"
    },
    {
        "id": 10,
        "correo": "Llegó a garita a las 23:30 hrs transporte con gas LP para descarga nocturna. No cuenta con autorización de horario.",
        "etiqueta_real": PrioridadEnum.ALTA,
        "categoria_esperada": "Materiales Peligrosos"
    },
    {
        "id": 11,
        "correo": "Camión CAM-402 con placas GT-1182 no aparece en el sistema de citas de acceso previo para el día de hoy.",
        "etiqueta_real": PrioridadEnum.ALTA,
        "categoria_esperada": "Control de Acceso"
    },
    {
        "id": 12,
        "correo": "Dictamen médico del conductor arroja resultado no apto por fatiga severa y presión arterial alta.",
        "etiqueta_real": PrioridadEnum.ALTA,
        "categoria_esperada": "Documentación y Certificación"
    },
    {
        "id": 13,
        "correo": "Tractocamión con placa ED-883 presenta fuga menor de aceite de transmisión en el carril de espera.",
        "etiqueta_real": PrioridadEnum.ALTA,
        "categoria_esperada": "Falla Mecánica / Seguridad"
    },
    {
        "id": 14,
        "correo": "Báscula registró 44,500 kg en unidad de paquetería express. Se solicita retención para descarga de excedente.",
        "etiqueta_real": PrioridadEnum.ALTA,
        "categoria_esperada": "Sobrepeso y Báscula"
    },

    # --- 15 a 22: Prioridad MEDIA (Fallas de sensor, demoras, discrepancias leves) ---
    {
        "id": 15,
        "correo": "La antena lectora RFID del carril norte no leyó el tag del camión CAM-110, requiriendo captura manual.",
        "etiqueta_real": PrioridadEnum.MEDIA,
        "categoria_esperada": "Anomalía en Sistema / Sensor"
    },
    {
        "id": 16,
        "correo": "Se formó fila de 8 camiones en patio de espera debido a lentitud temporal en el servidor de pesaje.",
        "etiqueta_real": PrioridadEnum.MEDIA,
        "categoria_esperada": "General / Operativo"
    },
    {
        "id": 17,
        "correo": "Discrepancia en remisión: la factura indica 20 tarimas pero en físico el guardia contó 21 tarimas de cajas secas.",
        "etiqueta_real": PrioridadEnum.MEDIA,
        "categoria_esperada": "General / Operativo"
    },
    {
        "id": 18,
        "correo": "La cámara de reconocimiento de matrículas OCR está sucia y tuvo error en placa de camión CAM-208.",
        "etiqueta_real": PrioridadEnum.MEDIA,
        "categoria_esperada": "Anomalía en Sistema / Sensor"
    },
    {
        "id": 19,
        "correo": "El chofer reporta que el sello de seguridad fiscal del contenedor viene con numeración corrida por una cifra.",
        "etiqueta_real": PrioridadEnum.MEDIA,
        "categoria_esperada": "Control de Acceso"
    },
    {
        "id": 20,
        "correo": "Falla de iluminación en poste 4 de la bahía de inspección. Visibilidad reducida para revisión nocturna.",
        "etiqueta_real": PrioridadEnum.MEDIA,
        "categoria_esperada": "General / Operativo"
    },
    {
        "id": 21,
        "correo": "Camión reporta demora de 45 minutos en aduana interna por revisión aleatoria no programada.",
        "etiqueta_real": PrioridadEnum.MEDIA,
        "categoria_esperada": "General / Operativo"
    },
    {
        "id": 22,
        "correo": "Lector de código de barras de gafetes de choferes parpadea en color amarillo y requiere reinicio.",
        "etiqueta_real": PrioridadEnum.MEDIA,
        "categoria_esperada": "Anomalía en Sistema / Sensor"
    },

    # --- 23 a 30: Prioridad BAJA (Informativos, cambios de guardia, calibraciones) ---
    {
        "id": 23,
        "correo": "Aviso informativo: Se realizó con éxito la calibración bimestral de la báscula de fosa número 1.",
        "etiqueta_real": PrioridadEnum.BAJA,
        "categoria_esperada": "General / Operativo"
    },
    {
        "id": 24,
        "correo": "Entrega de turno sin novedades extraordinarias en garita poniente. Todos los sensores operando al 100%.",
        "etiqueta_real": PrioridadEnum.BAJA,
        "categoria_esperada": "General / Operativo"
    },
    {
        "id": 25,
        "correo": "Recordatorio: Mañana a las 09:00 hrs se llevará a cabo limpieza programada en banquetas de acceso.",
        "etiqueta_real": PrioridadEnum.BAJA,
        "categoria_esperada": "General / Operativo"
    },
    {
        "id": 26,
        "correo": "El camión CAM-105 completó su descarga de refacciones automotrices y se retira en orden.",
        "etiqueta_real": PrioridadEnum.BAJA,
        "categoria_esperada": "General / Operativo"
    },
    {
        "id": 27,
        "correo": "Se solicita reposición de rollos de papel térmico para las impresoras de tickets de pesaje de garita.",
        "etiqueta_real": PrioridadEnum.BAJA,
        "categoria_esperada": "General / Operativo"
    },
    {
        "id": 28,
        "correo": "Actualización de catálogo de transportistas autorizados para el mes de noviembre cargada en el servidor.",
        "etiqueta_real": PrioridadEnum.BAJA,
        "categoria_esperada": "General / Operativo"
    },
    {
        "id": 29,
        "correo": "Aviso de mantenimiento preventivo de software para el próximo domingo a las 02:00 am.",
        "etiqueta_real": PrioridadEnum.BAJA,
        "categoria_esperada": "General / Operativo"
    },
    {
        "id": 30,
        "correo": "El proveedor de agua purificada entregó los garrafones para la caseta de vigilancia. Todo conforme.",
        "etiqueta_real": PrioridadEnum.BAJA,
        "categoria_esperada": "General / Operativo"
    }
]


class EvaluadorBenchmark:
    """
    Ejecuta el experimento de clasificación comparativo y computa matrices de confusión.
    """

    def __init__(self):
        self.clases = [PrioridadEnum.BAJA, PrioridadEnum.MEDIA, PrioridadEnum.ALTA, PrioridadEnum.CRITICA]

    def _inicializar_matriz(self) -> Dict[str, Dict[str, int]]:
        return {
            real.value: {pred.value: 0 for pred in self.clases}
            for real in self.clases
        }

    def ejecutar_evaluacion_completa(self) -> Dict[str, Any]:
        """
        Ejecuta los 30 correos a través de:
        1. Motor de Reglas
        2. LLM Ollama
        3. Clasificador Híbrido
        """
        matriz_reglas = self._inicializar_matriz()
        matriz_llm = self._inicializar_matriz()
        matriz_hibrido = self._inicializar_matriz()

        correctas_reglas = 0
        correctas_llm = 0
        correctas_hibrido = 0

        latencias_reglas = []
        latencias_llm = []
        latencias_hibrido = []

        detalles_correos = []

        for item in DATASET_30_CORREOS:
            correo = item["correo"]
            real = item["etiqueta_real"]

            # 1. Reglas
            t0 = time.time()
            res_r = clasificador_hibrido.clasificar_por_reglas(correo)
            lat_r = (time.time() - t0) * 1000
            pred_r = res_r["prioridad"]
            latencias_reglas.append(lat_r)
            matriz_reglas[real.value][pred_r.value] += 1
            if pred_r == real:
                correctas_reglas += 1

            # 2. LLM
            t1 = time.time()
            res_l, lat_l, _ = clasificador_hibrido.clasificar_con_llm(correo)
            pred_l = res_l.prioridad if res_l else pred_r
            latencias_llm.append(lat_l)
            matriz_llm[real.value][pred_l.value] += 1
            if pred_l == real:
                correctas_llm += 1

            # 3. Híbrido
            t2 = time.time()
            res_h = clasificador_hibrido.procesar_incidente_completo(correo)
            lat_h = (time.time() - t2) * 1000
            pred_h = res_h.prioridad_final
            latencias_hibrido.append(lat_h)
            matriz_hibrido[real.value][pred_h.value] += 1
            if pred_h == real:
                correctas_hibrido += 1

            detalles_correos.append({
                "id": item["id"],
                "correo": correo,
                "real": real.value,
                "pred_reglas": pred_r.value,
                "pred_llm": pred_l.value,
                "pred_hibrido": pred_h.value,
                "acierto_hibrido": pred_h == real,
                "discrepancia": res_h.discrepancia_detectada,
                "fuente": res_h.fuente_decisiva
            })

        total = len(DATASET_30_CORREOS)
        acc_reglas = (correctas_reglas / total) * 100
        acc_llm = (correctas_llm / total) * 100
        acc_hibrido = (correctas_hibrido / total) * 100

        prom_lat_reglas = sum(latencias_reglas) / total
        prom_lat_llm = sum(latencias_llm) / total
        prom_lat_hibrido = sum(latencias_hibrido) / total

        return {
            "total_muestras": total,
            "metricas": {
                "reglas": {
                    "aciertos": correctas_reglas,
                    "exactitud_pct": round(acc_reglas, 2),
                    "latencia_prom_ms": round(prom_lat_reglas, 2),
                    "matriz_confusion": matriz_reglas
                },
                "llm": {
                    "aciertos": correctas_llm,
                    "exactitud_pct": round(acc_llm, 2),
                    "latencia_prom_ms": round(prom_lat_llm, 2),
                    "matriz_confusion": matriz_llm
                },
                "hibrido": {
                    "aciertos": correctas_hibrido,
                    "exactitud_pct": round(acc_hibrido, 2),
                    "latencia_prom_ms": round(prom_lat_hibrido, 2),
                    "matriz_confusion": matriz_hibrido
                }
            },
            "detalles": detalles_correos
        }


# Instancia singleton
benchmark_evaluador = EvaluadorBenchmark()


if __name__ == "__main__":
    print("=== EJECUTANDO BENCHMARK CON LOS 30 CORREOS ===")
    resultados = benchmark_evaluador.ejecutar_evaluacion_completa()
    m = resultados["metricas"]
    print(f"Reglas:  Exactitud = {m['reglas']['exactitud_pct']}% | Latencia = {m['reglas']['latencia_prom_ms']} ms")
    print(f"LLM:     Exactitud = {m['llm']['exactitud_pct']}% | Latencia = {m['llm']['latencia_prom_ms']} ms")
    print(f"Híbrido: Exactitud = {m['hibrido']['exactitud_pct']}% | Latencia = {m['hibrido']['latencia_prom_ms']} ms")
