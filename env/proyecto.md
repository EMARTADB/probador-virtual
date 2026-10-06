# 👗 Probador Virtual Personal (Virtual Try-On App)

## 📌 Contexto del Proyecto

### Objetivo
Desarrollar una aplicación web interactiva local en **Python** con **Streamlit** que sirva como **Armario Digital y Probador Virtual (*Virtual Try-On*)**. La aplicación permite seleccionar prendas de vestir de un catálogo local e integrarlas de forma realista sobre una imagen de referencia propia.

### Componentes de la Arquitectura
* **Frontend / Interfaz:** `Streamlit` (desplegado localmente en `http://localhost:8501`).
* **Gestión de Inventario:** Archivo `inventario.json` que mapea las prendas, sus categorías, descripciones y rutas locales a sus imágenes.
* **Motor Multimodal (Gemini API):** `gemini-2.5-flash` para tareas de análisis, lectura de catálogo y generación de *prompts* optimizados.
* **Motor de Generación Visual (Probador Virtual):** Conexión vía API pública/remota con el modelo **`IDM-VTON`** alojado en la infraestructura **ZeroGPU de Hugging Face Spaces**, ejecutado mediante la librería `gradio_client`.

---

## 💡 Resumen de la Solución Técnica

### Justificación de la Arquitectura
1. **Superación de restricciones de la API de Gemini:** Los modelos de la API pública gratuita de Gemini (`gemini-2.5-flash`) procesan imágenes de entrada pero no generan imágenes sintéticas nuevas. Por otro lado, la llamada a `imagen-3.0-generate-002` devuelve un error `404 NOT_FOUND` en cuentas gratuitas de Google AI Studio por requerir facturación en Google Cloud Vertex AI.
2. **Uso de píxeles reales (Image-to-Image / Inpainting):** A diferencia de un modelo *Text-to-Image* que solo recibe descripciones en texto, `IDM-VTON` procesa la imagen real del usuario (`siri.png`) y el recorte de la prenda seleccionada, ajustando el tejido sobre la silueta respetando pose, sombras y anatomía.
3. **Ejecución 100% Gratuita y Local:** La aplicación se ejecuta de forma local sin requerir una GPU dedicada en el PC ni entornos como Google Colab. El procesamiento pesado de IA se delega a las GPUs H100 de ZeroGPU en Hugging Face sin coste.

---

## 🛠️ Requisitos e Instalación

### Dependencias de Python
Instalar las librerías necesarias ejecutando en la terminal: