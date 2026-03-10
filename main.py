from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import busqueda, video
import os
import socket
from datetime import datetime

app = FastAPI(
    title="LSP Backend API",
    version="4.0.0",
    description="API para la aplicacion de Lengua de Senas Peruana - Modelo local 137 clases",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(busqueda.router)
app.include_router(video.router)


@app.get("/")
async def root():
    return {
        "message": "API de Reconocimiento LSP funcionando correctamente",
        "version": "4.0.0",
        "host": socket.gethostname(),
        "datetime": datetime.now().isoformat(),
        "endpoints_disponibles": {
            "busqueda": "/busqueda/palabras-categorizadas",
            "prediccion": "/video/predict",
            "health": "/health",
            "documentacion": "/docs",
        },
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "LSP API",
        "version": "4.0.0",
        "host": socket.gethostname(),
        "port": int(os.environ.get("PORT", 8000)),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
    