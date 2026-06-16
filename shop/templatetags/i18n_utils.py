# shop/templatetags/i18n_utils.py
from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag(takes_context=True)
def change_lang_url(context, lang_code: str) -> str:
    """
    Return the current URL with the language prefix replaced by *lang_code*.
    If the target language is the default language, the prefix is removed.
    """
    request = context.get("request")
    if request is None:
        return "/"

    path = request.path_info  # путь без домена, например /en/video-walls/

    # Убираем существующий языковой префикс, если он есть
    current_lang = request.LANGUAGE_CODE
    if current_lang != settings.LANGUAGE_CODE and path.startswith(f"/{current_lang}/"):
        path = path[len(f"/{current_lang}"):] or "/"
    elif current_lang == settings.LANGUAGE_CODE and not any(
        path.startswith(f"/{lang}/") for lang, _ in settings.LANGUAGES
    ):
        # Без префикса — уже язык по умолчанию
        pass
    else:
        # На всякий случай убираем любой известный префикс
        for lang, _ in settings.LANGUAGES:
            if lang != settings.LANGUAGE_CODE and path.startswith(f"/{lang}/"):
                path = path[len(f"/{lang}"):] or "/"
                break

    # Собираем новый путь
    if lang_code == settings.LANGUAGE_CODE:
        return path
    else:
        return f"/{lang_code}{path}"
