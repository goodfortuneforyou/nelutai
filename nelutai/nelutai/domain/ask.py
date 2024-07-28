from datetime import datetime

from langchain.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
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


def get_category_response(llm, retriever, location, category):
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                'system',
                'You are an AI assistant that answers the questions based on a context provided.',
            ),
            (
                'user',
                '###Question: {question}\n###Context: {context}\n###Instructions: Make sure to generate an answer according to the location provided in the question.\n###Answer:',
            ),
        ]
    )

    rag_chain = (
        {'context': retriever | format_docs, 'question': RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    query = f'{location} Give me a list of {category}.'
    if category == 'events':
        now = datetime.now()
        timestamp = f'Today is {now.day}.{now.month}.'
        query += f' {timestamp}'

    response = rag_chain.invoke(query)

    return query, response


def ask_question(conversation: Conversation) -> str:
    llm = get_llm(0.2, 512)
    embeddings = get_embeddings()

    retriever = load_retriever(conversation.category, embeddings)
    query, response = get_category_response(
        llm, retriever, conversation.location, conversation.category
    )
    conversation.message_history = [('user', query), ('ai', response)]
    return response
