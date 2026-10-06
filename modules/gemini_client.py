"""
Módulo para interactuar con la Gemini API.
Analiza prendas y genera prompts optimizados para IDM-VTON.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_client = None

def _get_client() -> genai.Client:
    """Inicializa y devuelve el cliente Gemini (singleton)."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no encontrada en .env")
        _client = genai.Client(api_key=api_key)
    return _client


def analizar_prenda(imagen_path: str, descripcion: str) -> dict:
    """
    Analiza una prenda usando Gemini multimodal.
    Analiza una prenda usando Gemini multimodal y devuelve la descripción en inglés.

    Args:
        imagen_path: Ruta relativa a la imagen de la prenda.
        descripcion: Descripción textual de la prenda del inventario.

    Returns:
        dict con claves: tejido, color, patron, fit, notas.
        dict con claves en inglés: fabric, color, pattern, fit, details, vton_caption.
    """
    client = _get_client()

    prompt = f"""Analiza esta prenda de ropa con detalle técnico para un sistema de virtual try-on.
Descripción de referencia: {descripcion}
    prompt = f"""You are a professional fashion AI analyst. Analyze this clothing item for an AI Virtual Try-On diffusion model.
Inventory reference description: {descripcion}

Responde en JSON con exactamente estas claves:
You MUST reply with a JSON object in ENGLISH with exactly these keys:
{{
  "tejido": "descripción del material/tejido",
  "color": "colores principales",
  "patron": "liso / rayas / flores / tweed / lentejuelas / etc.",
  "fit": "ajustado / recto / holgado / etc.",
  "notas": "detalles relevantes para superposición realista (escote, mangas, largo, etc.)"
  "fabric": "material/fabric in English (e.g. ribbed cotton, tweed wool, silk, denim, lycra)",
  "color": "main colors and shade in English",
  "pattern": "solid / striped / floral / checkered / glitter / plain",
  "fit": "slim fit / relaxed / oversized / cropped / tailored",
  "details": "key visual details like neckline, straps, buttons, zipper, hemline",
  "vton_caption": "a concise, natural 1-2 sentence English description of the garment to be used directly as diffusion prompt (e.g. 'a red metallic triangle bikini top with thin halter ties')"
}}
Responde SOLO con el JSON, sin texto adicional."""
Return ONLY the raw JSON object, without backticks or markdown formatting."""

    with open(imagen_path, "rb") as f:
        img_bytes = f.read()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(
                data=img_bytes,
                mime_type=_get_mime_type(imagen_path),
            ),
            prompt,
        ],
    )

    import json
    texto = response.text.strip().strip("```json").strip("```").strip()
    return json.loads(texto)
    texto = response.text.strip()
    if texto.startswith("```json"):
        texto = texto[7:]
    elif texto.startswith("```"):
        texto = texto[3:]
    if texto.endswith("```"):
        texto = texto[:-3]
    return json.loads(texto.strip())


def generar_prompt_vton(analisis: dict, nombre_prenda: str) -> str:
def generar_prompt_vton(analisis: dict, nombre_prenda: str = "") -> str:
    """
    Genera un prompt optimizado para IDM-VTON a partir del análisis de la prenda.
    Genera el prompt en inglés optimizado para el motor de virtual try-on.
    """
    caption = analisis.get("vton_caption", "")
    if caption:
        return caption.strip()

    Args:
        analisis: dict devuelto por analizar_prenda().
        nombre_prenda: Nombre legible de la prenda.
    parts = [
        analisis.get("color", ""),
        analisis.get("fabric", ""),
        analisis.get("fit", ""),
        analisis.get("pattern", ""),
        analisis.get("details", ""),
    ]
    cleaned = ", ".join([p for p in parts if p])
    return cleaned or "clothing garment"

    Returns:
        str con el prompt para el motor de virtual try-on.
    """
    prompt = (
        f"A person wearing a {nombre_prenda}. "
        f"Fabric: {analisis.get('tejido', '')}. "
        f"Color: {analisis.get('color', '')}. "
        f"Pattern: {analisis.get('patron', '')}. "
        f"Fit: {analisis.get('fit', '')}. "
        f"{analisis.get('notas', '')}. "
        "Photorealistic, natural lighting, high quality fashion photography."
    )
    return prompt.strip()


def _get_mime_type(path: str) -> str:
    """Devuelve el MIME type según la extensión del archivo."""
    ext = Path(path).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext, "image/jpeg")
