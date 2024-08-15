import os
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings


def get_llm(temp: float, max_tokens: int) -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT'],
        azure_deployment=os.environ['AZURE_OPENAI_DEPLOYMENT_NAME'],
        openai_api_version=os.environ['AZURE_OPENAI_API_VERSION'],
        temperature=temp,
        max_tokens=max_tokens,
    )


def get_embeddings() -> AzureOpenAIEmbeddings:
    return AzureOpenAIEmbeddings(
        azure_deployment=os.environ['AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDINGS'],
        openai_api_version=os.environ['AZURE_OPENAI_API_VERSION_EMBEDDINGS'],
    )
