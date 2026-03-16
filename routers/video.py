from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import tempfile
import os
import httpx
import pathlib  # <--- Nueva importación para leer la extensión
from .modelo137 import process_video, predict

router = APIRouter(prefix="/video", tags=["Video Processing"])


@router.get("/stream")
async def stream_video(url: str):
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
            # Primera petición para obtener la cookie de confirmación
            response = await client.get(url)

            # Google Drive pide confirmación para archivos grandes
            if "virus scan warning" in response.text.lower() or "confirm" in str(
                response.url
            ):
                # Extrae el token de confirmación
                import re

                token_match = re.search(r"confirm=([0-9A-Za-z_-]+)", response.text)
                if token_match:
                    confirm_url = f"{url}&confirm={token_match.group(1)}"
                    response = await client.get(confirm_url)
                else:
                    # Intenta con uuid
                    uuid_match = re.search(r"uuid=([0-9A-Za-z_-]+)", response.text)
                    if uuid_match:
                        confirm_url = f"{url}&confirm=t&uuid={uuid_match.group(1)}"
                        response = await client.get(confirm_url)

            if response.status_code != 200:
                raise HTTPException(status_code=404, detail="Video no encontrado")

            return StreamingResponse(
                response.aiter_bytes(chunk_size=1024 * 64),
                media_type=response.headers.get("content-type", "video/mp4"),
                headers={
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "public, max-age=3600",
                },
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/predict")
def predict_sign(video: UploadFile = File(...)):
    temp_file = None
    try:
        content = video.file.read()
        print(f" Tamaño del video recibido: {len(content)} bytes")

        nombre_archivo = video.filename or "video.webm"
        ext = pathlib.Path(nombre_archivo).suffix
        if not ext:
            ext = ".webm"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            temp_file = tmp.name

        clip = process_video(temp_file)

        if clip is None:
            raise HTTPException(
                status_code=400,
                detail="No se pudieron extraer frames del video. Formato no soportado.",
            )

        result = predict(clip)
        top5 = result["top5"]

        return {
            "prediccion": top5[0]["palabra"],
            "conf_top5": result["conf_top5"],
            "certeza": result["certeza"],
            "top4": top5[1:],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
