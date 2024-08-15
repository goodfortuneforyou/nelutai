import json
import os

from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route

from nelutai.application.testing import (
    handle_application_request as testing_handler,
)
from nelutai.application.viber import (
    handle_application_request as viber_handler,
)


async def handle_request(request: Request):
    raw = await request.body()
    print('The request body was', json.loads(raw))
    task = None
    if os.environ['HANDLER'] == 'testing':
        task = BackgroundTask(testing_handler, raw, request.headers)
    elif os.environ['HANDLER'] == 'viber':
        task = BackgroundTask(viber_handler, raw, request.headers)
    return HTMLResponse(status_code=200, background=task)


app = Starlette(
    debug=True, routes=[Route('/', handle_request, methods=['POST'])]
)
