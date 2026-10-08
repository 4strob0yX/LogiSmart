# ============================================================
# EXPORTADOR DE REPORTES (CSV, JSON, HTML / PDF)
# ============================================================
# Módulo: export_reports.py
# Permite exportar bitácoras de accesos, incidentes clasificados
# y matriz de riesgos éticos en formatos estándar.
# ============================================================
import csv
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.database import db_servicio
from ai_services.matriz_riesgos import gestor_riesgos


DIRECTORIO_REPORTES = "reportes_exportados"


def asegurar_directorio():
    if not os.path.exists(DIRECTORIO_REPORTES):
        os.makedirs(DIRECTORIO_REPORTES, exist_ok=True)


def exportar_accesos_csv() -> str:
    asegurar_directorio()
    ruta = os.path.join(DIRECTORIO_REPORTES, f"bitacora_accesos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    accesos = db_servicio.listar_accesos(limite=200)

    with open(ruta, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Timestamp", "Camion_ID", "Placa", "P", "Q", "R", "S", "T", "M", "A_Estandar", "E_Inspeccion", "Semaforo", "Decision", "Operador"])
        for a in accesos:
            writer.writerow([
                a.get("_id"), a.get("marca_de_tiempo"), a.get("camion_id"), a.get("placa"),
                a.get("P"), a.get("Q"), a.get("R"), a.get("S"), a.get("T"), a.get("M"),
                a.get("resultado_A"), a.get("resultado_E"), a.get("semaforo"), a.get("decision"),
                a.get("operador")
            ])
    return ruta


def exportar_incidentes_csv() -> str:
    asegurar_directorio()
    ruta = os.path.join(DIRECTORIO_REPORTES, f"incidentes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    incidentes = db_servicio.listar_incidentes()

    with open(ruta, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Fecha", "Categoria", "Prioridad", "Estado", "Revision_Humana", "Resumen"])
        for inc in incidentes:
            writer.writerow([
                inc.get("_id"), inc.get("fecha_reporte"), inc.get("categoria"),
                inc.get("prioridad"), inc.get("estado"), inc.get("requiere_revision_humana"),
                inc.get("resumen")
            ])
    return ruta


def exportar_sistema_completo_json() -> str:
    asegurar_directorio()
    ruta = os.path.join(DIRECTORIO_REPORTES, f"respaldo_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    datos = {
        "exportado_en": datetime.now().isoformat(),
        "sistema": "LogiSmart Python Suite v2.4",
        "camiones": db_servicio.listar_camiones(),
        "accesos": db_servicio.listar_accesos(limite=500),
        "incidentes": db_servicio.listar_incidentes(),
        "riesgos_eticos": db_servicio.listar_riesgos_eticos()
    }

    with open(ruta, mode="w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)
    return ruta


def exportar_informe_html_pdf() -> str:
    """
    Genera un informe gerencial formateado en HTML profesional con
    reglas CSS de paginación para guardarse como PDF desde cualquier navegador.
    """
    asegurar_directorio()
    ruta = os.path.join(DIRECTORIO_REPORTES, f"informe_auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")

    accesos = db_servicio.listar_accesos(limite=10)
    incidentes = db_servicio.listar_incidentes()
    riesgos = db_servicio.listar_riesgos_eticos()
    stats_riesgos = gestor_riesgos.calcular_estadisticas_riesgo()

    criticos = sum(1 for i in incidentes if i.get("prioridad") == "CRITICA")
    altos = sum(1 for i in incidentes if i.get("prioridad") == "ALTA")

    filas_accesos_html = ""
    for a in accesos:
        color = "#10b981" if a.get("semaforo") == "VERDE" else ("#f59e0b" if a.get("semaforo") == "AMARILLO" else "#ef4444")
        filas_accesos_html += f"""
        <tr>
            <td>{a.get('camion_id')}</td>
            <td>{a.get('placa')}</td>
            <td>P={int(a.get('P',0))} Q={int(a.get('Q',0))} R={int(a.get('R',0))} S={int(a.get('S',0))}</td>
            <td style="color:{color}; font-weight:bold;">{a.get('decision')}</td>
            <td>{a.get('marca_de_tiempo')[:16]}</td>
        </tr>
        """

    filas_riesgos_html = ""
    for r in riesgos:
        filas_riesgos_html += f"""
        <tr>
            <td><strong>{r.get('modulo')}</strong><br><small>{r.get('categoria')}</small></td>
            <td>{r.get('descripcion')}</td>
            <td>{r.get('riesgo_inherente_score')}</td>
            <td>{r.get('mitigacion')}</td>
            <td style="color:#059669; font-weight:bold;">{r.get('riesgo_residual_score')}</td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Reporte de Auditoría LogiSmart</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 30px; color: #1e293b; }}
    h1 {{ color: #0f172a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; }}
    h2 {{ color: #1e3a8a; margin-top: 25px; }}
    .badge {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 13px; }}
    .kpi-container {{ display: flex; gap: 15px; margin: 20px 0; }}
    .kpi {{ flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; text-align: center; }}
    .kpi-num {{ font-size: 26px; font-weight: bold; color: #2563eb; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px 12px; text-align: left; }}
    th {{ background: #f1f5f9; }}
    @media print {{
        button {{ display: none; }}
        body {{ margin: 0; }}
    }}
</style>
</head>
<body>
    <button onclick="window.print()" style="float:right; padding:10px 18px; background:#09090b; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:600;">Imprimir / Guardar como PDF</button>
    <h1>INFORME OFICIAL DE AUDITORÍA - LOGISMART IA</h1>
    <p><strong>Fecha de Emisión:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | <strong>Entorno:</strong> Centro de Control Ciberfísico</p>
    
    <div class="kpi-container">
        <div class="kpi"><div>Total Incidentes</div><div class="kpi-num">{len(incidentes)}</div></div>
        <div class="kpi"><div>Incidentes Críticos</div><div class="kpi-num" style="color:#dc2626;">{criticos}</div></div>
        <div class="kpi"><div>Reducción Riesgo Ético</div><div class="kpi-num" style="color:#059669;">{stats_riesgos['reduccion_porcentual']}%</div></div>
        <div class="kpi"><div>Accesos Registrados</div><div class="kpi-num">{len(accesos)}</div></div>
    </div>

    <h2>1. Bitácora de Accesos Recientes en Garita</h2>
    <table>
        <thead>
            <tr><th>Camión</th><th>Placa</th><th>Vector (P,Q,R,S)</th><th>Decisión / Semáforo</th><th>Marca de Tiempo</th></tr>
        </thead>
        <tbody>
            {filas_accesos_html}
        </tbody>
    </table>

    <h2>2. Matriz de Riesgos Éticos y Reducción Residual</h2>
    <table>
        <thead>
            <tr><th>Módulo / Categoría</th><th>Descripción</th><th>Score Inherente</th><th>Mitigación Implementada</th><th>Score Residual</th></tr>
        </thead>
        <tbody>
            {filas_riesgos_html}
        </tbody>
    </table>

    <hr style="margin-top:40px; border:0; border-top:1px solid #e2e8f0;">
    <p style="font-size:12px; color:#64748b; text-align:center;">Sistema Desarrollado para la Práctica Integradora de Inteligencia Artificial y Sistemas Complejos.</p>
</body>
</html>
"""

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(html_content)
    return ruta


if __name__ == "__main__":
    print("CSV Accesos:", exportar_accesos_csv())
    print("CSV Incidentes:", exportar_incidentes_csv())
    print("JSON Completo:", exportar_sistema_completo_json())
    print("HTML/PDF:", exportar_informe_html_pdf())
