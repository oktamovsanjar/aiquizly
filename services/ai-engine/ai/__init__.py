from .validator import validate_questions

__all__ = ["AIStructurer", "validate_questions"]


def __getattr__(name: str):
    if name == "AIStructurer":
        from .structurer import AIStructurer
        return AIStructurer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
