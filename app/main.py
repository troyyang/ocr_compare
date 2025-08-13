import asyncio
import os
import sys
import json
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

import core.config as config
from core.error_handle import register_exception
from core.extends_logger import logger
from core.i18n import LanguageMiddleware
from core.middleware import NamingConventionMiddleware
from routers import register_router
from fastapi import WebSocket, WebSocketDisconnect, Depends, Request
from services.document_service import DocumentService
import traceback
from core.middleware import validate_token

def get_document_service():
    return DocumentService()

# Lifespan and other functions remain the same
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for setup and cleanup of resources"""
    try:
        logger.info("Application startup")
        yield
        logger.info("Application shutdown initiated")
    finally:
        pass
            
def create_app():

    current_app = FastAPI(
        title="Tech Document Management",
        description="Tech Document Management",
        version="0.1.0",
        contact={
            "name": "Troy Yang",
            "email": "troy.yang2@gmail.com",
        },
        lifespan=lifespan
    )

    # Configure CORS
    current_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    current_app.add_middleware(LanguageMiddleware)
    # the json key in request and response data will be converted to camelCase
    if config.IS_CAMEL_CASE:
        current_app.add_middleware(NamingConventionMiddleware)

    # Include routers
    register_router(current_app)

    register_exception(current_app)

    @current_app.get("/")
    async def read_root():
        return {"message": "Welcome to Law Document Analysis!"}

    @current_app.get("/download")
    async def download_file(storage_path: str):
        try:
            file_path = os.path.join(config.DATA_DIR, storage_path)
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")
            file_name = os.path.basename(file_path)
            headers = {
                'Content-Disposition': f'attachment; filename="{file_name}"'
            }
            return FileResponse(file_path, headers=headers)
        except Exception as e:
            logger.error(f"File download error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    
    @current_app.websocket("/app_ws")
    async def websocket_endpoint(websocket: WebSocket, document_service: DocumentService = Depends(get_document_service)):
        # await progress_manager.connect(websocket)
        await websocket.accept()
        from time import sleep 
        try:
            # Keep connection alive
            data = None
            while True:
                try:
                    # Wait for messages (ping/pong to keep connection alive)
                    data = await websocket.receive_json()
                    
                    if not data:
                        continue

                    token = data.get("token")
                    print("token: ", token)
                    user = await validate_token("Bearer " + token)
                    print("user: ", user)
                    await document_service.parse_doc_with_progress(websocket, data.get("doc_id"), user.get("userid"))
                    sleep(3)
                    # await websocket.send_text(json.dumps({"message": "progress", "data": data}))
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    traceback.print_exc()
                    logger.error(f"WebSocket error for document {data}: {e}")   
                    break
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected")
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")

    return current_app
app = create_app()

if __name__ == '__main__':
    # Add the current directory to the Python path
    root_path = os.getcwd()
    sys.path.append(root_path)
    # Run the FastAPI app
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=int(config.API_PORT),
        reload=False,               # close hot reload in production
        workers=config.APP_WORKERS, # use all available CPU cores
        log_level=config.APP_LOG_LEVEL,            # production environment use INFO level to reduce log noise
        timeout_keep_alive=5,        # quickly release idle Keep-Alive connections
        backlog=8192,                # increase pending connection queue capacity
        limit_concurrency=config.APP_LIMIT_CONCURRENCY,    # Optionally set maximum concurrency (default is unlimited)
        # http="h11",                # For HTTP/1.1 protocol, keep the default
        # proxy_headers=True,        # Enable if using reverse proxy
    )
