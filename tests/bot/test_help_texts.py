from pybot.presentation.texts import HELP_GROUP, HELP_PRIVATE, HELP_PRIVATE_PUBLIC


HELP_PAGE_BLOCK = (
    "Подробная инструкция по использованию бота:\nhttps://cewerty.github.io/PyBot-ITAcadem/user-guide/how-to-use-bot/"
)


def test_help_private_contains_roles_command() -> None:
    assert "/roles - показать все роли в системе" in HELP_PRIVATE


def test_help_private_contains_showroles_command() -> None:
    assert "/showroles [@user|id|reply] - показать роли пользователя" in HELP_PRIVATE


def test_help_private_public_contains_roles_command() -> None:
    assert "/roles - показать все роли в системе" in HELP_PRIVATE_PUBLIC


def test_help_private_public_contains_showroles_command() -> None:
    assert "/showroles [@user|id|reply] - показать роли пользователя" in HELP_PRIVATE_PUBLIC


def test_help_group_contains_roles_command() -> None:
    assert "/roles - показать все роли в системе" in HELP_GROUP


def test_help_group_contains_showroles_command() -> None:
    assert "/showroles [@user|id|reply] - показать роли пользователя" in HELP_GROUP


def test_help_private_contains_docs_link_block() -> None:
    assert HELP_PAGE_BLOCK in HELP_PRIVATE


def test_help_private_public_contains_docs_link_block() -> None:
    assert HELP_PAGE_BLOCK in HELP_PRIVATE_PUBLIC


def test_help_group_contains_docs_link_block() -> None:
    assert HELP_PAGE_BLOCK in HELP_GROUP
