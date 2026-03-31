from fastapi import APIRouter, UploadFile, Form, File, HTTPException
import boto3
import os
import uuid
import asyncpg
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/donacion", tags=["Donación de Señas"])


async def get_db_connection():
    return await asyncpg.connect(os.getenv("DATABASE_URL"))


@router.post("/subir")
async def subir_donacion(
    nombre: str = Form(...),
    correo: str = Form(...),
    dni: str = Form(...),
    telefono: str = Form(...),
    sena: str = Form(...),
    ciudad: str = Form(...),
    firma_base64: str = Form(...),
    video: UploadFile = File(...),
):

    if not os.getenv("MINIO_BUCKET_NAME") or not os.getenv("DATABASE_URL"):
        print(
            "Aviso: Intento de uso de /donacion/subir, pero las credenciales locales no están configuradas. Módulo desactivado."
        )
        return {
            "status": "construccion",
            "message": "El módulo de donación no tiene las credenciales configuradas en el servidor.",
            "archivo_video": None,
        }

    try:
        BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME")

        s3_client = boto3.client(
            "s3",
            endpoint_url=os.getenv("MINIO_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("MINIO_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("MINIO_SECRET_KEY"),
        )

        contenido_video = await video.read()

        extension = video.filename.split(".")[-1]
        nombre_archivo = f"{dni}_{uuid.uuid4().hex[:8]}.{extension}"
        ruta_minio = f"videos/{nombre_archivo}"

        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=ruta_minio,
            Body=contenido_video,
            ContentType=video.content_type,
        )

        conn = await get_db_connection()
        try:
            query = """
                INSERT INTO donaciones (nombre, correo, dni, telefono, sena, ciudad, firma_base64, video_url) 
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            await conn.execute(
                query,
                nombre,
                correo,
                dni,
                telefono,
                sena,
                ciudad,
                firma_base64,
                ruta_minio,
            )
        finally:
            await conn.close()

        print(
            "--- NUEVA DONACIÓN RECIBIDA, SUBIDA A MINIO Y GUARDADA EN POSTGRESQL ---"
        )

        print(
            f"Usuario: {nombre} | DNI: {dni} | Ciudad: {ciudad} | Seña: {sena} | Video: {ruta_minio}"
        )

        return {
            "status": "success",
            "message": "Datos guardados en PostgreSQL y video en MinIO exitosamente",
            "archivo_video": ruta_minio,
        }

    except Exception as e:
        print(f"Error al procesar donación: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al procesar el archivo y los datos: {str(e)}",
        )


@router.get("/listar")
async def listar_donaciones():
    if not os.getenv("DATABASE_URL"):
        return {
            "status": "construccion",
            "total": 0,
            "donaciones": [],
            "message": "Credenciales de PostgreSQL no configuradas.",
        }

    try:
        conn = await get_db_connection()
        try:
            query = "SELECT id, nombre, correo, dni, telefono, sena, ciudad, video_url, fecha FROM donaciones ORDER BY fecha DESC"

            registros = await conn.fetch(query)

            donaciones = [dict(registro) for registro in registros]

        finally:
            await conn.close()

        return {"status": "success", "total": len(donaciones), "donaciones": donaciones}

    except Exception as e:
        print(f"Error al listar: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno al consultar la base de datos PostgreSQL",
        )
