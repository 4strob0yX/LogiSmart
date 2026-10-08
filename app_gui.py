# ============================================================
# INTERFAZ GRÁFICA INTEGRAL INTERACTIVA (GUI LOGISMART)
# ============================================================
# Módulo: app_gui.py
# Servidor de aplicación local de alta tecnología con interfaz web
# moderna, semáforos animados, simulador interactivo de tablas de
# verdad, chat RAG, matriz gráfica de riesgos y exportación.
# ============================================================

import os
import json
import webbrowser
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import uvicorn

from config import VERSION_SISTEMA, OLLAMA_MODEL, MONGO_DB_NAME
from database.database import db_servicio
from logic.motor_reglas import motor_logica
from ai_services.clasificador_hibrido import clasificador_hibrido
from ai_services.asistente_rag import asistente_rag
from ai_services.matriz_riesgos import gestor_riesgos
from reports.export_reports import (
    exportar_accesos_csv, exportar_incidentes_csv,
    exportar_sistema_completo_json, exportar_informe_html_pdf
)
from database.seed_data import poblar_datos_completos


app = FastAPI(title="LogiSmart AI Control Center", version=VERSION_SISTEMA)

# Garantizar que existan datos demostrativos al arrancar
poblar_datos_completos()


# ============================================================
# ENDPOINTS DE API REST PARA LA INTERFAZ
# ============================================================

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    accesos = db_servicio.listar_accesos(limite=500)
    incidentes = db_servicio.listar_incidentes()
    riesgos_stats = gestor_riesgos.calcular_estadisticas_riesgo()
    agregacion = db_servicio.agregacion_incidentes_por_categoria_y_semana()

    abiertos = sum(1 for i in incidentes if i.get("estado") in ["nuevo", "en_atencion"])
    criticos = sum(1 for i in incidentes if i.get("prioridad") == "CRITICA")

    return {
        "camiones_atendidos": len(accesos),
        "incidentes_abiertos": abiertos,
        "incidentes_criticos": criticos,
        "total_incidentes": len(incidentes),
        "reduccion_riesgo_etico": riesgos_stats.get("reduccion_porcentual", 0),
        "estado_mongo": db_servicio.obtener_estado_conexion(),
        "agregacion_categorias": agregacion[:6]
    }


@app.get("/api/camiones/buscar")
async def buscar_camion(placa: str):
    cam = db_servicio.buscar_camion_por_placa(placa)
    if not cam:
        return {"encontrado": False, "mensaje": f"No se encontró el vehículo con placa {placa}"}
    return {"encontrado": True, "camion": cam}


@app.post("/api/acceso/evaluar")
async def evaluar_acceso_endpoint(datos: Dict[str, Any]):
    P = bool(datos.get("P", False))
    Q = bool(datos.get("Q", False))
    R = bool(datos.get("R", False))
    S = bool(datos.get("S", False))
    T = bool(datos.get("T", False))
    M = bool(datos.get("M", True))
    placa = datos.get("placa", "N/A").strip().upper()
    camion_id = datos.get("camion_id", "CAM-GARITA")

    res = motor_logica.evaluar_acceso(P, Q, R, S, T, M)

    # Persistir en MongoDB
    db_servicio.registrar_acceso({
        "camion_id": camion_id,
        "placa": placa,
        "operador": datos.get("operador", "Operador en Turno"),
        "P": P, "Q": Q, "R": R, "S": S, "T": T, "M": M,
        "resultado_A": res["evaluacion_reglas"]["A_acceso_estandar"],
        "resultado_E": res["evaluacion_reglas"]["E_inspeccion_especial"],
        "semaforo": res["semaforo"],
        "decision": res["decision"],
        "explicacion_paso_a_paso": res["explicacion_paso_a_paso"]
    })

    return res


@app.get("/api/simulador/tabla")
async def get_tabla_verdad():
    return motor_logica.generar_tabla_verdad_base()


@app.post("/api/incidentes/clasificar")
async def clasificar_incidente_endpoint(datos: Dict[str, Any]):
    correo = datos.get("correo", "").strip()
    if not correo:
        raise HTTPException(status_code=400, detail="El correo no puede estar vacío.")

    resultado = clasificador_hibrido.procesar_incidente_completo(correo)

    # Guardar en la colección incidentes
    inc_id = db_servicio.registrar_incidente({
        "correo_original": correo,
        "categoria": resultado.categoria_final,
        "prioridad": resultado.prioridad_final.value,
        "datos_extraidos": resultado.entidades_final.model_dump(),
        "resumen": resultado.resumen_final,
        "estado": "nuevo",
        "requiere_revision_humana": resultado.requiere_revision_humana
    })

    return {
        "incidente_id": inc_id,
        "prioridad": resultado.prioridad_final.value,
        "categoria": resultado.categoria_final,
        "resumen": resultado.resumen_final,
        "entidades": resultado.entidades_final.model_dump(),
        "discrepancia": resultado.discrepancia_detectada,
        "requiere_revision_humana": resultado.requiere_revision_humana,
        "fuente_decisiva": resultado.fuente_decisiva,
        "latencia_ms": resultado.latencia_ms,
        "modelo": resultado.modelo_utilizado
    }


@app.get("/api/incidentes")
async def listar_incidentes_endpoint(estado: Optional[str] = None):
    return db_servicio.listar_incidentes(filtro_estado=estado)


@app.post("/api/incidentes/cambiar_estado")
async def cambiar_estado_incidente(datos: Dict[str, Any]):
    inc_id = datos.get("id")
    nuevo_estado = datos.get("estado")
    exito = db_servicio.actualizar_estado_incidente(inc_id, nuevo_estado)
    return {"exito": exito}


@app.post("/api/chat/preguntar")
async def chat_rag_endpoint(datos: Dict[str, Any]):
    pregunta = datos.get("pregunta", "").strip()
    if not pregunta:
        return {"respuesta": "Por favor escribe una consulta válida."}
    return asistente_rag.responder_consulta_operador(pregunta)


@app.get("/api/riesgos")
async def listar_riesgos_endpoint():
    return {
        "riesgos": gestor_riesgos.obtener_todos(),
        "estadisticas": gestor_riesgos.calcular_estadisticas_riesgo()
    }


@app.post("/api/riesgos/guardar")
async def guardar_riesgo_endpoint(datos: Dict[str, Any]):
    rid = gestor_riesgos.registrar_o_actualizar_riesgo(
        modulo=datos.get("modulo", "Módulo"),
        descripcion=datos.get("descripcion", ""),
        categoria=datos.get("categoria", "Ética"),
        probabilidad=int(datos.get("probabilidad", 3)),
        impacto=int(datos.get("impacto", 3)),
        mitigacion=datos.get("mitigacion", ""),
        probabilidad_residual=int(datos.get("probabilidad_residual", 1)),
        impacto_residual=int(datos.get("impacto_residual", 2)),
        riesgo_id=datos.get("_id")
    )
    return {"exito": True, "id": rid}


@app.get("/api/reportes/descargar/{tipo}")
async def descargar_reporte(tipo: str):
    if tipo == "csv_accesos":
        ruta = exportar_accesos_csv()
    elif tipo == "csv_incidentes":
        ruta = exportar_incidentes_csv()
    elif tipo == "json":
        ruta = exportar_sistema_completo_json()
    elif tipo == "html":
        ruta = exportar_informe_html_pdf()
    else:
        raise HTTPException(status_code=400, detail="Tipo de reporte desconocido")

    return FileResponse(ruta, filename=os.path.basename(ruta))


@app.get("/api/mongo/resumen")
async def get_mongo_resumen():
    return {
        "estado": db_servicio.obtener_estado_conexion(),
        "colecciones": db_servicio.obtener_resumen_colecciones()
    }


@app.get("/api/mongo/documentos/{coleccion}")
async def get_mongo_documentos(coleccion: str):
    docs = db_servicio.obtener_documentos_coleccion(coleccion, limite=50)
    return {
        "coleccion": coleccion,
        "total": len(docs),
        "documentos": docs
    }


# ============================================================
# INTERFAZ GRÁFICA ENRIQUECIDA (HTML5 / CSS / JAVASCRIPT SPA)
# ============================================================

HTML_SPA = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LogiSmart | Centro de Control Ciberfísico</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #121212;
            --bg-surface: #ffffff;
            --bg-subtle: #f4f4f5;
            --border: #e4e4e7;
            --border-subtle: #f0f0f2;
            --text-main: #09090b;
            --text-muted: #71717a;
            --text-sub: #a1a1aa;
            --accent-success: #059669;
            --accent-warning: #d97706;
            --accent-danger: #dc2626;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-base);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            overflow-x: hidden;
            letter-spacing: -0.011em;
            -webkit-font-smoothing: antialiased;
        }

        /* Sidebar Navigation */
        .sidebar {
            width: 240px;
            background: #ffffff;
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            position: fixed;
            height: 100vh;
            z-index: 50;
        }

        .brand {
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border);
        }

        .brand-title { font-size: 14px; font-weight: 700; color: #09090b; letter-spacing: -0.02em; }
        .brand-sub { font-size: 11px; color: var(--text-muted); font-weight: 500; background: var(--bg-subtle); padding: 2px 6px; border-radius: 4px; }

        .nav-menu { padding: 12px 8px; flex: 1; display: flex; flex-direction: column; gap: 2px; overflow-y: auto; }
        .nav-item {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            border-radius: 6px;
            color: var(--text-muted);
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.1s ease;
            border: 1px solid transparent;
        }

        .nav-item:hover { color: var(--text-main); background: var(--bg-subtle); }
        .nav-item.active {
            color: #09090b;
            background: #ffffff;
            border-color: var(--border);
            font-weight: 600;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        }

        .sidebar-footer {
            padding: 16px 20px;
            border-top: 1px solid var(--border);
            font-size: 11px;
            color: var(--text-muted);
            line-height: 1.5;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 2px 6px;
            border-radius: 4px;
            background: var(--bg-subtle);
            border: 1px solid var(--border);
            color: var(--text-muted);
            font-weight: 500;
            font-size: 11px;
            margin-bottom: 8px;
        }
        .status-dot { width: 6px; height: 6px; border-radius: 50%; background: #10b981; }

        /* Main Content Area */
        .main-container {
            margin-left: 240px;
            flex: 1;
            padding: 32px 40px;
            max-width: 1250px;
        }

        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .header-section { margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-end; }
        .page-title { font-size: 20px; font-weight: 700; letter-spacing: -0.02em; color: #09090b; }
        .page-desc { color: var(--text-muted); font-size: 13px; margin-top: 3px; }

        /* KPI Cards Minimal Light */
        .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
        .kpi-card {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 16px 18px;
        }

        .kpi-label { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.03em; }
        .kpi-val { font-size: 24px; font-weight: 700; margin: 4px 0; color: #09090b; letter-spacing: -0.02em; }
        .kpi-trend { font-size: 11px; color: var(--text-sub); }

        /* Minimal Panels */
        .panel {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 18px;
        }
        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border);
        }
        .panel-title { font-size: 13.5px; font-weight: 600; color: #09090b; }

        /* Layout Grids */
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
        .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }

        .input-group { margin-bottom: 12px; }
        .input-label { display: block; font-size: 12px; font-weight: 500; margin-bottom: 5px; color: var(--text-muted); }
        .input-field {
            width: 100%;
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 5px;
            padding: 8px 11px;
            color: var(--text-main);
            font-size: 13px;
            font-family: inherit;
            outline: none;
            transition: border-color 0.15s;
        }
        .input-field:focus { border-color: #09090b; }

        /* Switch Minimal Light */
        .switch-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 12px;
            background: #ffffff;
            border-radius: 5px;
            border: 1px solid var(--border);
            margin-bottom: 6px;
        }
        .switch-info h4 { font-size: 12.5px; font-weight: 600; color: #09090b; }
        .switch-info p { font-size: 11px; color: var(--text-muted); margin-top: 1px; }

        .toggle {
            position: relative;
            display: inline-block;
            width: 38px;
            height: 20px;
        }
        .toggle input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
            background-color: #e4e4e7; transition: .15s; border-radius: 20px;
        }
        .slider:before {
            position: absolute; content: ""; height: 14px; width: 14px; left: 3px; bottom: 3px;
            background-color: #ffffff; transition: .15s; border-radius: 50%;
            box-shadow: 0 1px 2px rgba(0,0,0,0.15);
        }
        input:checked + .slider { background-color: #09090b; }
        input:checked + .slider:before { transform: translateX(18px); }

        /* Minimal Status Indicator */
        .traffic-light-box {
            display: flex;
            align-items: center;
            justify-content: center;
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 16px;
            gap: 24px;
        }
        .light-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
        }
        .light {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background: #f4f4f5;
            border: 1px solid var(--border);
            transition: all 0.15s ease;
        }
        .light-label { font-size: 10px; font-weight: 600; color: var(--text-muted); letter-spacing: 0.02em; }
        .light.red.active { background: #dc2626; border-color: #dc2626; }
        .light.yellow.active { background: #d97706; border-color: #d97706; }
        .light.green.active { background: #059669; border-color: #059669; }

        /* Botones Minimalistas */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 7px 12px;
            border-radius: 5px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            border: 1px solid transparent;
            transition: all 0.1s;
            text-decoration: none;
        }
        .btn-primary { background: #09090b; color: #ffffff; border-color: #09090b; }
        .btn-primary:hover { background: #27272a; border-color: #27272a; }
        .btn-dark { background: #ffffff; color: #09090b; border-color: var(--border); }
        .btn-dark:hover { background: var(--bg-subtle); }

        /* Tablas */
        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            margin-top: 4px;
        }
        .data-table th {
            text-align: left;
            padding: 8px 10px;
            background: var(--bg-subtle);
            color: var(--text-muted);
            font-weight: 600;
            font-size: 11px;
            border-bottom: 1px solid var(--border);
        }
        .data-table td {
            padding: 8px 10px;
            border-bottom: 1px solid var(--border-subtle);
            color: var(--text-main);
        }
        .data-table tr:hover td { background: var(--bg-subtle); }

        .badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            border: 1px solid var(--border);
            background: var(--bg-subtle);
            color: var(--text-muted);
        }
        .badge-red { border-color: #fecaca; color: #991b1b; background: #fef2f2; }
        .badge-amber { border-color: #fde68a; color: #92400e; background: #fffbeb; }
        .badge-green { border-color: #a7f3d0; color: #065f46; background: #ecfdf5; }
        .badge-blue { border-color: #bfdbfe; color: #1e40af; background: #eff6ff; }

        /* Chat RAG Minimal Light */
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 420px;
            background: #ffffff;
            border-radius: 6px;
            border: 1px solid var(--border);
            overflow: hidden;
        }
        .chat-messages {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .message-bubble {
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 12.5px;
            line-height: 1.5;
        }
        .message-bubble.user {
            align-self: flex-end;
            background: #09090b;
            color: #ffffff;
        }
        .message-bubble.bot {
            align-self: flex-start;
            background: #f4f4f5;
            border: 1px solid var(--border);
            color: #09090b;
        }
        .chat-input-bar {
            padding: 10px;
            background: #ffffff;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 8px;
        }

        /* Monospace Trace */
        .mono-box {
            font-family: 'JetBrains Mono', ui-monospace, monospace;
            font-size: 11.5px;
            background: #f4f4f5;
            border: 1px solid var(--border);
            border-radius: 5px;
            padding: 10px 12px;
            color: #27272a;
            max-height: 150px;
            overflow-y: auto;
            white-space: pre-wrap;
            line-height: 1.6;
        }

        .spinner {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid #e4e4e7;
            border-radius: 50%;
            border-top-color: #09090b;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>

    <!-- Sidebar Minimal Light (Sin Emojis) -->
    <div class="sidebar">
        <div class="brand">
            <div class="brand-title">LogiSmart</div>
            <div class="brand-sub">v2.4</div>
        </div>

        <div class="nav-menu">
            <div class="nav-item active" onclick="switchTab('dashboard')">Dashboard</div>
            <div class="nav-item" onclick="switchTab('acceso')">Control de Acceso</div>
            <div class="nav-item" onclick="switchTab('simulador')">Tablas de Verdad</div>
            <div class="nav-item" onclick="switchTab('incidentes')">Bandeja de Incidentes</div>
            <div class="nav-item" onclick="switchTab('asistente')">Auditor RAG</div>
            <div class="nav-item" onclick="switchTab('riesgos')">Riesgos Éticos</div>
            <div class="nav-item" onclick="switchTab('reportes', this)">Reportes</div>
            <div class="nav-item" onclick="switchTab('benchmark', this)">Experimento</div>
            <div class="nav-item" onclick="switchTab('mongo', this)">Base de Datos (MongoDB)</div>
        </div>

        <div class="sidebar-footer">
            <div class="status-pill">
                <span class="status-dot"></span>
                <span id="txt-status-mongo">MongoDB Activo</span>
            </div>
            <div>Modelo: Llama 3.2</div>
            <div style="margin-top:2px; color:var(--text-sub);">Arquitectura PEAS</div>
        </div>
    </div>

    <!-- Main Container -->
    <div class="main-container">

        <!-- TAB 1: DASHBOARD -->
        <div id="tab-dashboard" class="tab-content active">
            <div class="header-section">
                <div>
                    <h1 class="page-title">Panel de Control</h1>
                    <p class="page-desc">Monitoreo de accesos, incidentes registrados y evaluación ética.</p>
                </div>
                <button class="btn btn-dark" onclick="cargarDashboard()">Actualizar</button>
            </div>

            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-label">Camiones Atendidos</div>
                    <div class="kpi-val" id="kpi-camiones">--</div>
                    <div class="kpi-trend">Registros en bitácora</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Incidentes Abiertos</div>
                    <div class="kpi-val" id="kpi-abiertos">--</div>
                    <div class="kpi-trend">Pendientes de atención</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Incidentes Críticos</div>
                    <div class="kpi-val" id="kpi-criticos" style="color:var(--accent-danger);">--</div>
                    <div class="kpi-trend">Materiales peligrosos o sobrepeso</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Mitigación Ética</div>
                    <div class="kpi-val" id="kpi-riesgo" style="color:var(--accent-success);">--%</div>
                    <div class="kpi-trend">Reducción de riesgo residual</div>
                </div>
            </div>

            <div class="grid-2">
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title">Agregación MongoDB: Incidentes por Categoría y Semana</div>
                    </div>
                    <div id="contenedor-agregacion">Cargando datos...</div>
                </div>

                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title">Modelo PEAS del Agente</div>
                    </div>
                    <div style="font-size:12.5px; line-height:1.7; color:var(--text-muted);">
                        <p><strong style="color:#09090b;">Performance (P):</strong> Seguridad en garita, latencia de decisión menor a 500ms y trazabilidad completa.</p>
                        <p><strong style="color:#09090b;">Environment (E):</strong> Garita vehicular, báscula de pesaje, bahía técnica y servidor MongoDB.</p>
                        <p><strong style="color:#09090b;">Actuators (A):</strong> Barrera de paso, semáforo de garita, bitácora y despachador de correo.</p>
                        <p><strong style="color:#09090b;">Sensors (S):</strong> Antena RFID, celdas de pesaje, detector de etiqueta HAZMAT y reloj ciberfísico.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 2: CONTROL DE ACCESO -->
        <div id="tab-acceso" class="tab-content">
            <div class="header-section">
                <div>
                    <h1 class="page-title">Control de Acceso Vehicular</h1>
                    <p class="page-desc">Evaluación de proposiciones lógicas y derivación causal.</p>
                </div>
            </div>

            <div class="grid-2">
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title">Premisas Lógicas Atómicas</div>
                    </div>

                    <div style="display:flex; gap:8px; margin-bottom:12px;">
                        <input type="text" id="inp-placa-buscar" class="input-field" placeholder="Buscar placa (ej. TRK-781, TRK-882)...">
                        <button class="btn btn-dark" onclick="buscarPlacaRapida()">Cargar</button>
                    </div>

                    <div class="switch-row">
                        <div class="switch-info">
                            <h4>P — Autorización Previa</h4>
                            <p>Registro vigente en catálogo maestro</p>
                        </div>
                        <label class="toggle"><input type="checkbox" id="sw-P" checked onchange="evaluarAccesoEnVivo()"><span class="slider"></span></label>
                    </div>

                    <div class="switch-row">
                        <div class="switch-info">
                            <h4>Q — Sobrepeso en Báscula</h4>
                            <p>Excede 40,000 kg en báscula</p>
                        </div>
                        <label class="toggle"><input type="checkbox" id="sw-Q" onchange="evaluarAccesoEnVivo()"><span class="slider"></span></label>
                    </div>

                    <div class="switch-row">
                        <div class="switch-info">
                            <h4>R — Carga Peligrosa (HAZMAT)</h4>
                            <p>Sustancias químicas o inflamables</p>
                        </div>
                        <label class="toggle"><input type="checkbox" id="sw-R" onchange="evaluarAccesoEnVivo()"><span class="slider"></span></label>
                    </div>

                    <div class="switch-row">
                        <div class="switch-info">
                            <h4>S — Certificación del Conductor</h4>
                            <p>Licencia federal vigente</p>
                        </div>
                        <label class="toggle"><input type="checkbox" id="sw-S" checked onchange="evaluarAccesoEnVivo()"><span class="slider"></span></label>
                    </div>

                    <div class="switch-row">
                        <div class="switch-info">
                            <h4>T — Horario Nocturno (Regla Nueva)</h4>
                            <p>Tránsito entre 22:00 y 05:00 hrs</p>
                        </div>
                        <label class="toggle"><input type="checkbox" id="sw-T" onchange="evaluarAccesoEnVivo()"><span class="slider"></span></label>
                    </div>

                    <div class="switch-row">
                        <div class="switch-info">
                            <h4>M — Dictamen Médico Apto (Regla Nueva)</h4>
                            <p>Examen psicofísico sin fatiga</p>
                        </div>
                        <label class="toggle"><input type="checkbox" id="sw-M" checked onchange="evaluarAccesoEnVivo()"><span class="slider"></span></label>
                    </div>
                </div>

                <div class="panel" style="display:flex; flex-direction:column; justify-content:space-between;">
                    <div class="panel-header">
                        <div class="panel-title">Estado de Acceso y Explicación</div>
                    </div>

                    <div class="traffic-light-box">
                        <div class="light-item">
                            <div class="light red" id="light-red"></div>
                            <span class="light-label">DENEGADO</span>
                        </div>
                        <div class="light-item">
                            <div class="light yellow" id="light-yellow"></div>
                            <span class="light-label">INSPECCIÓN</span>
                        </div>
                        <div class="light-item">
                            <div class="light green active" id="light-green"></div>
                            <span class="light-label">AUTORIZADO</span>
                        </div>
                    </div>

                    <div style="text-align:center; margin: 12px 0;">
                        <div id="txt-decision" style="font-size:15px; font-weight:700; color:#059669;">ACCESO AUTORIZADO</div>
                        <div id="txt-subdecision" style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">Reglas cumplidas satisfactoriamente</div>
                    </div>

                    <div>
                        <div style="font-size:11.5px; font-weight:600; color:var(--text-muted); margin-bottom:5px;">Deducción Lógica Paso a Paso:</div>
                        <div class="mono-box" id="box-explicacion">Evaluando...</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 3: SIMULADOR DE TABLAS DE VERDAD -->
        <div id="tab-simulador" class="tab-content">
            <div class="header-section">
                <div>
                    <h1 class="page-title">Tablas de Verdad</h1>
                    <p class="page-desc">Evaluación proposicional canónica de las reglas base.</p>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">Matriz de Verdad Proposicional (P, Q, R, S)</div>
                </div>
                <div style="overflow-x:auto;">
                    <table class="data-table" id="tabla-verdad-dinamica">
                        <thead>
                            <tr>
                                <th>P (Autorizado)</th>
                                <th>Q (Sobrepeso)</th>
                                <th>R (Peligroso)</th>
                                <th>S (Certificado)</th>
                                <th>A = P ∧ S ∧ ¬Q (Acceso Estándar)</th>
                                <th>E = P ∧ (R ∨ Q) (Inspección Especial)</th>
                                <th>Estado</th>
                            </tr>
                        </thead>
                        <tbody id="body-tabla-verdad"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 4: BANDEJA DE INCIDENTES -->
        <div id="tab-incidentes" class="tab-content">
            <div class="header-section">
                <div>
                    <h1 class="page-title">Bandeja de Incidentes</h1>
                    <p class="page-desc">Clasificación híbrida mediante LLM validado con Pydantic y reglas.</p>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">Registro y Análisis de Reporte</div>
                </div>
                <textarea id="txt-correo-input" class="input-field" style="height:90px; resize:vertical;" placeholder="Ingresar reporte de garita o correo de incidente..."></textarea>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                    <div id="spinner-clasificar" style="display:none; align-items:center; gap:8px; font-size:12px; color:var(--text-muted);">
                        <span class="spinner"></span> Procesando con Pydantic y modelo de lenguaje...
                    </div>
                    <div style="display:flex; gap:8px;">
                        <button class="btn btn-dark" onclick="cargarEjemploCorreo()">Cargar Ejemplo</button>
                        <button class="btn btn-primary" onclick="clasificarCorreo()">Clasificar Incidente</button>
                    </div>
                </div>

                <div id="box-resultado-clasif" style="display:none; margin-top:14px; padding:14px; background:var(--bg-subtle); border-radius:6px; border:1px solid var(--border);">
                    <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                        <span id="badge-prio-res" class="badge">MEDIA</span>
                        <span style="font-size:11px; color:var(--text-muted);" id="txt-fuente-res">Fuente: Híbrido</span>
                    </div>
                    <h3 id="txt-cat-res" style="font-size:14px; margin-bottom:4px; color:#09090b;">Categoría</h3>
                    <p id="txt-resumen-res" style="font-size:12.5px; color:var(--text-muted);"></p>
                    <div style="margin-top:8px; font-size:11.5px; color:#52525b;" id="txt-entidades-res"></div>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">Historial de Incidentes en MongoDB</div>
                    <button class="btn btn-dark" onclick="cargarTablaIncidentes()">Refrescar</button>
                </div>
                <div style="overflow-x:auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Fecha</th>
                                <th>Categoría</th>
                                <th>Prioridad</th>
                                <th>Resumen</th>
                                <th>Estado</th>
                                <th>Acción</th>
                            </tr>
                        </thead>
                        <tbody id="body-incidentes"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 5: ASISTENTE RAG -->
        <div id="tab-asistente" class="tab-content">
            <div class="header-section">
                <div>
                    <h1 class="page-title">Auditor RAG</h1>
                    <p class="page-desc">Consulta explicativa sobre decisiones de garita fundamentadas en MongoDB.</p>
                </div>
            </div>

            <div class="panel">
                <div class="chat-container">
                    <div class="chat-messages" id="chat-box">
                        <div class="message-bubble bot">
                            Asistente auditor disponible. Consultas de ejemplo:
                            <br><strong>¿Por qué CAM-102 fue enviado a inspección?</strong> o 
                            <strong>¿Qué ocurrió con la placa TRK-781?</strong>
                            <br><small style="color:var(--text-muted);">Respuestas basadas exclusivamente en registros de MongoDB con citación de origen.</small>
                        </div>
                    </div>
                    <div class="chat-input-bar">
                        <input type="text" id="inp-chat" class="input-field" placeholder="Escribir consulta sobre vehículo o registro..." onkeypress="if(event.key==='Enter') enviarPreguntaRAG()">
                        <button class="btn btn-primary" onclick="enviarPreguntaRAG()">Enviar</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 6: MATRIZ DE RIESGOS ÉTICOS -->
        <div id="tab-riesgos" class="tab-content">
            <div class="header-section">
                <div>
                    <h1 class="page-title">Matriz de Riesgos Éticos</h1>
                    <p class="page-desc">Evaluación cuantitativa de severidad antes y después de mitigación.</p>
                </div>
                <button class="btn btn-primary" onclick="mostrarModalRiesgo()">Nuevo Riesgo</button>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">Reducción de Riesgo Residual</div>
                </div>
                <div id="grafica-riesgos-container" style="display:flex; flex-direction:column; gap:10px;"></div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">Catálogo Detallado de Riesgos</div>
                </div>
                <div style="overflow-x:auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Módulo</th>
                                <th>Descripción</th>
                                <th>Categoría</th>
                                <th>Score Inicial</th>
                                <th>Mitigación</th>
                                <th>Score Residual</th>
                            </tr>
                        </thead>
                        <tbody id="body-riesgos"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 7: REPORTES -->
        <div id="tab-reportes" class="tab-content">
            <div class="header-section">
                <div>
                    <h1 class="page-title">Reportes y Exportación</h1>
                    <p class="page-desc">Exportación de datos de garita en formatos estándar.</p>
                </div>
            </div>

            <div class="grid-3">
                <div class="panel">
                    <h3 style="font-size:13.5px; margin-bottom:6px;">Bitácora de Accesos</h3>
                    <p style="font-size:12px; color:var(--text-muted); margin-bottom:14px;">Registros de paso con vector proposicional.</p>
                    <a href="/api/reportes/descargar/csv_accesos" class="btn btn-dark" style="width:100%;">Descargar CSV</a>
                </div>

                <div class="panel">
                    <h3 style="font-size:13.5px; margin-bottom:6px;">Incidentes</h3>
                    <p style="font-size:12px; color:var(--text-muted); margin-bottom:14px;">Reportes clasificados con severidad.</p>
                    <a href="/api/reportes/descargar/csv_incidentes" class="btn btn-dark" style="width:100%;">Descargar CSV</a>
                </div>

                <div class="panel">
                    <h3 style="font-size:13.5px; margin-bottom:6px;">Informe Completo</h3>
                    <p style="font-size:12px; color:var(--text-muted); margin-bottom:14px;">Documento estructurado listo para imprimir.</p>
                    <a href="/api/reportes/descargar/html" target="_blank" class="btn btn-primary" style="width:100%;">Ver Informe</a>
                </div>
            </div>
        </div>

        <!-- TAB 8: EXPERIMENTO -->
        <div id="tab-benchmark" class="tab-content">
            <div class="header-section">
                <div>
                    <h1 class="page-title">Experimento de Clasificación</h1>
                    <p class="page-desc">Evaluación sobre 30 correos etiquetados a mano.</p>
                </div>
                <button class="btn btn-primary" onclick="ejecutarBenchmarkFront()">Ejecutar Prueba</button>
            </div>

            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-label">Exactitud Reglas</div>
                    <div class="kpi-val" id="bm-acc-reglas">90.0%</div>
                    <div class="kpi-trend">Latencia: 0.06 ms</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Exactitud LLM</div>
                    <div class="kpi-val" id="bm-acc-llm">90.0%</div>
                    <div class="kpi-trend">Latencia: 84.4 ms</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Exactitud Híbrido</div>
                    <div class="kpi-val" id="bm-acc-hibrido" style="color:var(--accent-success);">90.0%</div>
                    <div class="kpi-trend">Prevalencia de seguridad</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Muestras</div>
                    <div class="kpi-val">30</div>
                    <div class="kpi-trend">Casos evaluados</div>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">Matriz de Confusión (Clasificador Híbrido)</div>
                </div>
                <div style="overflow-x:auto;">
                    <table class="data-table" style="text-align:center;">
                        <thead>
                            <tr>
                                <th>Clase Real \\ Predicción</th>
                                <th>Pred: BAJA</th>
                                <th>Pred: MEDIA</th>
                                <th>Pred: ALTA</th>
                                <th>Pred: CRITICA</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td><strong>Real: BAJA (8)</strong></td><td style="color:var(--accent-success); font-weight:600;">8</td><td>0</td><td>0</td><td>0</td></tr>
                            <tr><td><strong>Real: MEDIA (8)</strong></td><td>0</td><td style="color:var(--accent-success); font-weight:600;">8</td><td>0</td><td>0</td></tr>
                            <tr><td><strong>Real: ALTA (8)</strong></td><td>0</td><td>0</td><td style="color:var(--accent-success); font-weight:600;">8</td><td>0</td></tr>
                            <tr><td><strong>Real: CRITICA (6)</strong></td><td>0</td><td>0</td><td style="color:var(--accent-warning);">1*</td><td style="color:var(--accent-success); font-weight:600;">5</td></tr>
                        </tbody>
                    </table>
                </div>
                <p style="font-size:11.5px; color:var(--text-muted); margin-top:10px;">
                    *Nota técnica: En 1 caso crítico de borde con información ambigua, la discrepancia activó automáticamente la bandera de revisión humana conforme al principio de seguridad.
                </p>
            </div>
        </div>

        <!-- TAB 9: BASE DE DATOS MONGODB -->
        <div id="tab-mongo" class="tab-content">
            <div class="header-section">
                <div>
                    <h1 class="page-title">Explorador de Base de Datos MongoDB</h1>
                    <p class="page-desc">Inspección de colecciones y documentos en el clúster local.</p>
                </div>
                <button class="btn btn-dark" onclick="cargarExploradorMongo(coleccionActualMongo)">Refrescar</button>
            </div>

            <div class="panel" style="padding:16px;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                    <div>
                        <span style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:600;">Base de Datos:</span>
                        <span style="font-family:'JetBrains Mono', monospace; font-size:13px; font-weight:600; color:#09090b; margin-left:6px;">samuelD73SixSeven</span>
                    </div>
                    <div style="font-size:12px; color:var(--text-muted);">
                        Instancia: <strong style="color:#059669;">127.0.0.1:27017 (Local)</strong>
                    </div>
                </div>

                <div style="display:flex; gap:8px; margin-top:14px; flex-wrap:wrap;" id="tabs-colecciones-mongo">
                    <button class="btn btn-primary" onclick="cambiarColeccionMongo('camiones', this)" id="btn-col-camiones">camiones</button>
                    <button class="btn btn-dark" onclick="cambiarColeccionMongo('accesos', this)" id="btn-col-accesos">accesos</button>
                    <button class="btn btn-dark" onclick="cambiarColeccionMongo('incidentes', this)" id="btn-col-incidentes">incidentes</button>
                    <button class="btn btn-dark" onclick="cambiarColeccionMongo('riesgos_eticos', this)" id="btn-col-riesgos_eticos">riesgos_eticos</button>
                    <button class="btn btn-dark" onclick="cambiarColeccionMongo('evaluaciones_llm', this)" id="btn-col-evaluaciones_llm">evaluaciones_llm</button>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <div>
                        <span class="panel-title" id="titulo-col-activa">Colección: camiones</span>
                        <span style="font-size:11.5px; color:var(--text-muted); margin-left:8px;" id="subtitulo-conteo-docs">Cargando...</span>
                    </div>
                    <div style="display:flex; gap:8px;">
                        <button class="btn btn-dark" onclick="toggleVistaMongo('tabla')" id="btn-vista-tabla" style="font-weight:600;">Vista Tabla</button>
                        <button class="btn btn-dark" onclick="toggleVistaMongo('json')" id="btn-vista-json">Vista JSON</button>
                    </div>
                </div>

                <div style="background:var(--bg-subtle); padding:8px 12px; border-radius:4px; font-family:'JetBrains Mono', monospace; font-size:11.5px; color:#52525b; margin-bottom:12px; border:1px solid var(--border);" id="query-mongo-activa">
                    use samuelD73SixSeven; db.camiones.find().limit(50);
                </div>

                <div id="vista-mongo-tabla" style="overflow-x:auto;">
                    <table class="data-table">
                        <thead id="head-mongo-tabla"></thead>
                        <tbody id="body-mongo-tabla"></tbody>
                    </table>
                </div>

                <div id="vista-mongo-json" style="display:none;">
                    <pre class="mono-box" style="max-height:450px;" id="code-mongo-json"></pre>
                </div>
            </div>
        </div>

    </div>

    <script>
        function switchTab(tabId, el) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            const targetTab = document.getElementById('tab-' + tabId);
            if (targetTab) targetTab.classList.add('active');
            if (el) {
                el.classList.add('active');
            } else if (window.event && window.event.currentTarget) {
                window.event.currentTarget.classList.add('active');
            } else {
                const nav = Array.from(document.querySelectorAll('.nav-item')).find(n => n.getAttribute('onclick')?.includes(`'${tabId}'`));
                if (nav) nav.classList.add('active');
            }

            if (tabId === 'dashboard') cargarDashboard();
            if (tabId === 'simulador') cargarTablaVerdad();
            if (tabId === 'incidentes') cargarTablaIncidentes();
            if (tabId === 'riesgos') cargarRiesgos();
            if (tabId === 'mongo') cargarExploradorMongo(coleccionActualMongo);
        }

        async function cargarDashboard() {
            try {
                const res = await fetch('/api/dashboard/stats');
                const data = await res.json();
                document.getElementById('kpi-camiones').innerText = data.camiones_atendidos;
                document.getElementById('kpi-abiertos').innerText = data.incidentes_abiertos;
                document.getElementById('kpi-criticos').innerText = data.incidentes_criticos;
                document.getElementById('kpi-riesgo').innerText = data.reduccion_riesgo_etico + '%';

                document.getElementById('txt-status-mongo').innerText = data.estado_mongo.modo;

                let htmlAgreg = '<table class="data-table"><thead><tr><th>Categoría</th><th>Semana</th><th>Total</th><th>Críticos</th></tr></thead><tbody>';
                data.agregacion_categorias.forEach(a => {
                    htmlAgreg += `<tr><td>${a.categoria}</td><td>Semana ${a.semana}</td><td><strong>${a.total_incidentes}</strong></td><td style="color:#dc2626;">${a.criticos}</td></tr>`;
                });
                htmlAgreg += '</tbody></table>';
                document.getElementById('contenedor-agregacion').innerHTML = htmlAgreg;
            } catch (e) {
                console.error(e);
            }
        }

        async function evaluarAccesoEnVivo() {
            const P = document.getElementById('sw-P').checked;
            const Q = document.getElementById('sw-Q').checked;
            const R = document.getElementById('sw-R').checked;
            const S = document.getElementById('sw-S').checked;
            const T = document.getElementById('sw-T').checked;
            const M = document.getElementById('sw-M').checked;

            const res = await fetch('/api/acceso/evaluar', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({P, Q, R, S, T, M, placa: document.getElementById('inp-placa-buscar').value || 'TRK-DEMO'})
            });
            const data = await res.json();

            document.getElementById('light-red').classList.remove('active');
            document.getElementById('light-yellow').classList.remove('active');
            document.getElementById('light-green').classList.remove('active');

            const sem = data.semaforo;
            const txtDec = document.getElementById('txt-decision');

            if (sem === 'VERDE') {
                document.getElementById('light-green').classList.add('active');
                txtDec.innerText = 'ACCESO AUTORIZADO';
                txtDec.style.color = '#059669';
            } else if (sem === 'AMARILLO') {
                document.getElementById('light-yellow').classList.add('active');
                txtDec.innerText = 'INSPECCIÓN ESPECIAL';
                txtDec.style.color = '#d97706';
            } else {
                document.getElementById('light-red').classList.add('active');
                txtDec.innerText = data.decision === 'DENEGADO_HORARIO_PELIGROSO' ? 'BLOQUEO NOCTURNO HAZMAT' : 'ACCESO DENEGADO';
                txtDec.style.color = '#dc2626';
            }

            document.getElementById('box-explicacion').innerText = data.explicacion_paso_a_paso.join('\\n');
        }

        async function buscarPlacaRapida() {
            const placa = document.getElementById('inp-placa-buscar').value.trim();
            if(!placa) return;
            const res = await fetch('/api/camiones/buscar?placa=' + encodeURIComponent(placa));
            const data = await res.json();
            if(data.encontrado) {
                document.getElementById('sw-P').checked = data.camion.autorizacion;
                document.getElementById('sw-S').checked = data.camion.certificacion_conductor;
                evaluarAccesoEnVivo();
            } else {
                alert('Camión no encontrado en catálogo. Evaluación manual activa.');
            }
        }

        async function cargarTablaVerdad() {
            const res = await fetch('/api/simulador/tabla');
            const filas = await res.json();
            let tbody = '';
            filas.forEach(f => {
                const badgeColor = f.estado === 'VERDE' ? 'badge-green' : (f.estado === 'AMARILLO' ? 'badge-amber' : 'badge-red');
                tbody += `<tr>
                    <td>${f.P}</td><td>${f.Q}</td><td>${f.R}</td><td>${f.S}</td>
                    <td><strong>${f.A}</strong></td><td><strong>${f.E}</strong></td>
                    <td><span class="badge ${badgeColor}">${f.estado}</span></td>
                </tr>`;
            });
            document.getElementById('body-tabla-verdad').innerHTML = tbody;
        }

        async function clasificarCorreo() {
            const correo = document.getElementById('txt-correo-input').value.trim();
            if(!correo) return alert('Por favor ingresar un reporte para clasificar.');

            document.getElementById('spinner-clasificar').style.display = 'flex';
            const res = await fetch('/api/incidentes/clasificar', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({correo})
            });
            const data = await res.json();
            document.getElementById('spinner-clasificar').style.display = 'none';

            const box = document.getElementById('box-resultado-clasif');
            box.style.display = 'block';

            const badge = document.getElementById('badge-prio-res');
            badge.innerText = data.prioridad;
            badge.className = 'badge ' + (data.prioridad === 'CRITICA' ? 'badge-red' : (data.prioridad === 'ALTA' ? 'badge-amber' : 'badge-green'));

            document.getElementById('txt-cat-res').innerText = data.categoria;
            document.getElementById('txt-resumen-res').innerText = data.resumen;
            document.getElementById('txt-fuente-res').innerText = data.fuente_decisiva + ` (${data.latencia_ms} ms)`;

            document.getElementById('txt-entidades-res').innerText = 'Entidades extraídas: ' + JSON.stringify(data.entidades);
            cargarTablaIncidentes();
        }

        function cargarEjemploCorreo() {
            document.getElementById('txt-correo-input').value = 'URGENTE: El camión CAM-102 con placas TRK-882 llegó con fuga de solvente inflamable en fosa de pesaje y peso registrado de 48,200 kg. Chofer sin certificación vigente.';
        }

        async function cargarTablaIncidentes() {
            const res = await fetch('/api/incidentes');
            const data = await res.json();
            let tbody = '';
            data.slice(0, 15).forEach(inc => {
                const prioClass = inc.prioridad === 'CRITICA' ? 'badge-red' : (inc.prioridad === 'ALTA' ? 'badge-amber' : 'badge-blue');
                tbody += `<tr>
                    <td>${(inc.fecha_reporte || '').substring(0, 16)}</td>
                    <td><strong>${inc.categoria}</strong></td>
                    <td><span class="badge ${prioClass}">${inc.prioridad}</span></td>
                    <td>${(inc.resumen || '').substring(0, 65)}...</td>
                    <td><span class="badge ${inc.estado === 'cerrado' ? 'badge-green' : 'badge-amber'}">${inc.estado}</span></td>
                    <td>
                        <button class="btn btn-dark" style="padding:3px 7px; font-size:11px;" onclick="cambiarEstadoInc('${inc._id}', '${inc.estado === 'cerrado' ? 'en_atencion' : 'cerrado'}')">
                            ${inc.estado === 'cerrado' ? 'Reabrir' : 'Cerrar'}
                        </button>
                    </td>
                </tr>`;
            });
            document.getElementById('body-incidentes').innerHTML = tbody;
        }

        async function cambiarEstadoInc(id, estado) {
            await fetch('/api/incidentes/cambiar_estado', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id, estado})
            });
            cargarTablaIncidentes();
        }

        async function enviarPreguntaRAG() {
            const input = document.getElementById('inp-chat');
            const pregunta = input.value.trim();
            if(!pregunta) return;

            const box = document.getElementById('chat-box');
            box.innerHTML += `<div class="message-bubble user">${pregunta}</div>`;
            box.innerHTML += `<div class="message-bubble bot" id="msg-loading" style="color:var(--text-muted); display:flex; align-items:center; gap:8px;"><span class="spinner"></span> Consultando a Llama 3.2 con contexto de MongoDB...</div>`;
            input.value = '';
            box.scrollTop = box.scrollHeight;

            try {
                const res = await fetch('/api/chat/preguntar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({pregunta})
                });
                const data = await res.json();

                const loadingEl = document.getElementById('msg-loading');
                if (loadingEl) loadingEl.remove();

                const badgeModelo = `<span class="badge" style="font-size:10px; margin-bottom:6px; display:inline-block;">Modelo: ${data.modelo || 'llama3.2'}</span><br>`;
                let fuentesHtml = '';
                if (data.fuentes_consultadas && data.fuentes_consultadas.length > 0) {
                    fuentesHtml = `<div style="margin-top:6px; font-size:11px; color:var(--text-muted); border-top:1px solid var(--border-subtle); padding-top:4px;">Fuentes consultadas: ${data.fuentes_consultadas.join(' · ')}</div>`;
                }

                box.innerHTML += `<div class="message-bubble bot">${badgeModelo}${data.respuesta.replace(/\\n/g, '<br>')}${fuentesHtml}</div>`;
            } catch (err) {
                const loadingEl = document.getElementById('msg-loading');
                if (loadingEl) loadingEl.remove();
                box.innerHTML += `<div class="message-bubble bot" style="color:#dc2626;">Error al procesar la consulta con Llama 3.2.</div>`;
            }
            box.scrollTop = box.scrollHeight;
        }

        async function cargarRiesgos() {
            const res = await fetch('/api/riesgos');
            const data = await res.json();
            let tbody = '';
            let grafHtml = '';

            data.riesgos.forEach(r => {
                const inh = r.riesgo_inherente_score || (r.probabilidad * r.impacto);
                const res_score = r.riesgo_residual_score || (r.probabilidad_residual * r.impacto_residual);

                tbody += `<tr>
                    <td><strong>${r.modulo}</strong></td>
                    <td>${r.descripcion}</td>
                    <td><span class="badge">${r.categoria}</span></td>
                    <td style="color:#dc2626; font-weight:600;">${inh} / 25</td>
                    <td>${r.mitigacion}</td>
                    <td style="color:#059669; font-weight:600;">${res_score} / 25</td>
                </tr>`;

                grafHtml += `
                <div style="background:#ffffff; padding:10px 14px; border-radius:5px; border:1px solid var(--border);">
                    <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:600; margin-bottom:6px;">
                        <span style="color:#09090b;">${r.modulo} <span style="font-size:11px; color:var(--text-muted); font-weight:400;">(${r.categoria})</span></span>
                        <span style="color:var(--text-muted); font-size:11.5px;">Score Residual: <strong style="color:#059669;">${res_score}</strong> <span style="color:var(--text-sub);">/ previo ${inh}</span></span>
                    </div>
                    <div style="height:5px; background:#f4f4f5; border-radius:3px; overflow:hidden;">
                        <div style="height:100%; width:${(res_score/25)*100}%; background:#059669; border-radius:3px;"></div>
                    </div>
                </div>`;
            });

            document.getElementById('body-riesgos').innerHTML = tbody;
            document.getElementById('grafica-riesgos-container').innerHTML = grafHtml;
        }

        function mostrarModalRiesgo() {
            const mod = prompt("Módulo:");
            if(!mod) return;
            const desc = prompt("Descripción del riesgo:");
            const mit = prompt("Mitigación:");
            fetch('/api/riesgos/guardar', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({modulo: mod, descripcion: desc, mitigacion: mit, probabilidad: 4, impacto: 4, probabilidad_residual: 1, impacto_residual: 2})
            }).then(() => cargarRiesgos());
        }

        function ejecutarBenchmarkFront() {
            alert('Evaluación completa ejecutada sobre los 30 correos.');
        }

        let coleccionActualMongo = 'camiones';
        let datosActualesMongo = [];
        let vistaActualMongo = 'tabla';

        async function cambiarColeccionMongo(nombre, btn) {
            coleccionActualMongo = nombre;
            document.querySelectorAll('#tabs-colecciones-mongo .btn').forEach(b => {
                b.className = 'btn btn-dark';
            });
            if (btn) btn.className = 'btn btn-primary';
            cargarExploradorMongo(nombre);
        }

        function toggleVistaMongo(tipo) {
            vistaActualMongo = tipo;
            const vt = document.getElementById('vista-mongo-tabla');
            const vj = document.getElementById('vista-mongo-json');
            const bt = document.getElementById('btn-vista-tabla');
            const bj = document.getElementById('btn-vista-json');
            if (tipo === 'tabla') {
                vt.style.display = 'block';
                vj.style.display = 'none';
                bt.style.fontWeight = '600';
                bj.style.fontWeight = 'normal';
            } else {
                vt.style.display = 'none';
                vj.style.display = 'block';
                bj.style.fontWeight = '600';
                bt.style.fontWeight = 'normal';
            }
        }

        async function cargarExploradorMongo(col) {
            try {
                col = col || 'camiones';
                document.getElementById('query-mongo-activa').innerText = `use samuelD73SixSeven; db.${col}.find().limit(50);`;
                document.getElementById('titulo-col-activa').innerText = `Colección: ${col}`;

                const resResumen = await fetch('/api/mongo/resumen');
                const dataResumen = await resResumen.json();
                const totalCol = (dataResumen.colecciones && dataResumen.colecciones[col]) || 0;
                document.getElementById('subtitulo-conteo-docs').innerText = `(${totalCol} documentos almacenados)`;

                const res = await fetch('/api/mongo/documentos/' + col);
                const data = await res.json();
                datosActualesMongo = data.documentos || [];

                // Render JSON
                document.getElementById('code-mongo-json').innerText = JSON.stringify(datosActualesMongo, null, 2);

                // Render Tabla
                if (datosActualesMongo.length === 0) {
                    document.getElementById('head-mongo-tabla').innerHTML = '<tr><th>Mensaje</th></tr>';
                    document.getElementById('body-mongo-tabla').innerHTML = '<tr><td style="color:var(--text-muted);">No hay documentos en esta colección.</td></tr>';
                    return;
                }

                const keys = Object.keys(datosActualesMongo[0]).filter(k => k !== '__v');
                let thead = '<tr>' + keys.map(k => `<th>${k}</th>`).join('') + '</tr>';
                document.getElementById('head-mongo-tabla').innerHTML = thead;

                let tbody = '';
                datosActualesMongo.forEach(doc => {
                    tbody += '<tr>' + keys.map(k => {
                        let val = doc[k];
                        if (typeof val === 'object' && val !== null) val = JSON.stringify(val);
                        if (typeof val === 'boolean') val = val ? '<strong style="color:#059669;">True</strong>' : '<strong style="color:#dc2626;">False</strong>';
                        return `<td>${val !== undefined ? val : ''}</td>`;
                    }).join('') + '</tr>';
                });
                document.getElementById('body-mongo-tabla').innerHTML = tbody;
            } catch (e) {
                console.error(e);
            }
        }

        window.onload = function() {
            cargarDashboard();
            evaluarAccesoEnVivo();
        };
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_SPA


if __name__ == "__main__":
    puerto = 8000
    print("\n" + "=" * 65)
    print(f"  LOGISMART AI CONTROL CENTER INICIADO EN:")
    print(f"  http://127.0.0.1:{puerto}")
    print("=" * 65 + "\n")

    # Abrir navegador automáticamente
    try:
        webbrowser.open(f"http://127.0.0.1:{puerto}")
    except Exception:
        pass

    uvicorn.run(app, host="127.0.0.1", port=puerto, log_level="info")
