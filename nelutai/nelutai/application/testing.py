import json
from typing import Mapping

from nelutai.application.helpers import RequestHandler
from nelutai.domain.conversation import Conversation
from nelutai.domain.enums import State
from nelutai.domain.handlers import handle_message


def _get_testing_sender(body, _) -> str:
    return 'fixed'


RequestHandler(_get_testing_sender)


async def handle_application_request(
    conversation: Conversation, raw: bytes | str, additional: Mapping[str, str]
) -> str:
    if conversation.state == State.WELCOME:
        msg = ''
    else:
        msg = json.loads(raw)['message']

    resp = handle_message(conversation, msg)
    return resp.message
