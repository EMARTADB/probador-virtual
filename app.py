"""
Probador Virtual Personal — Armario Digital & Multi-Piece Try-On App
"""
import io
import hashlib
import tempfile
from pathlib import Path

import streamlit as st
from PIL import Image

from modules import gemini_client, vton_client
from modules.inventory import InventoryError, load_inventory

# ── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="👗 Probador Virtual Personal",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constantes ───────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
INVENTARIO_PATH = PROJECT_ROOT / "armario" / "inventario.json"
SIRI_PATH = PROJECT_ROOT / "armario" / "siri.png"


# ── Helpers ──────────────────────────────────────────────────────────────────
@st.cache_data
def cargar_inventario() -> tuple[list[dict], list[str]]:
    return load_inventory(INVENTARIO_PATH, PROJECT_ROOT)


def foto_path(prenda: dict) -> str:
    return prenda.get("foto_path_resuelto", prenda.get("foto_path", ""))


def imagen_existe(prenda: dict) -> bool:
    path = foto_path(prenda)
    return bool(path) and Path(path).is_file()


def es_vestido(prenda: dict) -> bool:
    return vton_client.determinar_categoria_vton(
        prenda.get("categoria", ""),
        prenda.get("subcategoria", ""),
        prenda.get("nombre", ""),
    ) == "Dress"


def guardar_imagen_subida(data: bytes) -> Path:
    """Valida, normaliza y guarda temporalmente una imagen sin sus metadatos."""
    digest = hashlib.sha256(data).hexdigest()
    destination_dir = Path(tempfile.gettempdir()) / "probador_virtual"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"persona-{digest}.png"

    if not destination.exists():
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            if image.width * image.height > 25_000_000:
                raise ValueError("La imagen es demasiado grande (máximo 25 megapíxeles).")
            normalized = image.convert("RGB")
            normalized.save(destination, format="PNG", optimize=True)
    return destination


@st.cache_data(show_spinner=False)
def generar_prompt_cacheado(
    imagen_path: str,
    nombre: str,
    descripcion: str,
    version_archivo: int,
) -> str:
    del version_archivo
    return gemini_client.generar_prompt_desde_imagen(
        imagen_path=imagen_path,
        nombre_prenda=nombre,
        descripcion=descripcion,
    )


def clasificar_prenda(p: dict) -> str:
    """Clasifica para el selector de piezas."""
    cat = p.get("categoria", "")
    sub = p.get("subcategoria", "").lower()
    nom = p.get("nombre", "").lower()

    if cat == "Abrigo":
        return "abrigo"
    if cat == "Parte Inferior" or any(k in sub or k in nom for k in ["pantalón", "pantalon", "braguita", "falda"]):
        return "inferior"
    return "superior"


# ── Carga de datos ───────────────────────────────────────────────────────────
try:
    inventario, avisos_inventario = cargar_inventario()
except InventoryError as exc:
    st.error(f"No se pudo cargar el armario: {exc}")
    st.stop()

prendas_superiores = [p for p in inventario if clasificar_prenda(p) == "superior" and imagen_existe(p)]
prendas_inferiores = [p for p in inventario if clasificar_prenda(p) == "inferior" and imagen_existe(p)]
prendas_abrigo = [p for p in inventario if clasificar_prenda(p) == "abrigo" and imagen_existe(p)]

# ── Sidebar ───────────────────────────────────────────────────────────────────
prendas_seleccionadas = []

with st.sidebar:
    st.title("👗 Mi Armario")
    if avisos_inventario:
        with st.expander(f"⚠️ {len(avisos_inventario)} problema(s) en el inventario"):
            for aviso in avisos_inventario:
                st.warning(aviso)
    st.divider()

    modo = st.radio("Modo de Selección", ["✨ Conjunto Completo (hasta 3 piezas)", "👔 Prenda Única"], index=0)
    st.divider()

    if modo == "✨ Conjunto Completo (hasta 3 piezas)":
        st.caption("Selecciona hasta 3 piezas para armar tu conjunto completo.")

        # 1. Top
        st.subheader("1️⃣ Parte Superior / Vestido")
        opc_top = ["(Ninguna)"] + [f"{p['id']} — {p['nombre']}" for p in prendas_superiores]
        sel_top = st.selectbox("Seleccionar Top / Vestido", opc_top, key="sel_top")
        if sel_top != "(Ninguna)":
            p_top = next(p for p in prendas_superiores if f"{p['id']} — {p['nombre']}" == sel_top)
            prendas_seleccionadas.append(p_top)
            st.image(foto_path(p_top), caption=p_top["nombre"], width=180)

        vestido_seleccionado = sel_top != "(Ninguna)" and es_vestido(p_top)

        st.divider()

        # 2. Bottom
        st.subheader("2️⃣ Parte Inferior")
        if vestido_seleccionado:
            st.caption("No se añade una parte inferior a un vestido completo.")
        else:
            opc_bot = ["(Ninguna)"] + [f"{p['id']} — {p['nombre']}" for p in prendas_inferiores]
            sel_bot = st.selectbox("Seleccionar Pantalón / Falda", opc_bot, key="sel_bot")
            if sel_bot != "(Ninguna)":
                p_bot = next(p for p in prendas_inferiores if f"{p['id']} — {p['nombre']}" == sel_bot)
                prendas_seleccionadas.append(p_bot)
                st.image(foto_path(p_bot), caption=p_bot["nombre"], width=180)

        st.divider()

        # 3. Outerwear
        st.subheader("3️⃣ Abrigo / Capa")
        opc_out = ["(Ninguna)"] + [f"{p['id']} — {p['nombre']}" for p in prendas_abrigo]
        sel_out = st.selectbox("Seleccionar Cazadora / Blazer", opc_out, key="sel_out")
        if sel_out != "(Ninguna)":
            p_out = next(p for p in prendas_abrigo if f"{p['id']} — {p['nombre']}" == sel_out)
            prendas_seleccionadas.append(p_out)
            st.image(foto_path(p_out), caption=p_out["nombre"], width=180)

    else:
        st.subheader("Seleccionar Prenda Única")
        categorias = ["Todas"] + sorted({p["categoria"] for p in inventario})
        cat_sel = st.selectbox("Categoría", categorias)

        items_filtrados = [
            p for p in inventario
            if (cat_sel == "Todas" or p["categoria"] == cat_sel) and imagen_existe(p)
        ]
        nombres = [f"{p['id']} — {p['nombre']}" for p in items_filtrados]

        if nombres:
            seleccion = st.selectbox("Prenda", nombres)
            p_sel = next(p for p in items_filtrados if f"{p['id']} — {p['nombre']}" == seleccion)
            prendas_seleccionadas.append(p_sel)
            st.image(foto_path(p_sel), caption=p_sel["nombre"], width=200)

            st.markdown(f"**Estilo:** {', '.join(p_sel.get('estilo', []))}")
            st.markdown(f"**Colores:** {', '.join(p_sel.get('colores', []))}")
            temp_min = p_sel.get("temp_min", "—")
            temp_max = p_sel.get("temp_max", "—")
            st.markdown(f"**Temperatura:** {temp_min}°C – {temp_max}°C")

    st.divider()
    n_prendas = len(prendas_seleccionadas)
    texto_boton = f"✨ Probar {n_prendas} prenda(s)" if n_prendas > 0 else "✨ Probar prenda"
    boton = st.button(texto_boton, type="primary", disabled=(n_prendas == 0), use_container_width=True)


# ── Panel Principal ───────────────────────────────────────────────────────────
st.title("👗 Probador Virtual Personal")
st.markdown("Armario inteligente con análisis multimodal **Gemini 2.5** y generación **Virtual Try-On (ZeroGPU)**.")

col_ref, col_prendas, col_resultado = st.columns([1, 1, 1.2])

with col_ref:
    st.subheader("📸 Modelo Base")
    archivo_usuario = st.file_uploader(
        "Sube una foto de cuerpo entero (opcional)",
        type=["png", "jpg", "jpeg", "webp"],
        help="Si no subes una foto, se utilizará la imagen de ejemplo.",
    )
    imagen_referencia_path = SIRI_PATH
    if archivo_usuario is not None:
        try:
            imagen_referencia_path = guardar_imagen_subida(archivo_usuario.getvalue())
            st.image(str(imagen_referencia_path), caption="Tu foto", use_container_width=True)
        except (OSError, ValueError) as exc:
            st.error(f"No se pudo usar la imagen: {exc}")
            imagen_referencia_path = Path()
    elif SIRI_PATH.exists():
        st.image(str(SIRI_PATH), caption="Siri (imagen de ejemplo)", use_container_width=True)
    else:
        st.error(f"Imagen no encontrada: `{SIRI_PATH}`")
    st.caption("La foto se envía a un Space externo de Hugging Face para generar el resultado.")

with col_prendas:
    st.subheader(f"👔 Selección ({len(prendas_seleccionadas)} piezas)")
    if prendas_seleccionadas:
        for idx, prenda in enumerate(prendas_seleccionadas):
            st.markdown(f"**Pieza {idx + 1}:** {prenda['nombre']}")
            st.caption(f"Categoría: {prenda['categoria']} | Estilo: {', '.join(prenda.get('estilo', []))}")
            if imagen_existe(prenda):
                st.image(foto_path(prenda), width=220)
            st.divider()
    else:
        st.info("👈 Selecciona al menos una prenda en el menú lateral.")

with col_resultado:
    st.subheader("🪄 Resultado del Look")

    if "resultado_img" not in st.session_state:
        st.session_state.resultado_img = None
    if "historial" not in st.session_state:
        st.session_state.historial = []

    if boton:
        if not imagen_referencia_path.is_file():
            st.error("⚠️ Selecciona una imagen de referencia válida.")
        else:
            analisis_dict = {}
            status_box = st.status("🚀 Procesando look virtual...", expanded=True)

            try:
                # Paso 1: un único prompt multimodal por prenda, cacheado.
                status_box.write("🤖 Preparando prendas con Gemini...")
                for p in prendas_seleccionadas:
                    path_prenda = Path(foto_path(p))
                    prompt_en = generar_prompt_cacheado(
                        str(path_prenda),
                        p["nombre"],
                        p.get("descripcion_detallada", ""),
                        path_prenda.stat().st_mtime_ns,
                    )
                    analisis_dict[p["id"]] = {"prompt": prompt_en}
                    status_box.write(f"✓ **{p['nombre']}**: *'{prompt_en}'*")

                # Paso 2: Generación Virtual Try-On
                status_box.write("🪡 Aplicando prendas sobre el avatar...")

                def actualizar_progreso(actual, total, nombre):
                    status_box.write(f"⏳ Procesando pieza {actual}/{total}: **{nombre}**...")

                resultado_path = vton_client.probar_conjunto(
                    img_usuario_path=str(imagen_referencia_path),
                    prendas=prendas_seleccionadas,
                    analisis_dict=analisis_dict,
                    progreso_callback=actualizar_progreso,
                )

                with Image.open(resultado_path) as generated_image:
                    img_resultado = generated_image.copy()
                st.session_state.resultado_img = img_resultado

                nombres_look = " + ".join([p["nombre"] for p in prendas_seleccionadas])
                st.session_state.historial.append({
                    "look": nombres_look,
                    "imagen": img_resultado,
                })
                status_box.update(label="✅ ¡Look generado con éxito!", state="complete", expanded=False)

            except Exception as e:
                status_box.update(label=f"❌ Error: {e}", state="error", expanded=True)
                st.error(f"Detalle del error: {e}")

    # Mostrar resultado
    if st.session_state.resultado_img:
        st.image(st.session_state.resultado_img, caption="Look Final", use_container_width=True)

        buf = io.BytesIO()
        st.session_state.resultado_img.save(buf, format="PNG")
        st.download_button(
            label="⬇️ Descargar resultado",
            data=buf.getvalue(),
            file_name="look_virtual_tryon.png",
            mime="image/png",
            use_container_width=True,
            type="primary",
        )
    else:
        st.info("Selecciona tus prendas y pulsa **✨ Probar prenda(s)** para ver el resultado.")


# ── Historial de looks ────────────────────────────────────────────────────────
if st.session_state.get("historial"):
    st.divider()
    st.subheader("📜 Historial de looks probados en esta sesión")
    cols = st.columns(min(len(st.session_state.historial), 4))
    for i, look in enumerate(reversed(st.session_state.historial[-4:])):
        with cols[i]:
            st.image(look["imagen"], caption=look["look"], use_container_width=True)
