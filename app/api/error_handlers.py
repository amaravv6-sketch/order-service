from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.services.order_service import InvalidOrderError


async def invalid_order_exception_handler(
    request: Request,
    exc: InvalidOrderError,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "INVALID_ORDER",
                "message": str(exc),
                "request_id": request_id,
            }
        },
    )