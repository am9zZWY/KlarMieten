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
