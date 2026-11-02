# Probador Virtual Personal

Aplicación local de Streamlit para seleccionar prendas de un armario digital y
probarlas sobre una fotografía mediante Gemini e IDM-VTON/OOTDiffusion.

## Requisitos

- Python 3.11 o 3.12.
- Una clave de Google AI Studio en `GEMINI_API_KEY`.
- Opcional: un token de Hugging Face en `HF_TOKEN`; resulta útil para Spaces que
  exigen autenticación o aplican límites más restrictivos a usuarios anónimos.
- Conexión a Internet durante la generación.

## Instalación

En PowerShell, desde la carpeta del proyecto:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` y sustituye el valor de `GEMINI_API_KEY`. No publiques ese archivo
ni pegues claves reales en el repositorio.

Los nombres de los Spaces y sus endpoints también pueden modificarse en `.env`
si los proveedores cambian su API, sin necesidad de editar el código.

## Ejecución

```powershell
streamlit run app.py
```

Abre `http://localhost:8501`. Puedes subir una fotografía PNG, JPEG o WebP de
cuerpo entero. Si no lo haces, se utiliza `armario/siri.png` como demostración.

Para obtener mejores resultados utiliza una imagen frontal, bien iluminada, con
los brazos ligeramente separados del torso y sin ropa excesivamente holgada.

## Privacidad y servicios externos

- Las imágenes de las prendas se envían a Google Gemini para producir una
  descripción visual breve.
- La fotografía de la persona y las prendas se envían a Spaces externos de
  Hugging Face para generar el resultado.
- La fotografía subida se normaliza a PNG, sin metadatos, y se guarda de forma
  temporal en el equipo.

No utilices fotografías sensibles si no aceptas este tratamiento por terceros.
Consulta también las políticas de Google y Hugging Face antes de desplegar la
aplicación para otras personas.

## Inventario

Las prendas se definen en `armario/inventario.json`. Cada entrada necesita como
mínimo:

```json
{
  "id": "PR001",
  "nombre": "Nombre visible",
  "categoria": "Parte Superior",
  "foto_path": "armario/imagen.png"
}
```

Los identificadores deben ser únicos. Al arrancar, la aplicación valida el JSON
y muestra en la barra lateral los archivos de imagen ausentes.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas también se ejecutan automáticamente en GitHub para Python 3.11 y
3.12. Las llamadas reales a Gemini y Hugging Face no forman parte de las pruebas
unitarias porque dependen de credenciales, disponibilidad y cuota externas.

## Limitaciones conocidas

- Los Spaces públicos pueden cambiar sus parámetros, entrar en cola o dejar de
  estar disponibles.
- Los conjuntos se generan aplicando prendas sucesivamente. Cada paso puede
  introducir artefactos o modificar parcialmente una prenda anterior.
- Una imagen de catálogo limpia y frontal suele producir mejores resultados que
  una fotografía con modelo o un fondo complejo.
