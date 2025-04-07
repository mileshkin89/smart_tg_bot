from enum import Enum


class SessionMode(Enum):

    RANDOM = "random"
    GPT = "gpt"
    TALK = "talk"
    QUIZ = "quiz"
    TRANSLATE = "translate"
    RESUME = "resume"


class MessageRole(Enum):

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"