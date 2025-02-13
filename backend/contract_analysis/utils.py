from datetime import datetime


def get_nested(data, keys, default=None):
    """
    Safely retrieves a nested value from a dictionary using a list of keys.
    Returns the default value if any key is not found.
    """
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data


def convert_date(date_str):
    """
    Converts a date string in the format "YYYY-MM-DD" to a datetime object.
    """
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None
