from fastapi import APIRouter, HTTPException
import json
import os

router = APIRouter(
    prefix="/busqueda",
    tags=["busqueda"]
)

datos_palabras = {}

def cargar_json():
    global datos_palabras
    try:
        with open("data/videos_locales.json", 'r', encoding='utf-8') as archivo:
            datos_palabras = json.load(archivo)
        print(" JSON cargado correctamente")
    except Exception as error:
        print(f" Error cargando JSON: {error}")

cargar_json()

def buscar_video(palabra):
    palabra_minuscula = palabra.lower()
    for categoria in datos_palabras.values():
        for subcategoria in categoria.values():
            if isinstance(subcategoria, list):
                for item in subcategoria:
                    if item.get('palabra'):
                        if item['palabra'].lower() == palabra_minuscula:
                            return item.get('ruta_local')  # ← usa ruta_local
    return None

@router.get("/")
async def buscar_palabra(q: str):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Palabra no puede estar vacía")
    if not datos_palabras:
        raise HTTPException(status_code=500, detail="Datos no disponibles")

    ruta = buscar_video(q)

    if ruta:
        print(f"[busqueda] Encontrada: '{q}'")
        return {
            "palabra": q,
            "encontrada": True,
            "url_streaming": ruta  # ahora devuelve ruta local
        }
    else:
        print(f"[busqueda] No encontrada: '{q}'")
        return {
            "palabra": q,
            "encontrada": False,
            "url_streaming": None
        }

@router.get("/palabras-categorizadas")
async def obtener_palabras_categorizadas():
    if not datos_palabras:
        raise HTTPException(status_code=500, detail="Datos no disponibles")

    categorias_organizadas = {}
    total_palabras = 0

    for categoria_nombre, categoria_data in datos_palabras.items():
        if isinstance(categoria_data, dict):
            categorias_organizadas[categoria_nombre] = {}
            for subcategoria_nombre, subcategoria_data in categoria_data.items():
                if isinstance(subcategoria_data, list):
                    palabras = []
                    for item in subcategoria_data:
                        if isinstance(item, dict) and item.get('palabra'):
                            palabras.append({
                                "palabra": item['palabra'],
                                "tiene_video": bool(item.get('ruta_local'))  # ← usa ruta_local
                            })
                            total_palabras += 1
                    if palabras:
                        categorias_organizadas[categoria_nombre][subcategoria_nombre] = palabras

    print(f"[busqueda] Palabras categorizadas solicitadas | Total: {total_palabras}")
    return {
        "categorias": categorias_organizadas,
        "total_palabras": total_palabras,
        "total_categorias": len(categorias_organizadas)
    }

@router.get("/learn-data")
async def obtener_datos_completos_learn():
    if not datos_palabras:
        raise HTTPException(status_code=500, detail="Datos no disponibles")

    total_categorias = len(datos_palabras)
    total_subcategorias = 0
    total_palabras = 0
    categorias_resumen = []

    for categoria_nombre, categoria_data in datos_palabras.items():
        if isinstance(categoria_data, dict):
            subcategorias_count = len(categoria_data)
            palabras_count = 0
            for subcategoria_data in categoria_data.values():
                if isinstance(subcategoria_data, list):
                    palabras_count += len(subcategoria_data)
            total_subcategorias += subcategorias_count
            total_palabras += palabras_count
            categorias_resumen.append({
                "nombre": categoria_nombre,
                "total_subcategorias": subcategorias_count,
                "total_palabras": palabras_count,
                "es_dificil": categoria_nombre == "Categoria Dificil"
            })

    print(f"[busqueda] Learn-data solicitado | Categorías: {total_categorias} | Palabras: {total_palabras}")
    return {
        "datos_completos": datos_palabras,
        "categorias": categorias_resumen,
        "estadisticas": {
            "total_categorias": total_categorias,
            "total_subcategorias": total_subcategorias,
            "total_palabras": total_palabras
        }
    }