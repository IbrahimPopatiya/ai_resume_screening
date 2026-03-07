def normalize_message(message) -> str:
    if isinstance(message, dict):
        return message.get("content", "")
    if isinstance(message, str):
        return message
    return ""
