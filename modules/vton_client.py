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


IDM_SPACE = os.getenv("IDM_SPACE", "yisol/IDM-VTON")
OOTD_SPACE = os.getenv("OOTD_SPACE", "levihsu/OOTDiffusion")

IDM_API_NAME = os.getenv("IDM_API_NAME", "/tryon")
OOTD_API_NAME = os.getenv("OOTD_API_NAME", "/process_dc")


_idm_client = None
_ootd_client = None


class VTONError(RuntimeError):
    """Error contextualizado de los proveedores de Virtual Try-On."""


def _get_headers() -> dict:
    hf_token = os.getenv("HF_TOKEN")

    if hf_token:
        return {
            "Authorization": f"Bearer {hf_token}"
        }

    return {}


def _get_idm_client() -> Client:
    global _idm_client

    if _idm_client is None:
        _idm_client = Client(
            IDM_SPACE,
            token=os.getenv("HF_TOKEN"),
        )

    return _idm_client


def _get_ootd_client() -> Client:
    global _ootd_client

    if _ootd_client is None:
        _ootd_client = Client(
            OOTD_SPACE,
            token=os.getenv("HF_TOKEN"),
        )

    return _ootd_client


def determinar_categoria_vton(
    categoria: str,
    subcategoria: str = "",
    nombre: str = "",
    categoria_vton: str = "",
) -> str:
    """
    Determina si la prenda corresponde a:

    - Upper-body
    - Lower-body
    - Dress

    Si el inventario ya contiene categoria_vton, se utiliza como
    fuente principal.
    """

    categoria_vton_normalizada = (
        categoria_vton or ""
    ).strip().lower()

    if categoria_vton_normalizada in {
        "upper-body",
        "upper_body",
        "upper",
    }:
        return "Upper-body"

    if categoria_vton_normalizada in {
        "lower-body",
        "lower_body",
        "lower",
    }:
        return "Lower-body"

    if categoria_vton_normalizada in {
        "dress",
        "full-body",
        "full_body",
        "fullbody",
    }:
        return "Dress"

    # Compatibilidad con inventarios antiguos.
    cat_lower = (
        f"{categoria} {subcategoria} {nombre}"
    ).lower()

    if any(
        keyword in cat_lower
        for keyword in [
            "vestido",
            "dress",
            "mono",
            "jumpsuit",
            "gala",
            "cuerpo completo",
            "full body",
            "full-body",
            "bañador de una pieza",
            "banador de una pieza",
            "one-piece swimsuit",
        ]
    ):
        return "Dress"

    if any(
        keyword in cat_lower
        for keyword in [
            "inferior",
            "pantalón",
            "pantalon",
            "trousers",
            "pants",
            "falda",
            "skirt",
            "braguita",
            "bikini bottom",
            "shorts",
        ]
    ):
        return "Lower-body"

    return "Upper-body"


def _normalizar_resultado(resultado):
    """
    Normaliza distintos formatos de respuesta de Gradio.
    """

    if isinstance(
        resultado,
        (list, tuple),
    ):
        if not resultado:
            return None

        primer = resultado[0]

        if isinstance(
            primer,
            dict,
        ):
            return _normalizar_resultado(
                primer
            )

        if isinstance(
            primer,
            (
                str,
                bytes,
                os.PathLike,
            ),
        ):
            return str(primer)

        return primer

    if isinstance(
        resultado,
        dict,
    ):
        for key in (
            "image",
            "output",
            "path",
        ):
            if key in resultado:
                return _normalizar_resultado(
                    resultado[key]
                )

        return None

    if hasattr(
        resultado,
        "path",
    ):
        return str(
            resultado.path
        )

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
    categoria_vton: str = "",
) -> str:
    """
    Ejecuta el Virtual Try-On para una prenda concreta.
    """

    for label, path in (
        (
            "imagen de la persona",
            img_usuario_path,
        ),
        (
            "imagen de la prenda",
            img_prenda_path,
        ),
    ):
        if not os.path.isfile(
            path
        ):
            raise FileNotFoundError(
                f"No existe la {label}: {path}"
            )

    vton_cat = determinar_categoria_vton(
        categoria,
        subcategoria,
        nombre_prenda,
        categoria_vton,
    )

    for intento in range(
        1,
        reintentos + 1,
    ):
        try:

            # ----------------------------------------------------------
            # LOWER-BODY y DRESS
            # ----------------------------------------------------------
            if vton_cat in {
                "Lower-body",
                "Dress",
            }:

                ootd = _get_ootd_client()

                result = ootd.predict(
                    vton_img=handle_file(
                        img_usuario_path
                    ),
                    garm_img=handle_file(
                        img_prenda_path
                    ),
                    category=vton_cat,
                    n_samples=1,
                    n_steps=20,
                    image_scale=2.0,
                    seed=-1,
                    api_name=OOTD_API_NAME,
                )

                image = _normalizar_resultado(
                    result
                )

                if image:
                    return image

                raise RuntimeError(
                    "OOTDiffusion no devolvió una imagen válida."
                )

            # ----------------------------------------------------------
            # UPPER-BODY
            # ----------------------------------------------------------
            idm_error = None

            try:
                idm = _get_idm_client()

                garment_description = (
                    prompt
                    or "upper-body fashion garment"
                )

                result = idm.predict(
                    dict={
                        "background": handle_file(
                            img_usuario_path
                        ),
                        "layers": [],
                        "composite": None,
                    },
                    garm_img=handle_file(
                        img_prenda_path
                    ),
                    garment_des=garment_description,
                    is_checked=True,
                    is_checked_crop=False,
                    denoise_steps=30,
                    seed=42,
                    api_name=IDM_API_NAME,
                )

                image = _normalizar_resultado(
                    result
                )

                if image:
                    return image

                raise RuntimeError(
                    "IDM-VTON no devolvió una imagen válida."
                )

            except Exception as exc:
                idm_error = exc

            # ----------------------------------------------------------
            # Fallback de Upper-body usando OOTDiffusion
            # ----------------------------------------------------------
            try:
                ootd = _get_ootd_client()

                result = ootd.predict(
                    vton_img=handle_file(
                        img_usuario_path
                    ),
                    garm_img=handle_file(
                        img_prenda_path
                    ),
                    category="Upper-body",
                    n_samples=1,
                    n_steps=20,
                    image_scale=2.0,
                    seed=-1,
                    api_name=OOTD_API_NAME,
                )

                image = _normalizar_resultado(
                    result
                )

                if image:
                    return image

                raise RuntimeError(
                    "OOTDiffusion no devolvió una imagen válida."
                )

            except Exception as ootd_error:
                raise VTONError(
                    "Fallaron ambos proveedores para una prenda superior. "
                    f"IDM-VTON: {idm_error}. "
                    f"OOTDiffusion: {ootd_error}."
                ) from ootd_error

        except Exception as exc:

            if intento == reintentos:
                raise VTONError(
                    f"Virtual Try-On falló tras {reintentos} intentos "
                    f"para {nombre_prenda or img_prenda_path}. "
                    f"Categoría VTON: {vton_cat}. "
                    f"Último error: {exc}"
                ) from exc

            time.sleep(
                pausa
            )

    raise RuntimeError(
        "No se pudo generar el resultado final."
    )


def probar_conjunto(
    img_usuario_path: str,
    prendas: list[dict],
    analisis_dict: dict,
    progreso_callback=None,
) -> str:
    """
    Aplica varias prendas en un orden lógico.

    Orden:
    1. Lower-body
    2. Dress
    3. Upper-body
    4. Abrigo

    Si existe un Dress, se eliminan las prendas Lower-body del conjunto,
    porque un vestido de cuerpo completo debe reemplazar tanto la zona
    superior como la inferior.
    """

    def categoria_prenda(
        prenda: dict,
    ) -> str:
        return determinar_categoria_vton(
            prenda.get(
                "categoria",
                "",
            ),
            prenda.get(
                "subcategoria",
                "",
            ),
            prenda.get(
                "nombre",
                "",
            ),
            prenda.get(
                "categoria_vton",
                "",
            ),
        )

    # --------------------------------------------------------------
    # Si hay un vestido / prenda de cuerpo completo,
    # no aplicar pantalón o falda debajo.
    # --------------------------------------------------------------
    existe_dress = any(
        categoria_prenda(p)
        == "Dress"
        for p in prendas
    )

    if existe_dress:
        prendas = [
            p
            for p in prendas
            if categoria_prenda(p)
            != "Lower-body"
        ]

    def orden_prioridad(
        prenda: dict,
    ) -> int:

        cat = categoria_prenda(
            prenda
        )

        categoria_original = (
            prenda.get(
                "categoria",
                "",
            )
            or ""
        ).strip().lower()

        if cat == "Lower-body":
            return 1

        if cat == "Dress":
            return 2

        if categoria_original == "abrigo":
            return 4

        return 3

    prendas_ordenadas = sorted(
        prendas,
        key=orden_prioridad,
    )

    imagen_actual = (
        img_usuario_path
    )

    for i, prenda in enumerate(
        prendas_ordenadas
    ):

        if progreso_callback:
            progreso_callback(
                i + 1,
                len(
                    prendas_ordenadas
                ),
                prenda["nombre"],
            )

        prompt_vton = (
            analisis_dict
            .get(
                prenda["id"],
                {},
            )
            .get(
                "prompt",
                "",
            )
        )

        imagen_actual = probar_prenda(
            img_usuario_path=imagen_actual,
            img_prenda_path=prenda.get(
                "foto_path_resuelto",
                prenda["foto_path"],
            ),
            prompt=prompt_vton,
            categoria=prenda.get(
                "categoria",
                "",
            ),
            subcategoria=prenda.get(
                "subcategoria",
                "",
            ),
            nombre_prenda=prenda.get(
                "nombre",
                "",
            ),
            categoria_vton=prenda.get(
                "categoria_vton",
                "",
            ),
        )

    return imagen_actual