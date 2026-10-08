# ============================================================
# ESQUEMAS PYDANTIC PARA VALIDACIÓN ESTRICTA DE JSON
# ============================================================
# Valida la estructura requerida del LLM para incidentes:
# categoría, prioridad, entidades y resumen.
# ============================================================

from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class PrioridadEnum(str, Enum):
    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class CategoriaEnum(str, Enum):
    ACCESO = "Control de Acceso"
    SOBREPESO = "Sobrepeso y Báscula"
    HAZMAT = "Materiales Peligrosos"
    DOCUMENTACION = "Documentación y Certificación"
    MECANICO = "Falla Mecánica / Seguridad"
    SISTEMA = "Anomalía en Sistema / Sensor"
    OTRO = "General / Operativo"


class EntidadesExtraidas(BaseModel):
    """Entidades clave extraídas del cuerpo del correo."""
    placa: Optional[str] = Field(default=None, description="Placa o matrícula del camión (ej. TRK-882)")
    camion_id: Optional[str] = Field(default=None, description="Identificador único del vehículo (ej. CAM-102)")
    empresa: Optional[str] = Field(default=None, description="Empresa transportista responsable")
    conductor: Optional[str] = Field(default=None, description="Nombre del operador o chofer")
    peso_kg: Optional[float] = Field(default=None, description="Peso reportado o excedido en kilogramos")
    sustancia: Optional[str] = Field(default=None, description="Material peligroso o tipo de carga transportada")


class ExtraccionIncidenteLLM(BaseModel):
    """
    Esquema exacto exigido al LLM para la clasificación de incidentes.
    """
    categoria: str = Field(..., description="Categoría temática del incidente")
    prioridad: PrioridadEnum = Field(..., description="Nivel de severidad: BAJA, MEDIA, ALTA o CRITICA")
    entidades: EntidadesExtraidas = Field(default_factory=EntidadesExtraidas, description="Entidades identificadas")
    resumen: str = Field(..., min_length=10, max_length=500, description="Resumen conciso del correo")
    justificacion: Optional[str] = Field(default="", description="Explicación del porqué de la prioridad")

    @field_validator("prioridad", mode="before")
    @classmethod
    def normalizar_prioridad(cls, v):
        if isinstance(v, str):
            v_upper = v.strip().upper()
            if "CRITIC" in v_upper:
                return PrioridadEnum.CRITICA
            if "ALT" in v_upper:
                return PrioridadEnum.ALTA
            if "MED" in v_upper:
                return PrioridadEnum.MEDIA
            if "BAJ" in v_upper:
                return PrioridadEnum.BAJA
        return v


class ResultadoClasificacionHibrida(BaseModel):
    """Resultado final de la fusión entre Reglas y LLM."""
    correo_original: str
    resultado_llm: Optional[ExtraccionIncidenteLLM] = None
    resultado_reglas: Dict[str, Any]
    prioridad_final: PrioridadEnum
    categoria_final: str
    entidades_final: EntidadesExtraidas
    resumen_final: str
    discrepancia_detectada: bool
    requiere_revision_humana: bool
    fuente_decisiva: str
    latencia_ms: float
    modelo_utilizado: str
