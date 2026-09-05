from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.exceptions import DomainException

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainException)
    async def domain_handler(req: Request, exc: DomainException):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.message})
