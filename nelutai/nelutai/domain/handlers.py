import pandas as pd
from unidecode import unidecode
from ..constants import Constants

from .ask import ask_question
from .ask_freeform import ask_question as ask_question_freeform
from .conversation import Conversation
from .enums import State
from .response import Response


def _normalize_text(text: str) -> str:
    return unidecode(text.lower())


def finish_conversation_wrapper(handler):
    def wrapper(
        context: Conversation,
        message: str,
        cities: pd.DataFrame = None,
        cities_with_tags: pd.DataFrame = None,
    ):

        if [
            fc
            for fc in Constants.finish_conversation
            if fc.lower() in message.lower()
        ]:
            response = Constants.finish_conversation_message
            context.message_history += [message, response]
            context.state = State.ENDED
            return Response(message=response)
        else:
            return handler(context, message, cities, cities_with_tags)

    return wrapper


def change_location_wrapper(handler):
    def wrapper(
        context: Conversation,
        message: str,
        cities: pd.DataFrame = None,
        cities_with_tags: pd.DataFrame = None,
    ):
        if message == Constants.change_location:
            response = Constants.change_location_message
            context.state = State.ASKED_LOCATION
            return Response(message=response)
        else:
            return handler(context, message, cities, cities_with_tags)

    return wrapper


def change_interests_wrapper(handler):
    def wrapper(
        context: Conversation,
        message: str,
        cities: pd.DataFrame = None,
        cities_with_tags: pd.DataFrame = None,
    ):
        if message == Constants.change_interests:
            response = Constants.change_interests_message.format(
                city=context.location
            )
            city = _normalize_text(context.location)
            options = list(
                cities_with_tags[cities_with_tags['city'] == city]['tag']
            )
            context.state = State.ASKED_INTERESTS
            return Response(message=response, options=options)
        else:
            return handler(context, message, cities, cities_with_tags)

    return wrapper


def welcome(
    context: Conversation,
    message: str,
    cities: pd.DataFrame = None,
    cities_with_tags: pd.DataFrame = None,
) -> Response:
    response = Constants.welcome_message
    formatted_cities = ', '.join([c.title() for c in cities['city'].values])
    context.state = State.ASKED_LOCATION
    return Response(message=response.format(cities = formatted_cities))


@finish_conversation_wrapper
@change_location_wrapper
def ask_interests(
    context: Conversation,
    message: str,
    cities: pd.DataFrame = None,
    cities_with_tags: pd.DataFrame = None,
) -> Response:
    normalized_message = _normalize_text(message)
    options = []
    response = Constants.interests_message
    for city in cities['city'].values:
        if city in normalized_message:
            context.location = city.capitalize()
            context.state = State.ASKED_INTERESTS
            options = list(
                cities_with_tags[cities_with_tags['city'] == city]['tag']
            )
            break
    if not options:
        response = Constants.city_not_found_message
    return Response(message=response, options=options)


@finish_conversation_wrapper
@change_location_wrapper
@change_interests_wrapper
def free_form(
    context: Conversation,
    message: str,
    cities: pd.DataFrame = None,
    cities_with_tags: pd.DataFrame = None,
) -> Response:
    if context.state == State.ASKED_INTERESTS:
        context.category = str.lower(message)
        response = ask_question(context)
    else:
        response = ask_question_freeform(context, message)
    context.state = State.FREE_FORM
    return Response(message=response)


def handle_message(
    context: Conversation,
    message: str,
    cities: pd.DataFrame = None,
    cities_with_tags: pd.DataFrame = None,
) -> Response:
    handlers = {
        State.WELCOME: welcome,
        State.ASKED_LOCATION: ask_interests,
        State.ASKED_INTERESTS: free_form,
        State.FREE_FORM: free_form,
    }
    return handlers[context.state](context, message, cities, cities_with_tags)
