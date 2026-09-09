"""Small validators for fields permitted in public telemetry."""

import re


def object_value(value):
    if not isinstance(value, dict):
        raise ValueError("expected object")
    return value


def text(value, pattern):
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError("invalid public text field")
    return value


def integer(value):
    if type(value) is not int or value < 1:
        raise ValueError("expected positive integer")
    return value


def choice(value, allowed):
    if value not in allowed:
        raise ValueError("unsupported public field value")
    return value


def exact_keys(value, keys):
    if set(object_value(value)) != set(keys):
        raise ValueError("unexpected or missing public fields")


def timestamp(value):
    if value is None:
        return None
    return text(value, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
