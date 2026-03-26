from fastapi import APIRouter, UploadFile, Form, File, HTTPException
import boto3
import os
import uuid
import httpx
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

router = APIRouter(prefix="/donacion", tags=["Donación de Señas"])


@router.post("/subir")
async def subir_donacion(
    nombre: str = Form(...),
    correo: str = Form(...),
    dni: str = Form(...),
    telefono: str = Form(...),
    sena: str = Form(...),
    firma_base64: str = Form(...),
    video: UploadFile = File(...),
):
    # VERIFICACIÓN DE DEGRADACIÓN
    # Si falta el Bucket de R2 o el Token de D1, el módulo se considera "Apagado"
    if not os.getenv("R2_BUCKET_NAME") or not os.getenv("CF_D1_API_TOKEN"):
        print(
            "Aviso: Intento de uso de /donacion/subir, pero las credenciales no están configuradas. Módulo desactivado."
        )
        return {
            "status": "construccion",
            "message": "El módulo de donación se encuentra en construcción o no tiene las credenciales configuradas en el servidor.",
            "archivo_r2": None,
        }

    try:
        # Cargar variables dinámicamente solo si pasaron el chequeo
        BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
        CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
        CF_DATABASE_ID = os.getenv("CF_DATABASE_ID")
        CF_D1_API_TOKEN = os.getenv("CF_D1_API_TOKEN")
        D1_QUERY_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/d1/database/{CF_DATABASE_ID}/query"

        # Inicializar el cliente S3 (R2) dinámicamente
        s3_client = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        )

        # Leer el contenido del video
        contenido_video = await video.read()

        # Generar un nombre único para el archivo
        extension = video.filename.split(".")[-1]
        nombre_archivo = f"{dni}_{uuid.uuid4().hex[:8]}.{extension}"
        ruta_r2 = f"videos/{nombre_archivo}"

        # Subir el video a Cloudflare R2
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=ruta_r2,
            Body=contenido_video,
            ContentType=video.content_type,
        )

        # GUARDAR LOS DATOS EN CLOUDFLARE D1
        headers = {
            "Authorization": f"Bearer {CF_D1_API_TOKEN}",
            "Content-Type": "application/json",
        }

        payload = {
            "sql": "INSERT INTO donaciones (nombre, correo, dni, telefono, sena, firma_base64, video_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
            "params": [nombre, correo, dni, telefono, sena, firma_base64, ruta_r2],
        }

        # Petición asíncrona a Cloudflare
        async with httpx.AsyncClient() as client:
            respuesta = await client.post(D1_QUERY_URL, headers=headers, json=payload)

            if respuesta.status_code != 200:
                print(f"Error HTTP de Cloudflare D1: {respuesta.text}")
                raise Exception("Fallo en la comunicación con la API de D1")

            datos_respuesta = respuesta.json()
            if not datos_respuesta.get("success"):
                errores = datos_respuesta.get("errors", [])
                print(f"Error lógico de Cloudflare D1: {errores}")
                raise Exception(f"D1 rechazó la consulta: {errores}")

        print(
            "--- NUEVA DONACIÓN RECIBIDA, SUBIDA A R2 Y GUARDADA EN CLOUDFLARE D1 ---"
        )
        print(f"Usuario: {nombre} | DNI: {dni} | Seña: {sena} | Video: {ruta_r2}")

        return {
            "status": "success",
            "message": "Datos guardados en D1 y video en R2 exitosamente",
            "archivo_r2": ruta_r2,
        }

    except Exception as e:
        print(f"Error al procesar donación: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al procesar el archivo y los datos: {str(e)}",
        )


@router.get("/listar")
async def listar_donaciones():
    # VERIFICACIÓN DE DEGRADACIÓN
    if not os.getenv("CF_D1_API_TOKEN"):
        return {
            "status": "construccion",
            "total": 0,
            "donaciones": [],
            "message": "Credenciales de D1 no configuradas.",
        }

    try:
        CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
        CF_DATABASE_ID = os.getenv("CF_DATABASE_ID")
        CF_D1_API_TOKEN = os.getenv("CF_D1_API_TOKEN")
        D1_QUERY_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/d1/database/{CF_DATABASE_ID}/query"

        headers = {
            "Authorization": f"Bearer {CF_D1_API_TOKEN}",
            "Content-Type": "application/json",
        }

        payload = {
            "sql": "SELECT id, nombre, correo, dni, telefono, sena, video_url, fecha FROM donaciones ORDER BY fecha DESC"
        }

        async with httpx.AsyncClient() as client:
            respuesta = await client.post(D1_QUERY_URL, headers=headers, json=payload)

            if respuesta.status_code != 200 or not respuesta.json().get("success"):
                raise Exception("Fallo al obtener datos de D1")

            datos_d1 = respuesta.json()
            donaciones = datos_d1["result"][0]["results"]

        return {"status": "success", "total": len(donaciones), "donaciones": donaciones}

    except Exception as e:
        print(f"Error al listar: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Error interno al consultar la base de datos D1"
        )
