"""
Probador Virtual Personal — app principal Streamlit
Probador Virtual Personal — Armario Digital & Multi-Piece Try-On App
"""
import io
import json
import os
from pathlib import Path

import streamlit as st
from PIL import Image

from modules import gemini_client, vton_client

# ── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="👗 Probador Virtual",
    page_title="👗 Probador Virtual Personal",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constantes ───────────────────────────────────────────────────────────────
INVENTARIO_PATH = Path("armario/inventario.json")
SIRI_PATH = Path("armario/siri.png")
SIN_IMAGEN = Path("armario")  # fallback


# ── Helpers ──────────────────────────────────────────────────────────────────
@st.cache_data
def cargar_inventario() -> list[dict]:
    with open(INVENTARIO_PATH, encoding="utf-8-sig") as f:
        return json.load(f)


def imagen_existe(path: str) -> bool:
    return Path(path).exists()
    return Path(path).exists() if path else False


def mostrar_prenda(prenda: dict, caption: str = "") -> None:
    foto = prenda.get("foto_path", "")
    if imagen_existe(foto):
        st.image(foto, caption=caption or prenda["nombre"], use_container_width=True)
    else:
        st.warning(f"Imagen no encontrada: `{foto}`")
def clasificar_prenda(p: dict) -> str:
    """Clasifica para el selector de 3 piezas."""
    cat = p.get("categoria", "")
    sub = p.get("subcategoria", "").lower()
    nom = p.get("nombre", "").lower()

    if cat == "Abrigo":
        return "abrigo"
    if cat == "Parte Inferior" or any(k in sub or k in nom for k in ["pantalón", "pantalon", "braguita"]):
        return "inferior"
    return "superior"


# ── Carga de datos ───────────────────────────────────────────────────────────
inventario = cargar_inventario()

# Separar por tipos para la selección de hasta 3 piezas
prendas_superiores = [p for p in inventario if clasificar_prenda(p) == "superior" and imagen_existe(p.get("foto_path", ""))]
prendas_inferiores = [p for p in inventario if clasificar_prenda(p) == "inferior" and imagen_existe(p.get("foto_path", ""))]
prendas_abrigo = [p for p in inventario if clasificar_prenda(p) == "abrigo" and imagen_existe(p.get("foto_path", ""))]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("👗 Mi Armario")
    st.divider()
    st.caption("Selecciona hasta 3 piezas para armar tu conjunto completo.")

    inventario = cargar_inventario()
    modo = st.radio("Modo de Selección", ["✨ Conjunto Completo (hasta 3 piezas)", "👔 Prenda Única"], index=0)

    # Filtro por categoría
    categorias = ["Todas"] + sorted({p["categoria"] for p in inventario})
    cat_sel = st.selectbox("📂 Categoría", categorias)
    prendas_seleccionadas = []

    prendas_filtradas = (
        inventario if cat_sel == "Todas"
        else [p for p in inventario if p["categoria"] == cat_sel]
    )
    if modo == "✨ Conjunto Completo (hasta 3 piezas)":
        st.subheader("1️⃣ Parte Superior / Vestido")
        opc_top = ["(Ninguna)"] + [f"{p['id']} — {p['nombre']}" for p in prendas_superiores]
        sel_top = st.selectbox("Seleccionar Top / Vestido", opc_top, key="sel_top")
        if sel_top != "(Ninguna)":
            p_top = next(p for p in prendas_superiores if f"{p['id']} — {p['nombre']}" == sel_top)
            prendas_seleccionadas.append(p_top)
            st.image(p_top["foto_path"], caption=p_top["nombre"], width=180)

    # Selector de prenda
    nombres = [f"{p['id']} — {p['nombre']}" for p in prendas_filtradas]
    seleccion = st.selectbox("👔 Prenda", nombres)
    idx = nombres.index(seleccion)
    prenda_sel = prendas_filtradas[idx]
        st.divider()
        st.subheader("2️⃣ Parte Inferior")
        opc_bot = ["(Ninguna)"] + [f"{p['id']} — {p['nombre']}" for p in prendas_inferiores]
        sel_bot = st.selectbox("Seleccionar Pantalón / Falda", opc_bot, key="sel_bot")
        if sel_bot != "(Ninguna)":
            p_bot = next(p for p in prendas_inferiores if f"{p['id']} — {p['nombre']}" == sel_bot)
            prendas_seleccionadas.append(p_bot)
            st.image(p_bot["foto_path"], caption=p_bot["nombre"], width=180)

    st.divider()
    st.markdown("**Prenda seleccionada:**")
    foto = prenda_sel.get("foto_path", "")
    if imagen_existe(foto):
        st.image(foto, use_container_width=True)
        st.divider()
        st.subheader("3️⃣ Abrigo / Capa")
        opc_out = ["(Ninguna)"] + [f"{p['id']} — {p['nombre']}" for p in prendas_abrigo]
        sel_out = st.selectbox("Seleccionar Cazadora / Blazer", opc_out, key="sel_out")
        if sel_out != "(Ninguna)":
            p_out = next(p for p in prendas_abrigo if f"{p['id']} — {p['nombre']}" == sel_out)
            prendas_seleccionadas.append(p_out)
            st.image(p_out["foto_path"], caption=p_out["nombre"], width=180)

    else:
        st.info("Sin imagen disponible")
        # Prenda única
        st.subheader("Seleccionar Prenda")
        categorias = ["Todas"] + sorted({p["categoria"] for p in inventario})
        cat_sel = st.selectbox("Categoría", categorias)

    st.markdown(f"**Estilo:** {', '.join(prenda_sel.get('estilo', []))}")
    st.markdown(f"**Colores:** {', '.join(prenda_sel.get('colores', []))}")
    temp_min = prenda_sel.get("temp_min", "—")
    temp_max = prenda_sel.get("temp_max", "—")
    st.markdown(f"**Temperatura:** {temp_min}°C – {temp_max}°C")
        items_filtrados = [
            p for p in inventario
            if (cat_sel == "Todas" or p["categoria"] == cat_sel) and imagen_existe(p.get("foto_path", ""))
        ]
        nombres = [f"{p['id']} — {p['nombre']}" for p in items_filtrados]
        if nombres:
            seleccion = st.selectbox("Prenda", nombres)
            p_sel = next(p for p in items_filtrados if f"{p['id']} — {p['nombre']}" == seleccion)
            prendas_seleccionadas.append(p_sel)
            st.image(p_sel["foto_path"], caption=p_sel["nombre"], width=200)

    st.divider()
    boton = st.button("✨ Probar prenda", use_container_width=True, type="primary")
    n_prendas = len(prendas_seleccionadas)
    texto_boton = f"✨ Probar {n_prendas} prenda(s)" if n_prendas > 0 else "✨ Probar prenda"
    boton = st.button(texto_boton, type="primary", disabled=(n_prendas == 0))


# ── Panel principal ───────────────────────────────────────────────────────────
# ── Panel Principal ───────────────────────────────────────────────────────────
st.title("👗 Probador Virtual Personal")
st.caption("Selecciona una prenda del armario y pruébatela virtualmente.")
st.markdown("Armario inteligente con análisis multimodal **Gemini 2.5** y generación **Virtual Try-On (ZeroGPU)**.")

col_ref, col_prenda, col_resultado = st.columns([1, 1, 1])
col_ref, col_prendas, col_resultado = st.columns([1, 1, 1.2])

with col_ref:
    st.subheader("📸 Tú")
    st.subheader("📸 Modelo Base")
    if SIRI_PATH.exists():
        st.image(str(SIRI_PATH), use_container_width=True)
        st.image(str(SIRI_PATH), caption="Siri (Referencia)", width="stretch")
    else:
        st.error(f"Imagen de referencia no encontrada: `{SIRI_PATH}`")
        st.error(f"Imagen no encontrada: `{SIRI_PATH}`")

with col_prenda:
    st.subheader("👔 Prenda")
    mostrar_prenda(prenda_sel)
    with st.expander("📋 Descripción completa"):
        st.write(prenda_sel.get("descripcion_detallada", "Sin descripción."))
with col_prendas:
    st.subheader(f"👔 Selección ({len(prendas_seleccionadas)} piezas)")
    if prendas_seleccionadas:
        for idx, prenda in enumerate(prendas_seleccionadas):
            st.markdown(f"**Pieza {idx + 1}:** {prenda['nombre']}")
            st.caption(f"Categoría: {prenda['categoria']} | Estilo: {', '.join(prenda.get('estilo', []))}")
            st.image(prenda["foto_path"], width=220)
            st.divider()
    else:
        st.info("👈 Selecciona al menos una prenda en el menú lateral.")

with col_resultado:
    st.subheader("🪄 Resultado")
    st.subheader("🪄 Resultado del Look")

    # Inicializar estado de sesión
    if "resultado_img" not in st.session_state:
        st.session_state.resultado_img = None
    if "historial" not in st.session_state:
        st.session_state.historial = []

    if boton:
        foto_prenda = prenda_sel.get("foto_path", "")
        if not SIRI_PATH.exists():
            st.error("No se encontró la imagen de referencia `armario/siri.png`.")
        else:
            analisis_dict = {}
            status_box = st.status("🚀 Procesando look virtual...", expanded=True)

        if not imagen_existe(foto_prenda):
            st.error("⚠️ Esta prenda no tiene imagen local. No se puede procesar.")
        elif not SIRI_PATH.exists():
            st.error("⚠️ No se encontró la imagen de referencia `armario/siri.png`.")
        else:
            # Paso 1: Análisis con Gemini
            with st.spinner("🤖 Analizando prenda con Gemini..."):
                try:
            try:
                # Paso 1: Análisis Multimodal en Inglés con Gemini
                status_box.write("🤖 Analizando prendas con Gemini (descripciones técnicas en inglés)...")
                for p in prendas_seleccionadas:
                    analisis = gemini_client.analizar_prenda(
                        imagen_path=foto_prenda,
                        descripcion=prenda_sel.get("descripcion_detallada", ""),
                        imagen_path=p["foto_path"],
                        descripcion=p.get("descripcion_detallada", ""),
                    )
                    prompt_vton = gemini_client.generar_prompt_vton(
                        analisis=analisis,
                        nombre_prenda=prenda_sel["nombre"],
                    )
                    st.toast("✅ Análisis Gemini completado", icon="🤖")
                except Exception as e:
                    st.error(f"❌ Error en Gemini: {e}")
                    st.stop()
                    prompt_en = gemini_client.generar_prompt_vton(analisis, p["nombre"])
                    analisis_dict[p["id"]] = {"analisis": analisis, "prompt": prompt_en}
                    status_box.write(f"✓ **{p['nombre']}**: *'{prompt_en}'*")

            # Paso 2: Virtual Try-On con IDM-VTON
            with st.spinner("🪡 Generando prueba virtual (puede tardar 30-60s)..."):
                try:
                    resultado_path = vton_client.probar_prenda(
                        img_usuario_path=str(SIRI_PATH),
                        img_prenda_path=foto_prenda,
                        prompt=prompt_vton,
                    )
                    img_resultado = Image.open(resultado_path)
                    st.session_state.resultado_img = img_resultado
                # Paso 2: Generación Virtual Try-On
                status_box.write("🪡 Aplicando prendas sobre el avatar...")

                    # Guardar en historial
                    st.session_state.historial.append({
                        "prenda": prenda_sel["nombre"],
                        "imagen": img_resultado,
                    })
                    st.toast("✅ Try-on completado", icon="🪡")
                except Exception as e:
                    st.error(f"❌ Error en IDM-VTON: {e}")
                    st.stop()
                def actualizar_progreso(actual, total, nombre):
                    status_box.write(f"⏳ Procesando pieza {actual}/{total}: **{nombre}**...")

                resultado_path = vton_client.probar_conjunto(
                    img_usuario_path=str(SIRI_PATH),
                    prendas=prendas_seleccionadas,
                    analisis_dict=analisis_dict,
                    progreso_callback=actualizar_progreso,
                )

                img_resultado = Image.open(resultado_path)
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
        st.image(st.session_state.resultado_img, use_container_width=True)
        st.image(st.session_state.resultado_img, caption="Look Final", width="stretch")

        # Botón de descarga
        import io
        buf = io.BytesIO()
        st.session_state.resultado_img.save(buf, format="PNG")
        st.download_button(
            label="⬇️ Descargar resultado",
            data=buf.getvalue(),
            file_name=f"look_{prenda_sel['id']}.png",
            file_name="look_virtual_tryon.png",
            mime="image/png",
            use_container_width=True,
            type="primary",
        )
    else:
        st.info("Pulsa **✨ Probar prenda** para ver el resultado aquí.")
        st.info("Selecciona tus prendas y pulsa **✨ Probar prenda(s)** para ver el resultado.")


# ── Historial de looks ────────────────────────────────────────────────────────
if st.session_state.get("historial"):
    st.divider()
    st.subheader("📜 Historial de looks probados")
    st.subheader("📜 Historial de looks probados en esta sesión")
    cols = st.columns(min(len(st.session_state.historial), 4))
    for i, look in enumerate(reversed(st.session_state.historial[-4:])):
        with cols[i]:
            st.image(look["imagen"], caption=look["prenda"], use_container_width=True)
            st.image(look["imagen"], caption=look["look"], width="stretch")
