from enum import IntEnum


class State(IntEnum):
    WELCOME = 0
    ASKED_LOCATION = 1
    ASKED_INTERESTS = 2
    FREE_FORM = 3
    ENDED = 4
