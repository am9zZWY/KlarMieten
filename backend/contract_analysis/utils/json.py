import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

def model_to_json_schema(model_class):
    # Get model fields
    fields = model_class._meta.get_fields()

    schema = {}

    for field in fields:
        # Skip relation fields like ForeignKey
        if field.is_relation:
            continue

        # Get field type
        if hasattr(field, 'get_internal_type'):
            field_type = field.get_internal_type()

            # Map Django field types to JSON schema types
            if field_type in ['CharField', 'TextField', 'EmailField', 'URLField']:
                schema[field.name] = "string"
            elif field_type in ['IntegerField', 'PositiveIntegerField', 'SmallIntegerField']:
                schema[field.name] = "integer"
            elif field_type in ['DecimalField', 'FloatField']:
                schema[field.name] = "decimal"
            elif field_type == 'BooleanField':
                schema[field.name] = "boolean"
            elif field_type == 'DateField':
                schema[field.name] = "date"
            elif field_type == 'DateTimeField':
                schema[field.name] = "datetime"
            else:
                schema[field.name] = "string"  # Default to string for unknown types

    return schema


def clean_json(json_string: str) -> Any | None:
    """
    Cleans a JSON string received, ensuring it's valid JSON,
    and returns it as a Python dictionary.  Handles common issues like
    trailing commas, unescaped characters, and incorrect data types.

    Args:
        json_string: The JSON string to clean.

    Returns:
        A Python dictionary representing the cleaned JSON, or None if cleaning failed.
    """
    if not json_string:
        return None

    try:
        # Attempt to load the JSON string directly
        data = json.loads(json_string)
        return data  # If it loads without error, it's already valid.

    except json.JSONDecodeError as e:
        logger.error(f"Initial JSONDecodeError: {e}")

        # Attempt cleaning strategies:
        cleaned_string = json_string
        cleaned_string = cleaned_string.replace(",\n}", "\n}")
        cleaned_string = cleaned_string.replace(",\n]", "\n]")
        cleaned_string = cleaned_string.replace("'", '"')
        cleaned_string = cleaned_string.replace("```json", "")
        cleaned_string = cleaned_string.replace("```", "")
        cleaned_string = cleaned_string.replace("True", "true")
        cleaned_string = cleaned_string.replace("False", "false")
        cleaned_string = cleaned_string.replace("Null", "null")

        # 4. Try loading the cleaned string again
        try:
            data = json.loads(cleaned_string)
            return data
        except json.JSONDecodeError as e2:
            logger.error(f"Failed to clean JSON: {e2}")
            return None
