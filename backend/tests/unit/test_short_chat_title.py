from src.services.chat import short_chat_title


def test_short_chat_title_uses_three_to_four_words() -> None:
    assert short_chat_title("what are present in this heading Non-negotiable") == (
        "what are present in"
    )
    assert short_chat_title("Hello world friends") == "Hello world friends"
    assert short_chat_title("Hi") == "Hi"
    assert short_chat_title("  ") == "New chat"
