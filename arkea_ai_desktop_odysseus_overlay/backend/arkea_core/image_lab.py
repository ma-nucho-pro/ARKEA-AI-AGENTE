import os, json, base64, re, io
from pathlib import Path
from datetime import datetime
import requests
from backend.arkea_core.db import execute, one, rows
from backend.arkea_core.security import MAX_BINARY_RESPONSE, guarded_request, sanitize_svg
from backend.arkea_core import omniroute
from backend.arkea_core.agent_runtime import enrich_system_prompt

GENERATED = Path(os.getenv("ARKEA_DATA_DIR", "./data")) / "generated" / "images"
GENERATED.mkdir(parents=True, exist_ok=True)

def _setting(key: str, default: str = ""):
    row = one("SELECT value FROM settings WHERE key=?", (key,))
    return (row or {}).get("value") or default

def _save_bytes(data: bytes, ext: str = "png"):
    if not data or len(data) > MAX_BINARY_RESPONSE:
        raise ValueError("Imagen remota vacía o demasiado grande")
    from PIL import Image
    with Image.open(io.BytesIO(data)) as probe:
        probe.verify()
    name = f"arkea_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
    path = GENERATED / name
    path.write_bytes(data)
    return path, "/data/generated/images/" + name




def _extract_openrouter_text(data):
    try:
        return data.get('choices', [{}])[0].get('message', {}).get('content') or ''
    except Exception:
        return ''

def _save_svg_or_png_from_text(text: str, prompt: str):
    """Save model-generated SVG and rasterize it when CairoSVG is available."""
    m = re.search(r'<svg[\s\S]*?</svg>', text or '', re.I)
    if m:
        svg = sanitize_svg(m.group(0))
        svg_name = f"arkea_svg_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg"
        svg_path = GENERATED / svg_name
        svg_path.write_text(svg, encoding='utf-8')
        try:
            import cairosvg
            png_name = svg_name.replace('.svg', '.png')
            png_path = GENERATED / png_name
            cairosvg.svg2png(bytestring=svg.encode('utf-8'), write_to=str(png_path), output_width=1280, output_height=720)
            return png_path, '/data/generated/images/' + png_name
        except Exception:
            # Conservar el resultado real del modelo; no sustituirlo por una
            # tarjeta local que pueda confundirse con una generación de IA.
            return svg_path, '/data/generated/images/' + svg_name
    return None

def _try_api_connections_image(prompt: str):
    image_system = enrich_system_prompt(
        "Eres el módulo de generación visual de ARKEA AI. Sigue la skill activa.",
        "image",
    )
    effective_prompt = f"{image_system}\n\nSOLICITUD VISUAL:\n{prompt}"[:12_000]
    apis = rows("SELECT * FROM api_connections WHERE enabled=1 AND api_type IN ('image','image_generation') ORDER BY updated_at DESC, id DESC")
    engine_mode = (_setting("ai_engine_mode", "auto") or "auto").lower()
    if engine_mode in ("auto", "free") and not any((a.get("provider") or "").lower() == "omniroute" for a in apis):
        apis.insert(0, omniroute.connection_for("image_generation"))
    if engine_mode == "local":
        apis = [a for a in apis if (a.get("provider") or "").lower() in ("comfyui_local", "automatic1111_local")]
    elif engine_mode == "free":
        apis = [a for a in apis if (a.get("provider") or "").lower() == "omniroute"]
    elif engine_mode == "direct":
        apis = [a for a in apis if _is_direct_image_provider(a)]
    else:
        apis = sorted(apis, key=lambda a: 0 if (a.get("provider") or "").lower() == "omniroute" else 1)
    for api in apis:
        url=(api.get('base_url') or '').strip(); key=(api.get('api_key') or '').strip(); model=(api.get('model_id') or '').strip(); provider=(api.get('provider') or '').lower()
        if not url: continue
        try:
            headers={"Content-Type":"application/json"}
            if key: headers.update({'Authorization':f'Bearer {key}','X-API-Key':key})
            if 'openrouter' in provider or 'openrouter' in url: headers.update({'HTTP-Referer':_setting('site_url','http://127.0.0.1'),'X-Title':'ARKEA AI'})
            if ('openrouter' in provider or 'openrouter.ai' in url) and ('image' in provider or (api.get('api_type') in ('image','image_generation'))):
                payload={"model":model or 'qwen/qwen3-coder-flash',"messages":[{"role":"system","content":image_system+"\nDevuelve SOLO SVG completo 1280x720, sin markdown ni explicación."},{"role":"user","content":effective_prompt}],"max_tokens":int(json.loads(api.get('extra_json') or '{}').get('max_tokens',2800))}
                rr=guarded_request("POST",url,headers=headers,json=payload,timeout=220); rr.raise_for_status(); jd=rr.json(); text=_extract_openrouter_text(jd); saved=_save_svg_or_png_from_text(text,prompt)
                if saved: return saved
                continue
            if 'images/generations' in url or 'openai_images' in provider:
                payload={"model":model or 'gpt-image-1',"prompt":effective_prompt,"size":"1024x1024","n":1}
            elif 'stability' in provider or 'fal' in provider or 'replicate' in provider:
                payload={"model":model,"prompt":effective_prompt,"size":"1024x1024","n":1}
            else:
                payload={"model":model or 'openrouter/auto',"messages":[{"role":"system","content":image_system},{"role":"user","content":effective_prompt}],"max_tokens":1200}
            allow_local = provider in ('omniroute','comfyui_local','automatic1111_local')
            r=guarded_request("POST",url,allow_local=allow_local,headers=headers,json=payload,timeout=220); r.raise_for_status(); data=r.json(); candidates=[]
            if provider == 'omniroute':
                omniroute.remember_decision(r.headers.get('X-OmniRoute-Decision','') or f'image model={model}')
            if isinstance(data,dict):
                for keyname in ('data','images','output'):
                    if isinstance(data.get(keyname),list): candidates += data[keyname]
                if data.get('url'): candidates.append({'url':data['url']})
                if data.get('b64_json'): candidates.append({'b64_json':data['b64_json']})
            for c in candidates:
                if isinstance(c,str) and c.startswith('http'): return _save_bytes(guarded_request("GET",c,max_response_bytes=MAX_BINARY_RESPONSE,timeout=220).content,'png')
                if isinstance(c,dict):
                    if c.get('url'): return _save_bytes(guarded_request("GET",c['url'],max_response_bytes=MAX_BINARY_RESPONSE,timeout=220).content,'png')
                    if c.get('b64_json'): return _save_bytes(base64.b64decode(c['b64_json']),'png')
        except Exception:
            continue
    return None

def _is_direct_image_provider(api: dict) -> bool:
    provider = (api.get("provider") or "").strip().lower()
    base_url = (api.get("base_url") or "").strip().lower()
    if (
        provider == "omniroute"
        or provider.startswith("ollama")
        or provider.endswith("_local")
        or provider in {"comfyui", "automatic1111"}
    ):
        return False
    return not any(
        marker in base_url
        for marker in ("127.0.0.1", "localhost", "[::1]", "0.0.0.0")
    )


def _try_custom_image_api(prompt: str, *, allow_local: bool = True):
    url = _setting("image_api_url").strip()
    key = _setting("image_api_key").strip()
    model = _setting("image_api_model_id").strip()
    if not url:
        return None
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    effective_prompt = (
        enrich_system_prompt("Genera una imagen siguiendo la skill activa.", "image")
        + "\n\nSOLICITUD VISUAL:\n" + prompt
    )[:12_000]
    payload = {"prompt": effective_prompt, "size": "1280x720", "n": 1}
    if model:
        payload["model"] = model
    try:
        r = guarded_request(
            "POST", url, allow_local=allow_local,
            headers=headers, json=payload, timeout=180
        )
        r.raise_for_status()
        data = r.json()
        candidates = []
        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], list): candidates += data["data"]
            if "images" in data and isinstance(data["images"], list): candidates += data["images"]
            if "output" in data and isinstance(data["output"], list): candidates += data["output"]
            if "url" in data: candidates.append({"url": data["url"]})
            if "b64_json" in data: candidates.append({"b64_json": data["b64_json"]})
        for c in candidates:
            if isinstance(c, str) and c.startswith("http"):
                img = guarded_request("GET", c, max_response_bytes=MAX_BINARY_RESPONSE, timeout=180).content
                return _save_bytes(img, "png")
            if isinstance(c, dict):
                if c.get("url"):
                    img = guarded_request("GET", c["url"], max_response_bytes=MAX_BINARY_RESPONSE, timeout=180).content
                    return _save_bytes(img, "png")
                if c.get("b64_json"):
                    return _save_bytes(base64.b64decode(c["b64_json"]), "png")
        return None
    except Exception as e:
        name = f"api_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        p = GENERATED / name
        p.write_text(json.dumps({"error": str(e), "url": url, "model": model}, ensure_ascii=False, indent=2), encoding="utf-8")
        return None


def _try_custom_image_api_for_mode(prompt: str, engine_mode: str):
    """Keep the universal engine modes strict for image generation too."""
    if (engine_mode or "auto").strip().lower() not in {"auto", "direct"}:
        return None
    return _try_custom_image_api(
        prompt,
        allow_local=(engine_mode or "auto").strip().lower() == "auto",
    )


def generate_placeholder_image(prompt: str, project_id: int | None = None):
    engine_mode = (_setting("ai_engine_mode", "auto") or "auto").strip().lower()
    api_result = _try_api_connections_image(prompt) or _try_custom_image_api_for_mode(prompt, engine_mode)
    if api_result:
        path, url = api_result
        execute("INSERT INTO generations(project_id,generation_type,prompt,output_path,preview_path,model_used) VALUES(?,?,?,?,?,?)",
                (project_id, "image", prompt, str(path), str(path), _setting("image_api_model_id", "custom-api")))
        return {"path": str(path), "url": url, "type": "image", "provider": "custom_api"}

    if engine_mode == "free":
        return {
            "ok": False,
            "error": "OmniRoute no pudo generar la imagen. El modo Gratis es estricto y no usó una API directa ni un generador local.",
            "status": "omniroute_image_unavailable",
            "provider": "none",
        }
    if engine_mode == "direct":
        return {
            "ok": False,
            "error": "Ninguna API directa de imagen respondió. No se cambió silenciosamente a OmniRoute ni a un generador local.",
            "status": "direct_image_unavailable",
            "provider": "none",
        }

    # Fallback local gratuito: PNG real diseñado con Pillow.
    # No es difusión generativa, pero evita crear un HTML/SVG feo si no hay ComfyUI/API.
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        W, H = 1280, 720
        img = Image.new("RGB", (W, H), "#07111f")
        pix = img.load()
        for y in range(H):
            for x in range(W):
                r = int(7 + (x/W)*22 + (y/H)*9)
                g = int(17 + (x/W)*70 + (y/H)*35)
                b = int(31 + (x/W)*130 + (y/H)*45)
                pix[x,y] = (min(r,255), min(g,255), min(b,255))
        layer = Image.new("RGBA", (W,H), (0,0,0,0))
        d = ImageDraw.Draw(layer)
        d.ellipse((-160,-120,470,510), fill=(124,58,237,95))
        d.ellipse((760,260,1460,920), fill=(6,182,212,70))
        d.rounded_rectangle((110,90,1170,630), radius=48, fill=(255,255,255,32), outline=(125,211,252,180), width=3)
        d.rounded_rectangle((170,165,1110,555), radius=36, fill=(15,23,42,190), outline=(167,139,250,150), width=2)
        img = Image.alpha_composite(img.convert("RGBA"), layer)
        d = ImageDraw.Draw(img)
        def font(size, bold=False):
            for f in [
                "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            ]:
                try:
                    return ImageFont.truetype(f, size)
                except Exception:
                    pass
            return ImageFont.load_default()
        logo = "ARKEA AI"
        d.text((210,210), logo, font=font(66, True), fill=(255,255,255,255))
        raw = (prompt or "Imagen ARKEA").replace("\n"," ").strip()
        words = raw.split()
        lines, line = [], ""
        for w in words:
            if len(line + " " + w) > 48:
                lines.append(line.strip()); line = w
            else:
                line += " " + w
        if line.strip(): lines.append(line.strip())
        y = 320
        for ln in lines[:3]:
            d.text((215,y), ln, font=font(34, False), fill=(224,242,254,255))
            y += 46
        d.text((215,520), "Generado localmente por ARKEA AI · conecta ComfyUI/API para imagen IA realista", font=font(21, False), fill=(186,230,253,235))
        name = f"arkea_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = GENERATED / name
        img.convert("RGB").save(path, "PNG")
        execute("INSERT INTO generations(project_id,generation_type,prompt,output_path,preview_path,model_used) VALUES(?,?,?,?,?,?)",
                (project_id, "image", prompt, str(path), str(path), "local-pillow-design"))
        return {"path": str(path), "url": "/data/generated/images/" + name, "type": "image", "provider": "local_pillow_design"}
    except Exception:
        safe_text = prompt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:120]
        name = f"arkea_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg"
        path = GENERATED / name
        svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='1280' height='720' viewBox='0 0 1280 720'>
<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop stop-color='#7c3aed'/><stop offset='1' stop-color='#06b6d4'/></linearGradient></defs>
<rect width='1280' height='720' fill='#050b18'/><rect x='90' y='80' width='1100' height='560' rx='44' fill='url(#g)' opacity='.92'/>
<text x='640' y='300' font-family='Arial' font-size='58' font-weight='900' text-anchor='middle' fill='white'>ARKEA AI</text>
<text x='640' y='380' font-family='Arial' font-size='30' text-anchor='middle' fill='white'>{safe_text}</text></svg>"""
        path.write_text(svg, encoding="utf-8")
        return {"path": str(path), "url": "/data/generated/images/" + name, "type": "image", "provider": "local_svg"}


def edit_region_placeholder(original_path: str, mask_path: str, prompt: str, project_id: int | None = None):
    name = f"arkea_edit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = GENERATED / name
    path.write_text(json.dumps({"original": original_path, "mask": mask_path, "prompt": prompt, "note": "Pendiente conectar API de inpainting/ComfyUI."}, indent=2, ensure_ascii=False), encoding="utf-8")
    execute("INSERT INTO image_edits(project_id,original_image_path,mask_path,result_image_path,edit_prompt) VALUES(?,?,?,?,?)",
            (project_id, original_path, mask_path, str(path), prompt))
    return {"path": str(path), "message": "Edición parcial registrada. Conecta ComfyUI/API de inpainting para cambiar solo la zona seleccionada."}


def generate_local_svg_image(prompt: str, project_id: int | None = None):
    """Imagen local gratis sin modelo pesado: genera SVG editable si no hay API/ComfyUI."""
    name = f"arkea_svg_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg"
    path = GENERATED / name
    safe = (prompt or "Imagen ARKEA").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")[:120]
    svg = "<svg xmlns='http://www.w3.org/2000/svg' width='1280' height='720' viewBox='0 0 1280 720'>" \
          "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop stop-color='#7c3aed'/><stop offset='1' stop-color='#06b6d4'/></linearGradient>" \
          "<filter id='blur'><feGaussianBlur stdDeviation='18'/></filter></defs>" \
          "<rect width='1280' height='720' fill='#07111f'/>" \
          "<circle cx='250' cy='180' r='180' fill='#7c3aed' opacity='.35' filter='url(#blur)'/>" \
          "<circle cx='980' cy='520' r='230' fill='#06b6d4' opacity='.28' filter='url(#blur)'/>" \
          "<rect x='110' y='95' width='1060' height='530' rx='42' fill='url(#g)' opacity='.22' stroke='#7dd3fc' stroke-width='3'/>" \
          "<text x='140' y='180' font-family='Segoe UI,Arial' font-size='52' fill='#e5f6ff' font-weight='800'>ARKEA AI</text>" \
          f"<text x='140' y='265' font-family='Segoe UI,Arial' font-size='34' fill='#ffffff'>{safe}</text>" \
          "<text x='140' y='330' font-family='Segoe UI,Arial' font-size='22' fill='#bae6fd'>Imagen local editable generada sin API. Para imagen realista conecta ComfyUI/Stable Diffusion o una API.</text>" \
          "</svg>"
    path.write_text(svg, encoding="utf-8")
    try:
        execute("INSERT INTO generations(project_id,generation_type,prompt,output_path,preview_path,model_used) VALUES(?,?,?,?,?,?)",
                (project_id, "image-svg", prompt, str(path), str(path), "local-svg"))
    except Exception:
        pass
    return {"path": str(path), "url": "/data/generated/images/" + name, "svg": svg, "model": "local-svg"}
