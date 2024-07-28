import os
from functools import cache
from typing import Dict, List, Mapping, Tuple

import pandas as pd
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.event_type import EventType
from viberbot.api.messages import TextMessage
from viberbot.api.viber_requests import (ViberConversationStartedRequest,
                                         ViberMessageRequest, ViberRequest)

from nelutai.application.exceptions import NotAuthorizedError
from nelutai.application.helpers import RequestHandler
from nelutai.domain.conversation import Conversation
from nelutai.domain.enums import State
from nelutai.domain.handlers import handle_message
from ..constants import Constants

bot_configuration = BotConfiguration(
    name=Constants.bot_name,
    avatar=Constants.avatar_url,
    auth_token=os.environ['VIBER_AUTH_TOKEN'],
)
viber = Api(bot_configuration)


def get_btn(cols: int, text: str, rows: int = 1) -> Dict:
    return {
        'Columns': cols,
        'Rows': rows,
        'BgColor': '#e6f5ff',
        'TextSize': 'large',
        'ActionType': 'reply',
        'ActionBody': text,
        'ReplyType': 'message',
        'Text': text,
    }


def get_keyboard(
    options: List[str], old_state: State, new_state: State
) -> Dict:
    options = options or []
    should_double_last = len(options) % 2 == 1
    if old_state == State.WELCOME or new_state == State.ENDED:
        return None
    additional_buttons = []
    if new_state > State.ASKED_LOCATION:
        additional_buttons.append(get_btn(6, Constants.change_location))
    if new_state > State.ASKED_INTERESTS:
        additional_buttons.append(get_btn(6, Constants.change_interests))
    additional_buttons.append(get_btn(6, Constants.finish_conversation))
    return {
        'Type': 'keyboard',
        'BgColor': '#FFFFFF',
        'InputFieldState': 'hidden' if options else 'regular',
        'Buttons': [
            get_btn(
                6 if should_double_last and ind == len(options) - 1 else 3,
                option.capitalize(),
            )
            for ind, option in enumerate(options)
        ]
        + additional_buttons
    }


def _get_viber_sender(body: Dict, _: Dict) -> str:
    if 'user_id' in body:
        return body['user_id']
    elif 'user' in body:
        return body['user']['id']
    elif 'sender' in body:
        return body['sender']['id']
    else:
        return 'webhook'


@cache
def get_cities_metadata() -> Tuple[pd.DataFrame, pd.DataFrame]:
    return pd.read_csv('/chromadb/cities.csv', sep=';'), pd.read_csv(
        '/chromadb/cities_with_tags.csv', sep=';'
    )


def is_webhook(parsed: ViberRequest) -> bool:
    return parsed.event_type == EventType.WEBHOOK


def is_wrong_type(parsed: ViberRequest) -> bool:
    is_welcome_request = isinstance(parsed, ViberConversationStartedRequest)
    is_message_request = isinstance(parsed, ViberMessageRequest)
    return not is_welcome_request and not is_message_request


def is_duplicate(parsed: ViberRequest, conversation: Conversation) -> bool:
    return parsed.message_token in conversation.message_ids


def is_message_invalid(
    parsed: ViberRequest, conversation: Conversation
) -> bool:
    return (
        is_webhook(parsed)
        or is_wrong_type(parsed)
        or is_duplicate(parsed, conversation)
    )


@RequestHandler(_get_viber_sender)
async def handle_application_request(
    conversation: Conversation, raw: bytes | str, additional: Mapping[str, str]
) -> str:
    if not viber.verify_signature(
        raw, additional['X-Viber-Content-Signature']
    ):
        raise NotAuthorizedError()
    cities, cities_with_tags = get_cities_metadata()
    parsed: ViberRequest = viber.parse_request(raw)
    if is_message_invalid(parsed, conversation):
        return ''

    is_welcome_request = isinstance(parsed, ViberConversationStartedRequest)
    conversation.message_ids += [parsed.message_token]
    input_message = ''

    if is_welcome_request:
        conversation.reset()
    else:
        input_message = parsed.message.text

    old_state = conversation.state
    resp = handle_message(
        conversation, input_message, cities, cities_with_tags
    )
    new_state = conversation.state

    viber_message = TextMessage(
        text=resp.message,
        keyboard=get_keyboard(resp.options, old_state, new_state),
        min_api_version=4,
    )
    viber.send_messages(conversation.user_id, [viber_message])
    return resp.message
