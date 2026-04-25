from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.services.order_service import InvalidOrderError


async def invalid_order_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)

    if isinstance(exc, InvalidOrderError):
        message = str(exc)
    else:
        message = "Invalid order"

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "INVALID_ORDER",
                "message": message,
                "request_id": request_id,
            }
        },
    )