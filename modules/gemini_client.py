"""
Cliente para la API de Google Gemini en el Probador Virtual.
Realiza el análisis multimodal de prendas y la traducción/generación de prompts VTON.
"""
import base64
import os
from pathlib import Path
from google import genai
from google.genai import types

def _get_client() -> genai.Client:
    """Inicializa el cliente de Gemini usando la clave API del entorno o de Streamlit Secrets."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            pass
            
    if not api_key:
        raise ValueError("No se encontró GEMINI_API_KEY en las variables de entorno ni en st.secrets.")
        
    return genai.Client(api_key=api_key)


def _get_mime_type(path: str) -> str:
    """Devuelve el MIME type según la extensión del archivo."""
    ext = Path(path).suffix.lower()
    if ext in [".jpeg", ".jpg"]:
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    elif ext == ".webp":
        return "image/webp"
    return "image/jpeg"


def analizar_prenda(imagen_path: str, descripcion: str = "") -> str:
    """
    Usa Gemini 2.5 Flash para analizar la imagen de una prenda y generar un
    análisis descriptivo de su tejido, estilo, corte y detalles visuales.
    """
    client = _get_client()
    
    with open(imagen_path, "rb") as f:
        img_bytes = f.read()
        
    mime_type = _get_mime_type(imagen_path)
    
    prompt = (
        "Analiza detalladamente esta prenda de vestir para un sistema de Virtual Try-On.\n"
        "Describe en español:\n"
        "1. Tipo de prenda y corte (ej. cazadora de cuero, pantalón ajustado, vestido fluido).\n"
        "2. Color principal y secundario con matices exactos.\n"
        "3. Textura del tejido y material visual (ej. vaquero, lana, satén, cuero).\n"
        "4. Detalle de cierres, botones, bolsillos o estampados destacados.\n"
    )
    if descripcion:
        prompt += f"\nNotas adicionales sobre la prenda: {descripcion}"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=img_bytes, mime_type=mime_type),
            prompt
        ]
    )
    
    return response.text if response.text else "Prenda de vestir estándar."


def generar_prompt_vton(analisis: str, nombre_prenda: str) -> str:
    """
    Toma el análisis en español y genera una descripción concisa en inglés
    optimizada para condicionar el modelo Virtual Try-On (CatVTON / IDM-VTON).
    """
    client = _get_client()
    
    prompt = (
        f"Based on this description of clothing item '{nombre_prenda}':\n"
        f"\"{analisis}\"\n\n"
        "Generate a short, precise English prompt (1-2 sentences) describing the garment "
        "for a virtual try-on diffusion model. Focus strictly on visual characteristics: "
        "color, fabric, pattern, neck/sleeve/pant style, and fit. Do NOT describe the person."
    )
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    
    return response.text.strip() if response.text else f"A high quality {nombre_prenda}."
