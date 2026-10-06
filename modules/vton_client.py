"""
Módulo para conectar con IDM-VTON en Hugging Face ZeroGPU via gradio_client.
Módulo para conectar con los modelos de Virtual Try-On en Hugging Face ZeroGPU via gradio_client.
Soporta:
- IDM-VTON (yisol/IDM-VTON) para prendas superiores y abrigos
- OOTDiffusion (levihsu/OOTDiffusion) para partes inferiores, vestidos completos y combinaciones
"""
import os
import time
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from gradio_client import Client, handle_file

load_dotenv()

# Space de IDM-VTON en Hugging Face
HF_SPACE = "yisol/IDM-VTON"
IDM_SPACE = "yisol/IDM-VTON"
OOTD_SPACE = "levihsu/OOTDiffusion"

_client = None
_idm_client = None
_ootd_client = None


def _get_client() -> Client:
    """Inicializa y devuelve el cliente Gradio (singleton)."""
    global _client
    if _client is None:
        hf_token = os.getenv("HF_TOKEN")
        headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
        _client = Client(HF_SPACE, headers=headers)
    return _client
def _get_headers() -> dict:
    hf_token = os.getenv("HF_TOKEN")
    return {"Authorization": f"Bearer {hf_token}"} if hf_token else {}


def _get_idm_client() -> Client:
    global _idm_client
    if _idm_client is None:
        _idm_client = Client(IDM_SPACE, headers=_get_headers())
    return _idm_client


def _get_ootd_client() -> Client:
    global _ootd_client
    if _ootd_client is None:
        _ootd_client = Client(OOTD_SPACE, headers=_get_headers())
    return _ootd_client


def determinar_categoria_vton(categoria: str, subcategoria: str = "", nombre: str = "") -> str:
    """
    Determina si la prenda corresponde a Upper-body, Lower-body o Dress.
    """
    cat_lower = f"{categoria} {subcategoria} {nombre}".lower()
    
    # 1. Vestidos y piezas completas
    if any(k in cat_lower for k in ["vestido", "dress", "mono", "gala", "bañador de una pieza", "banador de una pieza"]):
        return "Dress"
    
    # 2. Partes inferiores
    if any(k in cat_lower for k in ["inferior", "pantalón", "pantalon", "trousers", "pants", "falda", "skirt", "braguita", "shorts"]):
        return "Lower-body"
    
    # 3. Partes superiores y abrigos
    return "Upper-body"


def probar_prenda(
    img_usuario_path: str,
    img_prenda_path: str,
    reintentos: int = 3,
    pausa: float = 5.0,
    prompt: str = "",
    categoria: str = "Parte Superior",
    subcategoria: str = "",
    nombre_prenda: str = "",
    reintentos: int = 2,
    pausa: float = 4.0,
) -> str:
    """
    Ejecuta el virtual try-on con IDM-VTON.

    Args:
        img_usuario_path: Ruta a la imagen de referencia del usuario (siri.png).
        img_prenda_path:  Ruta a la imagen recortada de la prenda.
        prompt:           Descripción textual generada por Gemini.
        reintentos:       Número de intentos ante fallos de ZeroGPU.
        pausa:            Segundos entre reintentos.

    Returns:
        Ruta local al archivo de imagen resultado (str).

    Raises:
        RuntimeError: Si todos los reintentos fallan.
    Ejecuta el virtual try-on adecuado según el tipo de prenda:
    - Lower-body / Dress -> OOTDiffusion (soporta cuerpo completo e inferior)
    - Upper-body -> IDM-VTON (ó OOTDiffusion como respaldo)
    """
    client = _get_client()
    vton_cat = determinar_categoria_vton(categoria, subcategoria, nombre_prenda)

    for intento in range(1, reintentos + 1):
        try:
            result = client.predict(
                dict={
                    "background": handle_file(img_usuario_path),
                    "layers": [],
                    "composite": None,
                },
                garm_img=handle_file(img_prenda_path),
                garment_des=prompt,
                is_checked=True,
                is_checked_crop=False,
                denoise_steps=30,
                seed=42,
                api_name="/tryon",
            )
            # result es una tupla: (imagen_resultado_path, imagen_mascara_path)
            return result[0]
            if vton_cat in ["Lower-body", "Dress"]:
                # Usar OOTDiffusion
                ootd = _get_ootd_client()
                result = ootd.predict(
                    vton_img=handle_file(img_usuario_path),
                    garm_img=handle_file(img_prenda_path),
                    category=vton_cat,
                    n_samples=1,
                    n_steps=20,
                    image_scale=2.0,
                    seed=-1,
                    api_name="/process_dc",
                )
                if isinstance(result, list) and len(result) > 0:
                    return result[0]["image"]
                raise RuntimeError("Formato de respuesta inesperado de OOTDiffusion")

            else:
                # Upper-body / Abrigo -> IDM-VTON
                try:
                    idm = _get_idm_client()
                    result = idm.predict(
                        dict={
                            "background": handle_file(img_usuario_path),
                            "layers": [],
                            "composite": None,
                        },
                        garm_img=handle_file(img_prenda_path),
                        garment_des=prompt or "fashion clothing",
                        is_checked=True,
                        is_checked_crop=False,
                        denoise_steps=30,
                        seed=42,
                        api_name="/tryon",
                    )
                    return result[0]
                except Exception as idm_err:
                    # Fallback a OOTDiffusion Upper-body si IDM-VTON falla
                    ootd = _get_ootd_client()
                    result = ootd.predict(
                        vton_img=handle_file(img_usuario_path),
                        garm_img=handle_file(img_prenda_path),
                        category="Upper-body",
                        n_samples=1,
                        n_steps=20,
                        image_scale=2.0,
                        seed=-1,
                        api_name="/process_dc",
                    )
                    if isinstance(result, list) and len(result) > 0:
                        return result[0]["image"]
                    raise idm_err

        except Exception as e:
            if intento == reintentos:
                raise RuntimeError(
                    f"IDM-VTON falló tras {reintentos} intentos. Último error: {e}"
                    f"Fallo en Virtual Try-On tras {reintentos} intentos. Último error: {e}"
                ) from e
            time.sleep(pausa)


def probar_conjunto(
    img_usuario_path: str,
    prendas: list[dict],
    analisis_dict: dict,
    progreso_callback=None,
) -> str:
    """
    Prueba un conjunto secuencial de hasta 3 prendas:
    1. Parte Inferior primero (pantalón)
    2. Parte Superior segundo (top/camiseta)
    3. Abrigo tercero (chaqueta/blazer)
    """
    # Orden de superposición lógico: Lower-body -> Upper-body -> Abrigo
    def orden_prioridad(p):
        cat = determinar_categoria_vton(p.get("categoria", ""), p.get("subcategoria", ""), p.get("nombre", ""))
        if cat == "Lower-body":
            return 1
        elif cat == "Dress":
            return 2
        elif p.get("categoria") == "Abrigo":
            return 4
        return 3

    prendas_ordenadas = sorted(prendas, key=orden_prioridad)
    imagen_actual = img_usuario_path

    for i, prenda in enumerate(prendas_ordenadas):
        if progreso_callback:
            progreso_callback(i + 1, len(prendas_ordenadas), prenda["nombre"])

        prompt_vton = analisis_dict.get(prenda["id"], {}).get("prompt", "")
        imagen_actual = probar_prenda(
            img_usuario_path=imagen_actual,
            img_prenda_path=prenda["foto_path"],
            prompt=prompt_vton,
            categoria=prenda.get("categoria", ""),
            subcategoria=prenda.get("subcategoria", ""),
            nombre_prenda=prenda.get("nombre", ""),
        )

    return imagen_actual
