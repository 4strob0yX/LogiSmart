# ============================================================
# MODELO PEAS FORMAL - AGENTE INTELIGENTE LOGISMART
# ============================================================
# PEAS: Performance, Environment, Actuators, Sensors
# Define el comportamiento formal del agente racional para el
# centro de control de acceso vehicular de carga pesada.
# ============================================================

class AgentePEASFormal:
    """
    Especificación formal del agente inteligente basada en el modelo
    de Russell & Norvig (Inteligencia Artificial: Un Enfoque Moderno).
    """

    def __init__(self):
        # ----------------------------------------------------
        # P - PERFORMANCE (Medida de Rendimiento)
        # Criterios objetivos y cuantificables del éxito del agente.
        # ----------------------------------------------------
        self.performance = {
            "seguridad_fisica": "0% accesos indebidos de camiones con sobrepeso crítico o sin permiso.",
            "tiempo_respuesta": "Latencia de decisión de garita inferior a 500 milisegundos.",
            "exactitud_clasificacion": "Mayor o igual a 90% en concordancia de severidad de incidentes.",
            "trazabilidad": "100% de decisiones auditadas con explicación causal paso a paso en MongoDB.",
            "falsos_positivos": "Minimizar retenciones innecesarias de transportes autorizados (< 2%).",
            "mitigacion_etica": "Reducción documentada de riesgo residual en al menos 40%."
        }

        # ----------------------------------------------------
        # E - ENVIRONMENT (Entorno de Operación)
        # El mundo físico y digital con el que interactúa el agente.
        # ----------------------------------------------------
        self.environment = {
            "zona_fisica": "Garita de acceso principal, patio de maniobras y bahía de inspección especial.",
            "flujo_vehicular": "Camiones de carga pesada (T3-S2, T3-S3) de empresas logísticas asociadas.",
            "operadores": "Guardias de seguridad patrimonial, choferes y despachadores.",
            "red_datos": "Clúster MongoDB (Atlas/Local), servidor Ollama y enlace de red local.",
            "condiciones_ambientales": "Operación continua 24/7 (turnos diurno y nocturno con baja visibilidad)."
        }

        # ----------------------------------------------------
        # A - ACTUATORS (Actuadores)
        # Mecanismos con los que el agente actúa sobre el entorno.
        # ----------------------------------------------------
        self.actuators = {
            "barrera_vehicular": "Pluma electro-hidráulica (Abierta: Permitido / Bloqueada: Denegado).",
            "semaforo_visual": "Semáforo tricolor (Verde: Estándar, Amarillo: Inspección Especial, Rojo: Denegado).",
            "alarma_patrimonial": "Sirena estroboscópica para conatos de intrusión o sobrepeso extremo.",
            "registro_digital": "Escritura atómica en colección 'accesos' de MongoDB con hash de auditoría.",
            "notificador_soporte": "Despachador de correos de incidente hacia soporte@logismart.com.",
            "interfaz_gui": "Retroalimentación visual al operador en tiempo real en la pantalla de control."
        }

        # ----------------------------------------------------
        # S - SENSORS (Sensores)
        # Dispositivos que capturan el estado del entorno (percepciones).
        # ----------------------------------------------------
        self.sensors = {
            "lector_rfid": "Antena lectora de tag de autorización previa vehicular (Premisa P).",
            "bascula_dinamica": "Celdas de carga piezoeléctricas en fosa de pesaje (Premisa Q).",
            "escaner_hazmat": "Detector de manifiestos y etiquetas de materiales peligrosos ONU (Premisa R).",
            "lector_qr_licencia": "Escáner óptico de certificación y vigencia de licencia SCT (Premisa S).",
            "reloj_ciberfisico": "Timestamp sincronizado NTP para control de turno nocturno (Premisa T).",
            "lector_aptitud_medica": "Validador biométrico de dictamen médico del conductor (Premisa M).",
            "bandeja_correos": "Lector IMAP/Web de reportes de anomalías de supervisores y choferes."
        }

    def obtener_resumen_dict(self):
        """Retorna el modelo PEAS como diccionario para la GUI o API."""
        return {
            "Performance": self.performance,
            "Environment": self.environment,
            "Actuators": self.actuators,
            "Sensors": self.sensors
        }

    def imprimir_resumen(self):
        """Muestra en terminal el modelo formal formateado."""
        print("\n" + "=" * 65)
        print("          ESPECIFICACIÓN FORMAL DEL AGENTE PEAS (LOGISMART)")
        print("=" * 65)
        for seccion, datos in self.obtener_resumen_dict().items():
            print(f"\n[{seccion.upper()}]")
            for clave, desc in datos.items():
                print(f"  • {clave.replace('_', ' ').title()}: {desc}")
        print("=" * 65 + "\n")


if __name__ == "__main__":
    agente = AgentePEASFormal()
    agente.imprimir_resumen()
