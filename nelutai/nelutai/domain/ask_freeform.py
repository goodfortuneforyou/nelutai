from langchain.chains import create_history_aware_retriever
from langchain.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough

from nelutai.domain.conversation import Conversation
from nelutai.domain.ask_shared import get_llm, get_embeddings


def format_docs(docs):
    return '\n\n'.join(doc.page_content for doc in docs)


def load_retriever(category, embeddings):
    folders = {
        'events': '/chromadb/events/chroma',
        'accomodations': '/chromadb/accomodations/chroma',
        'restaurants': '/chromadb/restaurants/chroma',
        'landmarks': '/chromadb/landmarks/chroma',
    }
    index_path = folders[category]
    vectordb = Chroma(
        persist_directory=index_path, embedding_function=embeddings
    )
    retriever = vectordb.as_retriever(search_kwargs={'k': 5})
    return retriever


def load_history_retriever(llm, retriever):
    contextualize_q_system_prompt = (
        'Given a chat history and the latest user question '
        'which might reference context in the chat history, '
        'formulate a standalone question which can be understood '
        'without the chat history. Do NOT answer the question, '
        'just reformulate it if needed and otherwise return it as is.'
    )
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ('system', contextualize_q_system_prompt),
            MessagesPlaceholder('chat_history'),
            ('human', '{input}'),
        ]
    )

    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )
    return history_aware_retriever


def format_chat_history(chat_history):
    formatted_messages = [
        f'{message[0]}: {message[1]}'
        for message in chat_history[-6:]
        if message[0] != 'system'
    ]
    combined_messages = '\n'.join(formatted_messages)
    return combined_messages


def generate_additional_response(
    llm, history_aware_retriever, chat_history, question, location
):
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                'system',
                'You are an AI assistant that answers the questions based on a context provided.',
            ),
            (
                'user',
                "###User's Question: {question}\n###Context: {context}\n###Instructions: Make sure to generate an answer according to the location provided in the question.\n###Answer:",
            ),
        ]
    )

    docs = history_aware_retriever.invoke(
        {'input': question, 'chat_history': chat_history}
    )

    context = format_docs(docs)

    formatted_chat_history = format_chat_history(chat_history)
    rag_chain = (
        {
            'context': lambda _: context,
            'question': RunnablePassthrough(),
            'history': lambda _: formatted_chat_history,
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    response = rag_chain.invoke(f'{location} {question}')

    return response


def ask_question(conversation: Conversation, message: str) -> str:
    llm = get_llm(0.2, 512)
    embeddings = get_embeddings()

    retriever = load_retriever(conversation.category, embeddings)
    history_aware_retriever = load_history_retriever(llm, retriever)
    response = generate_additional_response(
        llm,
        history_aware_retriever,
        conversation.message_history,
        message,
        conversation.location,
    )
    conversation.message_history += [('user', message), ('ai', response)]
    return response
