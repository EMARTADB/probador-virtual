"""
Cliente Gemini para analizar prendas y construir prompts descriptivos
para el motor Virtual Try-On.
"""

import os
from pathlib import Path

from google import genai
from google.genai import types


def _get_api_key() -> str:
    """
    Obtiene GEMINI_API_KEY desde variables de entorno o Streamlit secrets.
    """
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key:
        return api_key

    try:
        import streamlit as st

        api_key = st.secrets.get("GEMINI_API_KEY")
        if api_key:
            return str(api_key)

    except Exception:
        pass

    raise RuntimeError(
        "No se encontró GEMINI_API_KEY en las variables de entorno ni en st.secrets."
    )


def _crear_cliente() -> genai.Client:
    return genai.Client(
        api_key=_get_api_key()
    )


def _instruccion_categoria(categoria_vton: str) -> str:
    """
    Devuelve instrucciones específicas según la categoría VTON.
    """

    categoria = (
        categoria_vton
        or ""
    ).strip().lower()

    if categoria == "dress":
        return (
            "Treat this garment as a FULL-BODY garment. "
            "It must cover both the upper body and lower body. "
            "Examples include dresses, jumpsuits, one-piece swimsuits "
            "and similar full-body garments. "
            "Do not describe it as only a top or upper-body garment."
        )

    if categoria == "lower-body":
        return (
            "Treat this garment strictly as a LOWER-BODY garment. "
            "Focus only on trousers, skirts, shorts, bikini bottoms "
            "or other clothing intended for the waist and legs. "
            "If the source image contains an upper-body garment too, "
            "ignore it."
        )

    if categoria == "upper-body":
        return (
            "Treat this garment strictly as an UPPER-BODY garment. "
            "Focus only on tops, shirts, blouses, jackets, bikini tops "
            "or other clothing intended for the torso. "
            "If the source image contains a lower-body garment too, "
            "ignore it."
        )

    return (
        "Describe only the garment that is relevant for virtual try-on."
    )


def generar_prompt_desde_imagen(
    imagen_path: str,
    nombre_prenda: str = "",
    descripcion: str = "",
    categoria_vton: str = "",
) -> str:
    """
    Analiza visualmente una prenda con Gemini y devuelve una descripción
    breve en inglés optimizada para Virtual Try-On.

    Args:
        imagen_path:
            Ruta local de la imagen de la prenda.

        nombre_prenda:
            Nombre descriptivo registrado en el inventario.

        descripcion:
            Descripción adicional del inventario.

        categoria_vton:
            Categoría explícita usada por el motor VTON:
            Upper-body, Lower-body o Dress.

    Returns:
        Prompt descriptivo en inglés.
    """

    path = Path(
        imagen_path
    )

    if not path.is_file():
        raise FileNotFoundError(
            f"No existe la imagen de la prenda: {imagen_path}"
        )

    client = _crear_cliente()

    instrucciones_categoria = (
        _instruccion_categoria(
            categoria_vton
        )
    )

    contexto = []

    if nombre_prenda:
        contexto.append(
            f"Inventory name: {nombre_prenda}"
        )

    if descripcion:
        contexto.append(
            f"Inventory description: {descripcion}"
        )

    if categoria_vton:
        contexto.append(
            f"Virtual try-on category: {categoria_vton}"
        )

    contexto_texto = "\n".join(
        contexto
    )

    prompt = f"""
You are analysing a garment image for a virtual try-on system.

{contexto_texto}

CATEGORY INSTRUCTIONS:
{instrucciones_categoria}

Describe ONLY the garment that should be applied to the person.

The description must be concise, visual and useful for image generation.
Describe:

- garment type
- main color
- secondary colors if relevant
- fabric or apparent material
- pattern
- neckline
- sleeve type
- length
- silhouette / fit
- relevant construction details

Important rules:

1. Do not describe the model, mannequin, background, hanger or environment.
2. Do not describe unrelated garments present in the same image.
3. Respect the supplied virtual try-on category.
4. If category is Dress, describe the garment as a full-body piece.
5. If category is Upper-body, ignore lower-body pieces visible in the image.
6. If category is Lower-body, ignore upper-body pieces visible in the image.
7. Do not invent accessories.
8. Return only one short English description.
9. Do not use markdown.
"""

    image_bytes = path.read_bytes()

    suffix = path.suffix.lower()

    mime_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(
        suffix,
        "image/png",
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type,
            ),
            prompt,
        ],
    )

    texto = (
        response.text
        or ""
    ).strip()

    if not texto:
        raise RuntimeError(
            "Gemini no devolvió una descripción de la prenda."
        )

    return texto