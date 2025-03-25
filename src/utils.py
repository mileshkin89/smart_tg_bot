from config import PATH_TO_MESSAGES


def load_massages(name: str) -> str:
    with open(PATH_TO_MESSAGES / f"{name}.txt", encoding="utf-8") as file:
        return file.read()


# print(load_massages("main"))