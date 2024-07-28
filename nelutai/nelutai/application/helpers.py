import json
import os
import shutil
from datetime import datetime, timezone
from typing import Awaitable, Callable, Mapping

from azure.storage.blob import BlobClient, BlobServiceClient

from nelutai.domain.conversation import Conversation
from nelutai.domain.enums import State
from nelutai.constants import Constants


def _get_client(container_name: str, blob_name: str) -> BlobClient:
    account_name = os.environ['SA_NAME']
    account_key = os.environ['SA_KEY']
    blob_endpoint = os.environ['BLOB_ENDPOINT']
    connect_str = f'DefaultEndpointsProtocol=http;AccountName={account_name};AccountKey={account_key};BlobEndpoint={blob_endpoint};'

    blob_service = BlobServiceClient.from_connection_string(connect_str)

    return blob_service.get_blob_client(container_name, blob_name)


def get_blob_name(user: str) -> str:
    return f'{user}.json'


def get_conversation(user: str) -> Conversation:
    container_name = os.environ['SA_CONTAINER_CHATS']
    blob_client = _get_client(container_name, get_blob_name(user))
    if not blob_client.exists():
        conversation = Conversation(
            state=State.WELCOME,
            start=datetime.now(timezone.utc),
            message_history=[],
            message_ids=[],
            location=None,
            category=None,
            user_id=user,
        )
    else:
        conversation = Conversation.from_json(
            blob_client.download_blob().readall()
        )
    return conversation


def download_chroma():
    chroma_path = '/chromadb'
    if os.path.exists(chroma_path):
        return
    container_name = os.environ['SA_CONTAINER_CHROMA']
    blob_name = Constants.index_path
    blob_client = _get_client(container_name, blob_name)
    with open(blob_name, 'wb') as f:
        download_stream = blob_client.download_blob()
        f.write(download_stream.readall())
    shutil.unpack_archive(blob_name, chroma_path)


def update_conversation(conversation: Conversation):
    container_name = os.environ['SA_CONTAINER_CHATS']
    blob_client = _get_client(
        container_name, get_blob_name(conversation.user_id)
    )
    if conversation.state != State.ENDED:
        blob_client.upload_blob(conversation.to_json(), overwrite=True)
    else:
        blob_client.delete_blob()


class RequestHandler:
    def __init__(self, identity_function: Callable[[Mapping, Mapping], str]):
        self.identity_function = identity_function

    def __call__(
        self,
        handler: Callable[
            [Conversation, bytes | str, Mapping[str, str]], Awaitable[str]
        ],
    ):
        async def wrapper(raw: bytes | str, additional: Mapping[str, str]):
            user = self.identity_function(json.loads(raw), additional)
            conversation = get_conversation(user)
            resp = await handler(conversation, raw, additional)
            if resp:
                update_conversation(conversation)

        return wrapper


download_chroma()
