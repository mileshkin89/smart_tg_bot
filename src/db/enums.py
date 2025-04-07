from enum import Enum


class SessionMode(Enum):

    RANDOM = "random"
    GPT = "gpt"
    TALK, CHOOSE_PERSONALITY = "talk", "choose"
    QUIZ = "quiz"
    TRANSLATE = "translate"
    RESUME = "resume"


class MessageRole(Enum):

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"