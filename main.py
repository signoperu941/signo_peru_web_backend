from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from routers import busqueda, video
import os
import socket
from datetime import datetime

# RATE LIMITING
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

def get_real_ip(request: Request):
    return request.headers.get("cf-connecting-ip", request.headers.get("x-forwarded-for", request.client.host))

# Máximo 60 peticiones por minuto por IP
limiter = Limiter(key_func=get_real_ip, default_limits=["60/minute"])

# ESCUDO DE TAMAÑO DE ARCHIVOS (PAYLOAD LIMIT)
class LimitUploadSize(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int):
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        if request.method == 'POST':
            if 'content-length' in request.headers:
                content_length = int(request.headers['content-length'])
                if content_length > self.max_upload_size:
                    return Response(
                        content="Payload Too Large: El video excede el límite permitido de 10MB.", 
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                    )
        return await call_next(request)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ruta_videos = os.path.join(BASE_DIR, "public", "videos")

app = FastAPI(
    title="LSP Backend API",
    version="4.0.0",
    description="API para la aplicacion de Lengua de Senas Peruana - Modelo local 137 clases",
)

# APLICAR RATE LIMITING EN FASTAPI
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# APLICAR LÍMITE DE TAMAÑO (10 MB = 10 * 1024 * 1024 bytes)
app.add_middleware(LimitUploadSize, max_upload_size=10_485_760)

# CONFIGURACIÓN CORS
# Borrar las URLs temporales y colocar Ssolo el dominio final.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://signo-peru-web-dun.vercel.app",
        "https://signo-peru-web-cesar424s-projects.vercel.app",
        "https://api.buenfeps.site"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists(ruta_videos):
    app.mount("/videos", StaticFiles(directory=ruta_videos), name="videos")
    print(f" Carpeta de videos conectada exitosamente: {ruta_videos}")
else:
    print(f" ERROR: No se encontró la carpeta en: {ruta_videos}")

# Incluir routers
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
            "videos": "/videos"
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