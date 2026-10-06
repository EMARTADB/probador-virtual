"""
Módulo para conectar con modelos de Virtual Try-On en Hugging Face ZeroGPU.
Soporta:
- IDM-VTON para prendas superiores y abrigos
- OOTDiffusion para partes inferiores y vestidos
"""
import os
import time

from dotenv import load_dotenv
from gradio_client import Client, handle_file

load_dotenv()

HF_SPACE = "yisol/IDM-VTON"
IDM_SPACE = "yisol/IDM-VTON"
OOTD_SPACE = "levihsu/OOTDiffusion"

_client = None
_idm_client = None
_ootd_client = None


def _get_headers() -> dict:
    hf_token = os.getenv("HF_TOKEN")
    return {"Authorization": f"Bearer {hf_token}"} if hf_token else {}


def _get_client() -> Client:
    """Inicializa y devuelve el cliente Gradio (singleton)."""
    global _client
    if _client is None:
        _client = Client(HF_SPACE, headers=_get_headers())
    return _client


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
    """Determina si la prenda corresponde a Upper-body, Lower-body o Dress."""
    cat_lower = f"{categoria} {subcategoria} {nombre}".lower()

    if any(k in cat_lower for k in ["vestido", "dress", "mono", "gala", "bañador de una pieza", "banador de una pieza"]):
        return "Dress"
    if any(k in cat_lower for k in ["inferior", "pantalón", "pantalon", "trousers", "pants", "falda", "skirt", "braguita", "shorts"]):
        return "Lower-body"
    return "Upper-body"


def _normalizar_resultado(resultado):
    """Normaliza distintos formatos de respuesta de Gradio."""
    if isinstance(resultado, (list, tuple)):
        if not resultado:
            return None
        primer = resultado[0]
        if isinstance(primer, dict):
            for key in ("image", "output", "path"):
                if key in primer:
                    return primer[key]
            return primer
        if isinstance(primer, (str, bytes, os.PathLike)):
            return str(primer)
        return primer
    if isinstance(resultado, dict):
        for key in ("image", "output", "path"):
            if key in resultado:
                return resultado[key]
    return resultado


def probar_prenda(
    img_usuario_path: str,
    img_prenda_path: str,
    prompt: str,
    reintentos: int = 3,
    pausa: float = 5.0,
    categoria: str = "Parte Superior",
    subcategoria: str = "",
    nombre_prenda: str = "",
) -> str:
    """Ejecuta el virtual try-on para una prenda concreta."""
    vton_cat = determinar_categoria_vton(categoria, subcategoria, nombre_prenda)

    for intento in range(1, reintentos + 1):
        try:
            if vton_cat in ["Lower-body", "Dress"]:
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
                image = _normalizar_resultado(result)
                if image:
                    return image
                raise RuntimeError("OOTDiffusion no devolvió una imagen válida.")

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
                image = _normalizar_resultado(result)
                if image:
                    return image
            except Exception:
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
                image = _normalizar_resultado(result)
                if image:
                    return image
                raise

            raise RuntimeError("El modelo no devolvió una imagen válida.")

        except Exception as e:
            if intento == reintentos:
                raise RuntimeError(f"Virtual Try-On falló tras {reintentos} intentos. Último error: {e}") from e
            time.sleep(pausa)

    raise RuntimeError("No se pudo generar el resultado final.")


def probar_conjunto(
    img_usuario_path: str,
    prendas: list[dict],
    analisis_dict: dict,
    progreso_callback=None,
) -> str:
    """Aplica varias prendas en orden lógico: inferior → superior → abrigo."""

    def orden_prioridad(p):
        cat = determinar_categoria_vton(p.get("categoria", ""), p.get("subcategoria", ""), p.get("nombre", ""))
        if cat == "Lower-body":
            return 1
        if cat == "Dress":
            return 2
        if p.get("categoria") == "Abrigo":
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
