# ARKEA AI Agent Core - by: Arkeai AI Roberto Manuel Jara Peche
# Copyright (C) 2026 Roberto Manuel Jara Peche. Licensed under AGPL-3.0-or-later.
from pathlib import Path
import urllib.parse
from html import escape
from backend.arkea_core.workspace import create_project, write_project_file, set_preview
from backend.arkea_core.skills import create_skill_from_prompt
from backend.arkea_core.memory import save_memory
from backend.arkea_core.image_lab import generate_placeholder_image, generate_local_svg_image
from backend.arkea_core.docs import create_pptx, create_docx, create_xlsx, convert_to_pdf_with_libreoffice
from backend.arkea_core.research import research_query, scihub_blocked
from backend.arkea_core.ollama import chat_local, get_selected_models
from backend.arkea_core.model_router import route_text, route_html, ARKEA_AGENT_SYSTEM
from backend.arkea_core.conversations import get_or_create_active, save_message

VISUAL_CSS = """
<style>
body{margin:0;background:#07111f;color:#e5f1ff;font-family:Inter,Arial,sans-serif;padding:40px}
.card{background:linear-gradient(135deg,#121c34,#0a2635);border:1px solid #27405f;border-radius:24px;padding:24px;margin:16px 0;box-shadow:0 20px 60px #0006}
h1{font-size:44px;margin:0 0 12px;background:linear-gradient(90deg,#a78bfa,#22d3ee);-webkit-background-clip:text;color:transparent}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.pill{background:#101a2f;border:1px solid #31506f;border-radius:999px;padding:10px 14px;display:inline-block;margin:6px}
</style>
"""

def visual_html(title: str, body: str):
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>{VISUAL_CSS}</head><body>
<h1>{title}</h1>
<div class='card'>{body}</div>
</body></html>"""



def quick_visual_response(message: str, answer: str):
    safe_q = escape(message)
    safe_a = escape(answer)
    points = [p.strip(' -•') for p in answer.replace('\n', '. ').split('.') if p.strip()][:6]
    if not points:
        points = [answer[:180] or 'Respuesta generada por ARKEA AI']
    cards = ''.join(f"<div class='vcard'><span>{i+1}</span><p>{escape(pt)}</p></div>" for i, pt in enumerate(points[:4]))
    map_nodes = ''.join(f"<div class='node n{i}'>{escape(pt[:42])}</div>" for i, pt in enumerate(points[:5]))
    body = f"""
    <section class='hero'><h2>Respuesta visual</h2><p><b>Pregunta:</b> {safe_q}</p></section>
    <section class='visual-grid'>
      <div class='panel'><h3>Idea central</h3><p>{safe_a}</p></div>
      <div class='panel'><h3>Mapa semántico</h3><div class='map'><div class='center'>Tema</div>{map_nodes}</div></div>
      <div class='panel'><h3>Cuadro rápido</h3><div class='cards'>{cards}</div></div>
      <div class='panel'><h3>Ruta sugerida</h3><div class='timeline'><b>1</b><span>Comprender</span><b>2</b><span>Comparar</span><b>3</b><span>Aplicar</span></div></div>
    </section>
    <style>
    .hero{{padding:22px;border-radius:22px;background:linear-gradient(135deg,#064e3b,#0f766e);color:white;margin-bottom:18px}}
    .visual-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}}
    .panel{{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.16);border-radius:20px;padding:18px;box-shadow:0 18px 50px #0004}}
    .cards{{display:grid;gap:10px}}.vcard{{display:flex;gap:10px;align-items:flex-start;padding:12px;border-radius:14px;background:#ecfdf5;color:#064e3b}}.vcard span{{background:#10b981;color:white;border-radius:50%;width:26px;height:26px;display:grid;place-items:center;font-weight:bold;flex:0 0 auto}}
    .map{{position:relative;min-height:250px;border-radius:18px;background:radial-gradient(circle at center,#dcfce7,#f8fafc);overflow:hidden;color:#064e3b}}
    .center,.node{{position:absolute;padding:9px 12px;border-radius:999px;background:white;border:1px solid #86efac;box-shadow:0 8px 24px #0002;font-size:12px}}
    .center{{left:50%;top:50%;transform:translate(-50%,-50%);background:#10b981;color:white;font-weight:bold}}
    .n0{{left:8%;top:12%}}.n1{{right:8%;top:16%}}.n2{{left:10%;bottom:18%}}.n3{{right:8%;bottom:16%}}.n4{{left:35%;top:8%}}
    .timeline{{display:grid;grid-template-columns:auto 1fr;gap:12px;align-items:center}}.timeline b{{background:#10b981;color:white;border-radius:50%;width:32px;height:32px;display:grid;place-items:center}}
    </style>
    """
    return {"say": answer, "html_content": visual_html("Explicación visual ARKEA", body)}

def _preview_url(path: str, project_id: int | None = None):
    if project_id is not None:
        return f"/api/arkea/projects/{project_id}/preview"
    p = Path(path)
    return f"/data/projects/{p.parent.name}/{p.name}"


def _file_download_url(path: str):
    return "/api/arkea/files/download?path=" + urllib.parse.quote(str(path))

def _conversation_output_dir(conversation_id: int | None):
    if not conversation_id:
        return None
    try:
        from backend.arkea_core.conversations import one
        c = one('SELECT folder_path FROM conversations WHERE id=?', (conversation_id,))
        if c and c.get('folder_path'):
            out = Path(c['folder_path'])
            out.mkdir(parents=True, exist_ok=True)
            return str(out)
    except Exception:
        return None
    return None


CONTEXT_MARKER = "[CONTEXTO DE ARCHIVOS SUBIDOS PARA USAR EN LA RESPUESTA]"

def _split_user_context(message: str):
    if CONTEXT_MARKER in message:
        primary, ctx = message.split(CONTEXT_MARKER, 1)
        return primary.strip(), ctx.strip()
    return message.strip(), ""

def _context_text(ctx: str, max_chars: int = 4500):
    if not ctx:
        return ""
    try:
        import json
        arr = json.loads(ctx)
        parts = []
        if isinstance(arr, list):
            for item in arr[-5:]:
                fn = item.get("archivo") or item.get("filename") or "archivo"
                tipo = item.get("tipo") or item.get("kind") or ""
                texto = (item.get("texto") or item.get("extracted_text") or "").strip()
                vision = (item.get("vision") or "").strip()
                block = f"Archivo: {fn} ({tipo})"
                if vision:
                    block += f"\nDescripción visual: {vision}"
                if texto:
                    block += f"\nContenido extraído:\n{texto[:2500]}"
                parts.append(block)
        return "\n\n".join(parts)[:max_chars]
    except Exception:
        return ctx[:max_chars]

def _needs_image_generation(low: str):
    verbs = ["crea", "crear", "genera", "generar", "haz", "hacer", "dibuja", "diseña", "diseñar"]
    nouns = ["imagen", "foto", "arte", "ilustración", "ilustracion", "logo", "miniatura", "thumbnail", "png", "jpg", "jpeg", "fondo", "wallpaper", "portada"]
    return any(v in low for v in verbs) and any(n in low for n in nouns)


def create_html_project(message: str, project_type: str = "html"):
    project = create_project(message[:70] or "Proyecto ARKEA", project_type)
    try:
        html = route_html(message)
    except Exception:
        html = visual_html("Proyecto creado por ARKEA", f"<p>{escape(message)}</p><p>Este archivo puede editarse por voz o texto y se actualiza en el visualizador.</p>")
    path = write_project_file(project["id"], "index.html", html, "html")
    set_preview(project["id"], path)
    return {"say": "Listo. Creé el HTML funcional y lo abrí en vista previa.", "project": project, "preview": path, "preview_url": _preview_url(path, project["id"]), "folder_path": project.get("folder_path")}

def create_game_project(message: str):
    project = create_project((message[:70] or "Juego HTML ARKEA"), "game")
    try:
        html = route_html("Crea un juego completamente nuevo y original desde cero. No uses plantilla prefabricada. Debe ser jugable, con HTML, CSS y JavaScript internos. Pedido exacto: " + message)
    except Exception:
        html = visual_html("Juego ARKEA", "<p>No pude usar el modelo externo. Configura una API de código/artefacto en Ajustes > APIS para crear juegos originales.</p>")
    path = write_project_file(project["id"], "index.html", html, "html")
    set_preview(project["id"], path)
    return {"say": "Listo. Creé un juego original con código y lo abrí en vista previa.", "project": project, "preview": path, "preview_url": _preview_url(path, project["id"]), "html_content": html, "folder_path": project.get("folder_path")}

def _doc_preview_html(title, path, kind, msg):
    safe_title = escape(title)
    safe_msg = escape(msg)
    safe_path = escape(path)
    ext = Path(path).suffix.lower().replace('.', '').upper() or kind
    app_name = 'Word' if 'doc' in ext.lower() else 'Excel' if 'xls' in ext.lower() else 'PowerPoint' if 'ppt' in ext.lower() else kind
    if app_name == 'Word':
        inner = f"""<div class='paper'><h1>{safe_title}</h1><p>{safe_msg}</p><h2>Documento editable</h2><p>ARKEA redactó este archivo con estructura profesional. Abre la carpeta para editarlo con Microsoft Word u Office compatible.</p><div class='box'>{safe_path}</div></div>"""
    elif app_name == 'Excel':
        inner = f"""<table class='sheet'><tr><th>Hoja</th><th>Estado</th><th>Diseño</th></tr><tr><td>Resumen</td><td>Creada</td><td>ARKEA</td></tr><tr><td>Plan</td><td>Creada</td><td>Con formato</td></tr><tr><td>Indicadores</td><td>Creada</td><td>Editable</td></tr></table><div class='box'>{safe_path}</div>"""
    else:
        inner = f"""<div class='slide'><h1>{safe_title}</h1><p>{safe_msg}</p></div><div class='box'>{safe_path}</div>"""
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
body{{margin:0;background:#0b1411;color:#0f172a;font-family:Segoe UI,Arial;padding:24px}}.office{{max-width:980px;margin:auto;background:#f8fafc;border-radius:20px;box-shadow:0 24px 80px rgba(0,0,0,.32);overflow:hidden}}.ribbon{{height:54px;background:linear-gradient(90deg,#0f6b45,#16a34a);color:#fff;display:flex;align-items:center;gap:22px;padding:0 20px}}.ribbon b{{font-size:18px}}.ribbon span{{opacity:.85}}.paper{{width:min(760px,92%);min-height:720px;margin:28px auto;background:#fff;padding:58px;box-shadow:0 8px 26px rgba(15,23,42,.18);border:1px solid #e2e8f0}}h1{{font-size:30px;color:#0f172a}}h2{{color:#166534}}.box{{margin:20px;padding:14px;border-radius:14px;background:#ecfdf5;border:1px solid #bbf7d0;color:#14532d;word-break:break-all}}.sheet{{width:92%;margin:32px auto;border-collapse:collapse;background:#fff}}.sheet th{{background:#16a34a;color:white}}.sheet th,.sheet td{{border:1px solid #dbe4f0;padding:14px;text-align:left}}.slide{{margin:34px auto;width:82%;aspect-ratio:16/9;background:linear-gradient(135deg,#0f6b45,#38bdf8);border-radius:20px;color:#fff;padding:48px;display:flex;flex-direction:column;justify-content:center}}
</style></head><body><div class='office'><div class='ribbon'><b>{app_name}</b><span>Inicio</span><span>Insertar</span><span>Diseño</span><span>Vista</span></div>{inner}</div></body></html>"""



def _office_live_preview_html(title, path, kind, msg, paragraphs=None, rows=None, slides=None, pdf_url=''):
    safe_title = escape(title or 'Archivo ARKEA')
    safe_msg = escape(msg or '')
    safe_path = escape(path or '')
    kind = (kind or '').upper()
    if kind == 'DOCX':
        body = ''.join(f"<p>{escape(p)}</p>" for p in (paragraphs or [])[:28]) or f"<p>{safe_msg}</p>"
        extra = "<div class='lo-note'>Vista tipo LibreOffice Writer. Si LibreOffice está instalado, ARKEA también crea/usa PDF de previsualización.</div>"
        doc = f"<div class='writer-page'><h1>{safe_title}</h1>{body}</div>"
    elif kind == 'XLSX':
        rws = rows or []
        table = '<table class="sheet">' + ''.join('<tr>' + ''.join(f'<td>{escape(str(c))}</td>' for c in row) + '</tr>' for row in rws[:20]) + '</table>'
        extra = "<div class='lo-note'>Vista tipo LibreOffice Calc con hojas reales en el archivo XLSX.</div>"
        doc = table
    else:
        ss = slides or []
        doc = ''.join(f"<div class='slide-preview'><h2>{escape(s.get('title','Diapositiva'))}</h2><p>{escape(s.get('body',''))}</p></div>" for s in ss[:8]) or f"<p>{safe_msg}</p>"
        extra = "<div class='lo-note'>Vista tipo LibreOffice Impress / PowerPoint editable.</div>"
    pdf_link = f"<a class='pdf' href='{escape(pdf_url)}'>Abrir vista PDF generada con LibreOffice</a>" if pdf_url else "<span class='pdf disabled'>PDF LibreOffice no disponible; usando vista HTML fiel.</span>"
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
html,body{{margin:0;background:#0b1411;color:#172033;font-family:'Segoe UI',Arial,sans-serif;}}
.office-live{{min-height:100vh;padding:22px;background:linear-gradient(135deg,#e8fff1,#f8fafc)}}
.ribbon{{height:54px;background:linear-gradient(90deg,#0b6b46,#10b981);color:#fff;border-radius:18px 18px 0 0;display:flex;align-items:center;gap:20px;padding:0 20px;box-shadow:0 12px 34px #0002}}
.ribbon b{{font-size:18px}}.ribbon span{{opacity:.86}}.lo-note{{background:#dcfce7;border:1px solid #86efac;color:#14532d;border-radius:14px;padding:10px 14px;margin:16px auto;max-width:840px}}
.writer-page{{width:min(820px,92%);min-height:900px;margin:18px auto;background:white;padding:62px;box-shadow:0 16px 60px #0003;border:1px solid #e2e8f0;line-height:1.7}}
.writer-page h1{{text-align:center;color:#0f5132;margin-top:0}}.writer-page p{{font-size:15px;color:#1f2937;text-align:justify}}
.sheet{{width:min(980px,96%);margin:24px auto;border-collapse:collapse;background:white;box-shadow:0 14px 50px #0002}}.sheet td{{border:1px solid #cbd5e1;padding:12px}}.sheet tr:first-child td{{background:#10b981;color:white;font-weight:bold}}
.slide-preview{{width:min(920px,92%);aspect-ratio:16/9;margin:24px auto;border-radius:22px;background:linear-gradient(135deg,#064e3b,#22c55e);color:white;padding:48px;box-shadow:0 16px 50px #0003}}.slide-preview h2{{font-size:34px}}
.filebar{{max-width:980px;margin:0 auto 16px;display:flex;gap:10px;align-items:center;justify-content:space-between;color:#14532d}}.path{{font-size:12px;word-break:break-all;opacity:.75}}.pdf{{color:#047857;font-weight:700}}.disabled{{opacity:.7}}
@keyframes pulse{{0%{{opacity:.6}}50%{{opacity:1}}100%{{opacity:.6}}}}.thinking{{animation:pulse 1s infinite}}
</style></head><body><div class='office-live'><div class='ribbon'><b>LibreOffice / Office Preview</b><span>Inicio</span><span>Insertar</span><span>Diseño</span><span>Vista</span><span class='thinking'>creando en vivo...</span></div><div class='filebar'><div><b>{kind}</b><div class='path'>{safe_path}</div></div>{pdf_link}</div>{extra}{doc}</div></body></html>"""
def _topic_from_prompt(message: str):
    t = message.strip()
    t = t.replace("créame", "").replace("creame", "").replace("crea", "").replace("hazme", "").replace("haz", "")
    t = t.replace("un word", "").replace("una word", "").replace("un documento", "").replace("un power point", "").replace("powerpoint", "").replace("presentación", "").replace("presentacion", "").replace("excel", "")
    return t.strip(" :.-")[:90] or "contenido solicitado"

def _smart_sections(topic: str):
    return [
        f"Este material desarrolla el tema: {topic}.",
        "Se organiza con una estructura clara, visual y editable para que el usuario pueda modificarlo desde ARKEA AI.",
        "Incluye una propuesta inicial con apartados, ideas clave y una ruta de mejora para ampliarlo con más datos, imágenes o referencias.",
        "El diseño usa la identidad ARKEA AI: azul, cian, violeta y estilo moderno tipo Aero/Liquid Glass."
    ]

def _smart_rows(topic: str):
    return [
        ["Sección", "Contenido", "Estado"],
        ["Tema", topic, "Definido"],
        ["Objetivo", "Organizar información de forma clara y útil", "Listo"],
        ["Datos principales", "Agregar o editar datos según necesidad", "Editable"],
        ["Indicadores", "Puede incluir porcentajes, cantidades o avances", "Pendiente"],
        ["Acción siguiente", "Pedir a ARKEA agregar fórmulas, gráficos o más hojas", "Sugerido"],
    ]

def _smart_slides(topic: str):
    return [
        {"title":"Presentación", "body": topic},
        {"title":"Propósito", "body":"Explicar el tema de manera visual, breve y ordenada."},
        {"title":"Ideas clave", "body":"• Concepto principal\n• Elementos importantes\n• Aplicación práctica\n• Beneficio esperado"},
        {"title":"Desarrollo", "body": "Contenido editable generado por ARKEA AI. Puedes pedirme agregar imágenes, gráficos, ejemplos o más diapositivas."},
        {"title":"Cierre", "body":"Conclusión visual y llamada a la acción. ARKEA AI puede convertirlo en una versión académica, comercial o educativa."},
    ]

def create_word_from_prompt(message: str, file_context: str = "", output_dir: str | None = None):
    primary, ctx = _split_user_context(message)
    if file_context:
        ctx = file_context
    context_summary = _context_text(ctx)
    topic = _topic_from_prompt(primary)
    title = "ARKEA · " + topic[:55].title()
    try:
        long_doc = any(k in primary.lower() for k in ["amplio", "extenso", "largo", "gigante", "muy largo", "completo", "todo completo", "detallado"])
        target = "18 a 30 párrafos amplios, con subtítulos escritos como líneas independientes" if long_doc else "8 a 12 párrafos claros con subtítulos escritos como líneas independientes"
        prompt = "Redacta un documento Word profesional, humano, amplio y estructurado. Devuelve " + target + ". No uses markdown, no uses JSON. Tema: " + primary
        if context_summary:
            prompt += "\nUsa este contexto de archivos:\n" + context_summary[:5000]
        generated = route_text(prompt, task="document", system=ARKEA_AGENT_SYSTEM + "\nRedacta contenido para un documento Word editable, con lenguaje claro y profesional.")
        paragraphs = [p.strip() for p in generated.split("\n") if p.strip()]
        if len(paragraphs) < 3:
            paragraphs = _smart_sections(topic)
    except Exception:
        paragraphs = _smart_sections(topic)
    if context_summary and not any('archivo' in p.lower() for p in paragraphs[:3]):
        paragraphs.insert(1, "Contenido base tomado de los archivos subidos:\n" + context_summary[:3800])
    tables = [[["Apartado", "Detalle"], ["Tema", topic], ["Archivos usados", "Sí" if context_summary else "No"], ["Formato", "Word editable"], ["Diseño", "Logo ARKEA, colores, cuadros y estructura profesional"]]]
    path = create_docx(title, paragraphs, tables=tables, output_dir=output_dir)
    pdf_path = convert_to_pdf_with_libreoffice(path)
    pdf_url = _file_download_url(pdf_path) if pdf_path else ""
    html = _office_live_preview_html("Word creado con diseño ARKEA", path, "DOCX", "Se generó un documento Word editable usando la instrucción real del usuario y los archivos subidos como contexto.", paragraphs=paragraphs, pdf_url=pdf_url)
    return {"say": "Listo. Creé el documento Word en la carpeta del chat y lo dejé visible en la vista previa.", "file": path, "folder_path": str(Path(path).parent), "download_url": _file_download_url(path), "pdf_preview_url": pdf_url, "html_content": html, "title": title}

def create_excel_from_prompt(message: str, file_context: str = "", output_dir: str | None = None):
    primary, ctx = _split_user_context(message)
    if file_context:
        ctx = file_context
    context_summary = _context_text(ctx)
    topic = _topic_from_prompt(primary)
    title = "ARKEA · " + topic[:45].title()
    rows = _smart_rows(topic)
    if context_summary:
        rows.append(["Contexto de archivos", context_summary[:1200], "Usado"])
    sheets = [
        {"name":"Resumen", "rows": rows},
        {"name":"Plan", "rows":[["Actividad","Responsable","Estado"],["Revisar datos","Usuario","Pendiente"],["Agregar fórmulas","ARKEA AI","Sugerido"],["Crear gráficos","ARKEA AI","Sugerido"]]},
        {"name":"Indicadores", "rows":[["Indicador","Valor","Observación"],["Avance","0%","Editable"],["Prioridad","Alta","Según solicitud"],["Calidad visual","ARKEA","Aplicada"]]},
    ]
    path = create_xlsx(title, rows, sheets=sheets, output_dir=output_dir)
    pdf_path = convert_to_pdf_with_libreoffice(path)
    pdf_url = _file_download_url(pdf_path) if pdf_path else ""
    html = _office_live_preview_html("Excel creado con diseño ARKEA", path, "XLSX", "Se generó un Excel editable con hojas, estilos, colores, filtros y logo.", rows=rows, pdf_url=pdf_url)
    return {"say": "Listo. Creé el Excel en la carpeta del chat con hojas, colores, filtros y diseño ARKEA.", "file": path, "folder_path": str(Path(path).parent), "download_url": _file_download_url(path), "pdf_preview_url": pdf_url, "html_content": html}

def create_ppt_from_prompt(message: str, file_context: str = "", output_dir: str | None = None):
    primary, ctx = _split_user_context(message)
    if file_context:
        ctx = file_context
    context_summary = _context_text(ctx)
    topic = _topic_from_prompt(primary)
    slides = _smart_slides(topic)
    if context_summary:
        slides.insert(2, {"title":"Contenido de archivos subidos", "body": context_summary[:900]})
    path = create_pptx("ARKEA · " + topic[:55].title(), slides, output_dir=output_dir)
    pdf_path = convert_to_pdf_with_libreoffice(path)
    pdf_url = _file_download_url(pdf_path) if pdf_path else ""
    html = _office_live_preview_html("PowerPoint creado con diseño ARKEA", path, "PPTX", "Se generó una presentación editable con logo ARKEA, colores modernos y estructura visual.", slides=slides, pdf_url=pdf_url)
    return {"say": "Listo. Creé la presentación PowerPoint en la carpeta del chat con logo ARKEA, colores y diseño visual.", "file": path, "folder_path": str(Path(path).parent), "download_url": _file_download_url(path), "pdf_preview_url": pdf_url, "html_content": html}


def create_simulator_project(message: str):
    project = create_project(_topic_from_prompt(message)[:70] or "Simulador ARKEA", "html")
    try:
        html = route_html("Crea un simulador interactivo original y completo. No uses plantilla prefabricada. Pedido: " + message)
    except Exception:
        html = visual_html("Simulador ARKEA", "<p>No pude usar el modelo externo. Configura una API en Ajustes > APIS para crear simuladores completos.</p>")
    path = write_project_file(project["id"], "index.html", html, "html")
    set_preview(project["id"], path)
    return {"say": "Listo. Creé el simulador con código y lo abrí en vista previa.", "project": project, "preview": path, "preview_url": _preview_url(path, project["id"]), "html_content": html, "folder_path": project.get("folder_path")}



def create_image_from_prompt(message: str):
    project = create_project("Imagen ARKEA", "image")
    img = generate_placeholder_image(message, project["id"])
    if not img or not img.get("url"):
        img = generate_local_svg_image(message, project["id"])
    return {"say": "Listo. Generé una imagen PNG/JPG o visual. Si conectas una API de imagen, usaré esa API para imagen realista y edición.", "project": project, "image": img, "preview_url": img.get("url"), "folder_path": project.get("folder_path"), "download_url": img.get("url"), "file": img.get("path")}

def create_calculator_project(message: str):
    project = create_project((message[:70] or "Calculadora ARKEA"), "html")
    try:
        html = route_html("Crea una calculadora original desde cero, moderna, responsive y funcional. No uses plantilla prefabricada. Pedido exacto: " + message)
    except Exception:
        html = visual_html("Calculadora ARKEA", "<p>No pude usar el modelo externo. Configura una API de código/artefacto en Ajustes > APIS para crear calculadoras originales.</p>")
    path = write_project_file(project["id"], "index.html", html, "html")
    set_preview(project["id"], path)
    return {"say": "Listo. Creé una calculadora original y la abrí en vista previa.", "project": project, "preview": path, "preview_url": _preview_url(path, project["id"]), "html_content": html, "folder_path": project.get("folder_path")}

def organize_current_folder(message: str, conversation_id: int):
    from backend.arkea_core.conversations import one
    import shutil
    c = one('SELECT folder_path FROM conversations WHERE id=?', (conversation_id,))
    if not c or not c.get('folder_path'):
        return {"say": "No encontré carpeta activa del chat."}
    folder = Path(c["folder_path"])
    if not folder.exists():
        return {"say": "La carpeta activa no existe todavía."}
    groups = {
        "imagenes": [".png",".jpg",".jpeg",".webp",".gif",".bmp",".svg"],
        "documentos": [".pdf",".doc",".docx",".txt",".md"],
        "hojas_excel": [".xls",".xlsx",".csv"],
        "presentaciones": [".ppt",".pptx"],
        "videos": [".mp4",".mov",".webm",".avi",".mkv"],
        "audios": [".mp3",".wav",".m4a",".ogg"],
        "codigo": [".html",".css",".js",".ts",".py",".json",".sql",".cs",".java"],
        "comprimidos": [".zip",".rar",".7z"],
    }
    moved = []
    for item in folder.iterdir():
        if item.is_dir() or item.name.startswith("ARKEA_"):
            continue
        ext = item.suffix.lower()
        target_group = "otros"
        for g, exts in groups.items():
            if ext in exts:
                target_group = g
                break
        target_dir = folder / target_group
        target_dir.mkdir(exist_ok=True)
        target = target_dir / item.name
        if target.exists():
            target = target_dir / f"{item.stem}_arkea{item.suffix}"
        shutil.move(str(item), str(target))
        moved.append(f"{item.name} → {target_group}/")
    report = folder / "ARKEA_ORGANIZACION.md"
    report.write_text("# Organización ARKEA\n\n" + "\n".join(f"- {x}" for x in moved), encoding="utf-8")
    return {"say": f"Organicé la carpeta activa del chat. Moví {len(moved)} archivos.", "file": str(report)}


def handle_message(message: str, project_id: int | None = None, skill_id: str | None = None, mode: str = "auto", conversation_id: int | None = None):
    # Regla principal: clasificar SOLO la instrucción del usuario.
    # Nunca usar nombres o texto de archivos subidos para decidir acción, porque eso causaba miniaturas falsas.
    primary_message, file_ctx = _split_user_context(message)
    title_hint = (primary_message[:40] or "Nuevo chat")
    conv = {"id": conversation_id} if conversation_id else get_or_create_active(title_hint)
    conversation_id = conv["id"]
    save_message(conversation_id, "user", primary_message)

    def done(payload: dict):
        payload["conversation_id"] = conversation_id
        save_message(conversation_id, "assistant", payload.get("say", ""), payload.get("model_used", ""))
        return payload

    low = primary_message.lower().strip()

    # 1) Acciones explícitas de archivos/documentos tienen prioridad máxima.
    if 'imagen' in low and any(k in low for k in ['editar','edita','mejora','variacion','variación']) and file_ctx:
        return done({'say':'Puedo preparar la edición, pero la edición real por zona requiere una API de imagen/inpainting conectada en Ajustes > APIS. Conecta Stability, ComfyUI, Replicate, FAL o una API compatible y la usaré.'})
    out_dir = _conversation_output_dir(conversation_id)
    if "word" in low or "docx" in low or "documento" in low or "informe en word" in low:
        return done(create_word_from_prompt(primary_message, file_ctx, output_dir=out_dir))
    if "excel" in low or "xlsx" in low or "hoja de cálculo" in low or "hoja de calculo" in low:
        return done(create_excel_from_prompt(primary_message, file_ctx, output_dir=out_dir))
    if "powerpoint" in low or "ppt" in low or "diapositiva" in low or "presentación" in low or "presentacion" in low:
        return done(create_ppt_from_prompt(primary_message, file_ctx, output_dir=out_dir))

    # 2) Automatización / organización segura.
    if ("organiza" in low or "ordenar" in low or "ordena" in low) and ("carpeta" in low or "descarga" in low or "archivos" in low):
        return done(organize_current_folder(primary_message, conversation_id))

    if "sci-hub" in low or "scihub" in low:
        return done({"say": "No puedo integrar Sci-Hub. Activé el módulo de investigación legal con OpenAlex, Crossref, arXiv, repositorios y open access.", "data": scihub_blocked()})
    if "create skill" in low or "crear skill" in low:
        skill = create_skill_from_prompt(primary_message)
        save_memory("skill", f"Skill creada: {skill['name']}", title=skill["name"], scope_id=skill["id"], source="skill_creator")
        return done({"say": f"Skill creada: {skill['name']}. Ya está instalada en data/skills/{skill['id']}", "skill": skill})

    # 3) Proyectos interactivos.
    if "calculadora" in low or "calculator" in low:
        return done(create_calculator_project(primary_message))
    if "simulador" in low or "simula" in low or "simulación" in low or "simulacion" in low:
        return done(create_simulator_project(primary_message))
    if "juego" in low or "game" in low:
        return done(create_game_project(primary_message))
    explicit_html_request = any(k in low for k in ["crea una página web", "crea una pagina web", "haz una página web", "haz una pagina web", "landing page", "crea html", "crea un html", "hacer html", "crea una web", "crea una app", "crea interfaz", "crea una interfaz"]) or low.startswith("html:")
    if explicit_html_request:
        return done(create_html_project(primary_message, "html"))
    if any(v in low for v in ["crea", "crear", "haz", "hacer", "genera", "generar", "desarrolla"]) and not any(x in low for x in ["imagen", "foto", "word", "excel", "ppt", "powerpoint", "diapositiva"]):
        return done(create_html_project(primary_message, "html"))

    # 4) Imagen solo si el usuario pide GENERAR/DIBUJAR/DISEÑAR imagen.
    if _needs_image_generation(low):
        return done(create_image_from_prompt(primary_message))
    if ("miniatura" in low or "thumbnail" in low) and any(v in low for v in ["crea", "crear", "haz", "genera", "diseña"]):
        project = create_project("Miniatura YouTube", "image")
        img = generate_placeholder_image(primary_message, project["id"])
        return done({"say": "Listo. Creé una miniatura como imagen PNG local. Para IA realista conecta ComfyUI/API de imagen.", "project": project, "image": img, "preview_url": img["url"], "folder_path": project.get("folder_path")})

    # 5) Internet / agente de búsqueda con API web si está configurada.
    if any(k in low for k in ["internet", "busca", "buscar", "mejores hoteles", "mejor hotel", "hoteles", "compara precios", "web"]):
        answer = route_text(primary_message, task="web", system=ARKEA_AGENT_SYSTEM + "\nUsa búsqueda web si el proveedor la permite. Compara opciones y recomienda una mejor alternativa con criterios claros.")
        return done(quick_visual_response(primary_message, answer))

    # 6) Investigación.
    if "tesis" in low or "investiga" in low or "investigación" in low:
        result = research_query(primary_message, 5)
        project = create_project("Investigación de tesis", "research")
        html = visual_html("Investigación para tesis", "<p>Fuentes legales consultadas: OpenAlex y Crossref.</p><pre>" + str(result)[:3000] + "</pre>")
        path = write_project_file(project["id"], "informe_investigacion.html", html, "html")
        set_preview(project["id"], path)
        return done({"say": "Hice una búsqueda académica legal inicial y creé un informe visual para tesis.", "project": project, "research": result, "preview": path, "preview_url": _preview_url(path, project["id"])})

    # 6) Chat normal con contexto de archivos si existe.
    context = _context_text(file_ctx)
    llm_msg = primary_message
    if context:
        llm_msg += "\n\nUsa este contexto de archivos subidos para responder:\n" + context
    answer = route_text(llm_msg, task="chat", system=ARKEA_AGENT_SYSTEM)
    return done(quick_visual_response(primary_message, answer))

