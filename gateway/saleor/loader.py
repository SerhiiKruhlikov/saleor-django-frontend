# menu/graphql/loader.py
from pathlib import Path
from graphql import parse, Source, GraphQLSyntaxError
from functools import lru_cache


@lru_cache(maxsize=64)
def load_query(app_name: str, relative_path: str) -> str:
    base = Path(app_name) / "graphql"
    full_path = base / relative_path

    with open(full_path, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        parse(Source(source, str(full_path)))
    except GraphQLSyntaxError as e:
        raise ValueError(f"Ошибка синтаксиса в {full_path}: {e}")

    return source
