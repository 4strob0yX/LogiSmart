# ============================================================
# MOTOR DE REGLAS LÓGICAS PROPOSICIONALES EXTENDIDO
# ============================================================
# Módulo: motor_reglas.py
# Implementa el razonamiento simbólico formal para el acceso
# vehicular, explicador paso a paso y detector de contradicciones.
# ============================================================

from itertools import product
from typing import Dict, Any, List, Tuple


class MotorReglasLogicas:
    """
    Motor inferencial proposicional que evalúa condiciones de acceso
    basado en lógica booleana clásica con trazabilidad causal.
    """

    def __init__(self):
        # Nombres descriptivos de las proposiciones
        self.definiciones = {
            "P": "Autorización previa vigente en sistema",
            "Q": "Peso bruto excedido respecto al límite de báscula",
            "R": "Transporte de materiales peligrosos (HAZMAT)",
            "S": "Licencia y certificación vehicular vigente del conductor",
            # Nuevas proposiciones solicitadas:
            "T": "Tránsito en horario nocturno restringido (22:00 a 05:00 hrs)",
            "M": "Examen psicofísico / aptitud médica del conductor vigente"
        }

    def evaluar_acceso(
        self,
        P: bool,
        Q: bool,
        R: bool,
        S: bool,
        T: bool = False,
        M: bool = True
    ) -> Dict[str, Any]:
        """
        Evalúa las premisas y deduce el estado de acceso con explicación causal.
        
        Reglas Base:
          A = P ∧ S ∧ ¬Q        (Acceso Estándar)
          E = P ∧ (R ∨ Q)       (Inspección Especial)

        Reglas Nuevas Justificadas:
          H = R ∧ T            (Bloqueo HAZMAT Nocturno: protección civil prohíbe químicos de noche)
          C = S ∧ M            (Habilitación Integral del Conductor: licencia + aptitud médica)
        """

        # ----------------------------------------------------
        # 1. EVALUACIÓN DE REGLAS FORMALES
        # ----------------------------------------------------
        # Regla 1 (Base): Acceso Estándar
        acceso_estandar = bool(P and S and (not Q))

        # Regla 2 (Base): Inspección Especial
        inspeccion_especial = bool(P and (R or Q))

        # Regla 3 (Nueva Justificada): Restricción Nocturna HAZMAT
        # Justificación: Las normativas de seguridad vial restringen el tránsito
        # de sustancias inflamables/tóxicas en zonas urbanas durante la noche.
        bloqueo_nocturno_hazmat = bool(R and T)

        # Regla 4 (Nueva Justificada): Habilitación Integral Conductor
        # Justificación: Exige que el chofer no solo tenga licencia vigente (S),
        # sino dictamen médico activo (M) para prevenir accidentes por fatiga.
        conductor_apto_integral = bool(S and M)

        # ----------------------------------------------------
        # 2. RESOLUCIÓN DE DECISIÓN OPERATIVA Y SEMÁFORO
        # ----------------------------------------------------
        explicacion_pasos: List[str] = []
        contradicion_detectada = False
        advertencias: List[str] = []

        # Paso 1: Verificación de Autorización Previa (P)
        if not P:
            explicacion_pasos.append("P = False: El camión NO cuenta con autorización previa en sistema.")
            decision = "DENEGADO"
            semaforo = "ROJO"
            explicacion_pasos.append("Deducción: Al ser P = False, las conjunciones A y E se evalúan como False.")
        else:
            explicacion_pasos.append("P = True: Autorización previa validada.")

            # Paso 2: Análisis de Restricción Nocturna HAZMAT (H = R ∧ T)
            if bloqueo_nocturno_hazmat:
                decision = "DENEGADO_HORARIO_PELIGROSO"
                semaforo = "ROJO"
                explicacion_pasos.append(
                    "H = R ∧ T = True: Material peligroso (R=True) detectado en horario nocturno (T=True). "
                    "Infracción directa a la directriz de seguridad de protección civil."
                )
                advertencias.append("Alerta: Tránsito de materiales peligrosos prohibido entre 22:00 y 05:00 hrs.")

            # Paso 3: Análisis de Inspección Especial (E = P ∧ (R ∨ Q))
            elif inspeccion_especial:
                decision = "INSPECCION_ESPECIAL"
                semaforo = "AMARILLO"
                razones_e = []
                if Q:
                    razones_e.append("Sobrepeso en báscula (Q=True)")
                if R:
                    razones_e.append("Materiales peligrosos (R=True)")
                explicacion_pasos.append(
                    f"E = P ∧ (R ∨ Q) = True: Vehículo derivado a bahía de inspección especial debido a: {', '.join(razones_e)}."
                )

                if acceso_estandar:
                    # En teoría proposicional, si Q=False y R=True, tanto A como E pueden dar True simultáneamente.
                    # Esto representa una ambigüedad operativa: ¿pasa o se inspecciona?
                    contradicion_detectada = True
                    advertencias.append(
                        "Alerta de precedencia: Tanto A (Acceso) como E (Inspección) resultaron True. "
                        "El protocolo de seguridad prioriza E (Inspección Especial) ante materiales peligrosos."
                    )
                    explicacion_pasos.append("Resolución de seguridad: Prevalece Inspección Especial sobre Acceso Estándar.")

            # Paso 4: Análisis de Acceso Estándar (A = P ∧ S ∧ ¬Q)
            elif acceso_estandar and conductor_apto_integral:
                decision = "ACCESO_AUTORIZADO"
                semaforo = "VERDE"
                explicacion_pasos.append(
                    "A = P ∧ S ∧ ¬Q = True: Autorizado (P), conductor certificado (S) y dentro del límite de peso (¬Q)."
                )
                explicacion_pasos.append("C = S ∧ M = True: Conductor con acreditación médica y licencia al 100%.")

            # Paso 5: Fallo de certificación o aptitud médica
            else:
                decision = "DENEGADO"
                semaforo = "ROJO"
                if not S:
                    explicacion_pasos.append("S = False: Conductor sin licencia o certificación vencida.")
                if not M:
                    explicacion_pasos.append("M = False: Conductor sin dictamen psicofísico médico vigente.")
                if Q:
                    explicacion_pasos.append("Q = True: Sobrepeso detectado sin protocolo de inspección especial.")
                explicacion_pasos.append("Deducción: No se cumplen las premisas mínimas de acceso seguro.")

        # ----------------------------------------------------
        # 3. EMPAQUETADO DEL RESULTADO
        # ----------------------------------------------------
        return {
            "premisas": {
                "P": P, "Q": Q, "R": R, "S": S, "T": T, "M": M
            },
            "evaluacion_reglas": {
                "A_acceso_estandar": acceso_estandar,
                "E_inspeccion_especial": inspeccion_especial,
                "H_bloqueo_hazmat_nocturno": bloqueo_nocturno_hazmat,
                "C_conductor_apto_integral": conductor_apto_integral
            },
            "decision": decision,
            "semaforo": semaforo,
            "explicacion_paso_a_paso": explicacion_pasos,
            "contradicion_detectada": contradicion_detectada,
            "advertencias": advertencias
        }

    def generar_tabla_verdad_base(self) -> List[Dict[str, Any]]:
        """
        Genera las 16 combinaciones canónicas de las 4 premisas base (P, Q, R, S).
        """
        filas = []
        for P, Q, R, S in product([False, True], repeat=4):
            A = P and S and (not Q)
            E = P and (R or Q)
            filas.append({
                "P": int(P),
                "Q": int(Q),
                "R": int(R),
                "S": int(S),
                "A": int(A),
                "E": int(E),
                "estado": "VERDE" if (A and not E) else ("AMARILLO" if E else "ROJO")
            })
        return filas

    def generar_tabla_verdad_extendida(self) -> List[Dict[str, Any]]:
        """
        Genera la tabla de verdad extendida con las 6 variables (64 filas).
        """
        filas = []
        for P, Q, R, S, T, M in product([False, True], repeat=6):
            res = self.evaluar_acceso(P, Q, R, S, T, M)
            filas.append({
                "P": int(P), "Q": int(Q), "R": int(R),
                "S": int(S), "T": int(T), "M": int(M),
                "A": int(res["evaluacion_reglas"]["A_acceso_estandar"]),
                "E": int(res["evaluacion_reglas"]["E_inspeccion_especial"]),
                "H": int(res["evaluacion_reglas"]["H_bloqueo_hazmat_nocturno"]),
                "decision": res["decision"],
                "semaforo": res["semaforo"]
            })
        return filas

    def detectar_redundancias_y_contradicciones(self) -> Dict[str, Any]:
        """
        Reto Opcional: Análisis estático de teoremas y colisiones lógicas.
        """
        tabla_base = self.generar_tabla_verdad_base()
        colisiones_A_y_E = [fila for fila in tabla_base if fila["A"] == 1 and fila["E"] == 1]
        
        # Una colisión ocurre cuando A=1 y E=1:
        # A = P ∧ S ∧ ¬Q  => Q=0, P=1, S=1
        # E = P ∧ (R ∨ Q) => P=1, R=1 (ya que Q=0)
        # Por tanto, si P=1, Q=0, R=1, S=1, ambas reglas se activan a la vez.
        
        return {
            "total_combinaciones": len(tabla_base),
            "colisiones_detectadas": len(colisiones_A_y_E),
            "condicion_colision": "P ∧ ¬Q ∧ R ∧ S (Autorizado, sin sobrepeso, pero con materiales peligrosos)",
            "solucion_operativa": "Principio de Prevalencia de Seguridad: En caso de A=1 y E=1, la garita deriva a E (Inspección Especial)."
        }


# Instancia singleton para uso rápido
motor_logica = MotorReglasLogicas()


if __name__ == "__main__":
    print("=== PRUEBA DEL MOTOR DE REGLAS AMPLIADO ===")
    res = motor_logica.evaluar_acceso(P=True, Q=False, R=True, S=True, T=True, M=True)
    print("Decisión:", res["decision"])
    print("Semáforo:", res["semaforo"])
    print("\nExplicación Paso a Paso:")
    for paso in res["explicacion_paso_a_paso"]:
        print(" ->", paso)
    print("\nAnálisis del Reto de Contradicciones:")
    print(motor_logica.detectar_redundancias_y_contradicciones())
