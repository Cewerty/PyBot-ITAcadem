import pytest

from pybot.utils import telegram_user_link


def test_telegram_user_link_uses_fallback_label_by_default() -> None:
    result = telegram_user_link(123_456_789)

    assert result == "<a href='tg://user?id=123456789'>Пользователь</a>"


def test_telegram_user_link_uses_first_name_and_last_name_when_provided() -> None:
    result = telegram_user_link(123_456_789, first_name="Иван", last_name="Иванов")

    assert result == "<a href='tg://user?id=123456789'>Иван Иванов</a>"


def test_telegram_user_link_escapes_html_in_label() -> None:
    result = telegram_user_link(123_456_789, first_name="<Иван>", last_name="& Иванов")

    assert result == "<a href='tg://user?id=123456789'>&lt;Иван&gt; &amp; Иванов</a>"


def test_telegram_user_link_uses_fallback_label_when_name_parts_are_blank() -> None:
    result = telegram_user_link(
        123_456_789,
        first_name="   ",
        last_name="",
        fallback_label="Участник",
    )

    assert result == "<a href='tg://user?id=123456789'>Участник</a>"


def test_telegram_user_link_rejects_non_positive_user_id() -> None:
    with pytest.raises(ValueError, match="greater than 0"):
        telegram_user_link(0)
