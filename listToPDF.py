#!/usr/bin/env python3
import os
import shutil
import asyncio
import time
from icrawler.builtin import GoogleImageCrawler
from googletrans import Translator
from PIL import Image  # Para validar las imágenes

# --- CONFIGURACIÓN ---
# Archivo con la lista de elementos (una palabra por línea)
LISTA_FILE = "lista.txt"

# Carpeta temporal para descargar imágenes
IMG_TMP_DIR = "tmp_imagenes"
# Carpeta destino para las imágenes (en este ejemplo, se usa el mismo directorio que el script)
IMG_DEST_DIR = "."

# Tamaño de la imagen en la tabla (3.5 x 3.5 cm)
IMG_WIDTH = "3.5cm"
IMG_HEIGHT = "3.5cm"

# Códigos de idioma para las traducciones:
# "es": español (España), "ca": catalán, "en": inglés, "fr": francés, "ma": marroquí (se usará 'ar' como aproximación)
lang_codes = {
    "es": "es",
    "ca": "ca",
    "en": "en",
    "fr": "fr",
    "ma": "ar"
}
# --- FIN CONFIGURACIÓN ---

# Asegurarse de que exista la carpeta temporal para imágenes
os.makedirs(IMG_TMP_DIR, exist_ok=True)

# Inicializar el traductor
translator = Translator()

# Leer la lista de elementos
with open(LISTA_FILE, encoding="utf-8") as f:
    elements = [line.strip() for line in f if line.strip()]

# --- PARTE ASINCRÓNICA: TRADUCCIONES ---
async def obtener_traducciones(elem: str) -> dict:
    """
    Traduce el elemento a los idiomas deseados y devuelve un diccionario
    con las traducciones.
    """
    traducciones = {}
    for key, dest in lang_codes.items():
        try:
            resultado = await translator.translate(elem, dest=dest)
            traducciones[key] = resultado.text
        except Exception as e:
            print(f"Error traduciendo '{elem}' a {dest}: {e}")
            traducciones[key] = elem  # Valor por defecto en caso de error
    return traducciones

async def procesar_traducciones(elements: list) -> dict:
    """
    Crea tareas para traducir cada elemento y devuelve un diccionario
    del tipo:
      { elemento: { idioma: traducción, ... }, ... }
    """
    resultados = {}
    tasks = [asyncio.create_task(obtener_traducciones(elem)) for elem in elements]
    traducciones_list = await asyncio.gather(*tasks)
    for i, elem in enumerate(elements):
        resultados[elem] = traducciones_list[i]
    return resultados

print("Realizando traducciones automáticas...")
translations = asyncio.run(procesar_traducciones(elements))
print("Traducciones completadas.")

# --- FUNCIÓN PARA VALIDAR IMÁGENES ---
def validar_imagen(path: str) -> bool:
    """
    Intenta abrir y verificar la imagen para determinar si es válida.
    """
    try:
        with Image.open(path) as img:
            img.verify()  # Lanza excepción si la imagen está corrupta
        return True
    except Exception as e:
        print(f"Error validando la imagen {path}: {e}")
        return False

# --- DESCARGA DE IMÁGENES (SÍNCRONA) ---
def descargar_imagen(consulta: str, destino: str, nombre_elemento: str) -> bool:
    """
    Revisa si ya existe una imagen válida para 'nombre_elemento' en el destino.
    Si no existe o está corrupta, utiliza GoogleImageCrawler para buscar y
    descargar la primera imagen encontrada. Renombra la imagen descargada a 
    <nombre_elemento>.jpg.
    """
    dest_file = os.path.join(destino, f"{nombre_elemento}.jpg")
    # Si ya existe un archivo para este elemento, validarlo.
    if os.path.exists(dest_file):
        if validar_imagen(dest_file):
            print(f"La imagen para '{nombre_elemento}' ya existe y es válida. Saltando descarga.")
            return True
        else:
            print(f"La imagen para '{nombre_elemento}' es inválida. Se procederá a re-descargarla.")
            os.remove(dest_file)

    # Utilizar icrawler para descargar la imagen
    crawler = GoogleImageCrawler(storage={'root_dir': IMG_TMP_DIR})
    # Puedes agregar un delay o modificar parámetros de búsqueda si es necesario.
    crawler.crawl(keyword=consulta, max_num=1)
    archivos = os.listdir(IMG_TMP_DIR)
    if archivos:
        archivo = os.path.join(IMG_TMP_DIR, sorted(archivos)[0])
        nuevo_path = os.path.join(destino, f"{nombre_elemento}.jpg")
        shutil.move(archivo, nuevo_path)
        # Agregar un breve delay para evitar peticiones muy frecuentes.
        time.sleep(1)
        # Limpiar la carpeta temporal para la próxima descarga
        for f in os.listdir(IMG_TMP_DIR):
            os.remove(os.path.join(IMG_TMP_DIR, f))
        return True
    else:
        print(f"No se encontró imagen para: {consulta}")
        return False

print("Descargando imágenes...")
for elem in elements:
    consulta = elem  # Puedes refinar la consulta si lo deseas.
    exito = descargar_imagen(consulta, IMG_DEST_DIR, elem)
    if not exito:
        print(f"Advertencia: No se descargó imagen para {elem}.")
print("Descarga de imágenes completada.")

# --- GENERACIÓN DEL ARCHIVO LaTeX ---
latex_rows = ""
for elem in elements:
    tr = translations[elem]
    # Se espera que la imagen esté en <elem>.jpg.
    latex_rows += (
        f"\\includegraphics[width={IMG_WIDTH},height={IMG_HEIGHT}]{{{elem}.jpg}} & "
        f"{tr['es']} & {tr['ca']} & {tr['en']} & {tr['fr']} & {tr['ma']} \\\\ \\hline\n"
    )

latex_template = f"""\\documentclass{{article}}
\\usepackage{{graphicx}}
\\usepackage{{longtable}}
\\usepackage{{polyglossia}}
\\setdefaultlanguage{{spanish}}
\\setotherlanguage{{arabic}}
\\setmainfont{{Amiri}}
\\newfontfamily\\arabicfont[Script=Arabic]{{Amiri}}

\\begin{{document}}
\\section*{{Frutas y Verduras en Múltiples Idiomas}}

\\begin{{longtable}}{{|c|c|c|c|c|c|}}
\\hline
\\textbf{{Imagen}} & \\textbf{{Español}} & \\textbf{{Catalán}} & \\textbf{{Inglés}} & \\textbf{{Francés}} & \\textbf{{Marroquí}} \\\\ \\hline
{latex_rows}
\\end{{longtable}}

\\end{{document}}
"""

with open("tabla.tex", "w", encoding="utf-8") as f:
    f.write(latex_template)

print("Archivo 'tabla.tex' generado correctamente.")
print("Compila 'tabla.tex' (por ejemplo, con lualatex) para obtener el PDF final.")
