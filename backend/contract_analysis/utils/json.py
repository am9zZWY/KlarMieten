import json
import logging
from typing import Any

from django.db import models

logger = logging.getLogger(__name__)

def model_to_schema(model_class):
    fields = model_class._meta.get_fields()
    schema = {}

    for field in fields:
        # Skip primary keys (IDs) and relation fields (Foreign Keys)
        if field.primary_key or field.is_relation or not hasattr(field, 'get_internal_type'):
            continue

        field_type = field.get_internal_type()
        field_name = field.name

        # Type mapping with null support
        if field_type in ['CharField', 'TextField', 'EmailField', 'URLField']:
            schema[field_name] = "string, null"
        elif field_type in ['IntegerField', 'PositiveIntegerField', 'SmallIntegerField']:
            schema[field_name] = "integer, null"
        elif field_type in ['DecimalField', 'FloatField']:
            schema[field_name] = "number, null"
        elif field_type == 'BooleanField':
            schema[field_name] = "boolean, null" if field.null else "boolean, false"
        elif field_type in ['DateField', 'DateTimeField', 'TimeField']:
            schema[field_name] = f"{field_type.lower().replace('field', '')}, null"
        else:
            schema[field_name] = "string, null"

    logger.info(f"Generated JSON schema for {model_class}: {schema}")
    return schema

def model_to_json_schema(model):
    """
    Convert a Django model to a JSON Schema representation
    """
    schema = {
        "type": "object",
        "title": model._meta.verbose_name.title(),
        "description": model.__doc__ or "",
        "properties": {},
        "required": []
    }

    # Process each field in the model
    for field in model._meta.fields:
        field_schema = field_to_schema(field)
        if field_schema:
            schema["properties"][field.name] = field_schema

            # Add to required fields if not nullable
            if not field.null and not field.blank and not isinstance(field, models.AutoField):
                schema["required"].append(field.name)

    return schema

def field_to_schema(field):
    """
    Convert a Django model field to a JSON Schema property definition
    """
    schema = {
        "title": field.verbose_name.title() if hasattr(field, 'verbose_name') else field.name.replace('_', ' ').title(),
        "description": field.help_text if field.help_text else ""
    }

    # Handle field nullability
    if field.null or field.blank:
        schema["nullable"] = True

    # Map Django field types to JSON Schema types
    if isinstance(field, models.AutoField):
        schema["type"] = "integer"
        schema["readOnly"] = True

    elif isinstance(field, models.CharField) or isinstance(field, models.TextField):
        schema["type"] = "string"
        if hasattr(field, 'max_length') and field.max_length:
            schema["maxLength"] = field.max_length

        # Handle choices
        if field.choices:
            schema["enum"] = [choice[0] for choice in field.choices]
            schema["enumNames"] = [choice[1] for choice in field.choices]

    elif isinstance(field, models.IntegerField) or isinstance(field, models.PositiveIntegerField):
        schema["type"] = "integer"
        if isinstance(field, models.PositiveIntegerField):
            schema["minimum"] = 0

    elif isinstance(field, models.BooleanField):
        schema["type"] = "boolean"
        schema["default"] = field.default

    elif isinstance(field, models.DateField):
        schema["type"] = "string"
        schema["format"] = "date"

    elif isinstance(field, models.TimeField):
        schema["type"] = "string"
        schema["format"] = "time"

    elif isinstance(field, models.DateTimeField):
        schema["type"] = "string"
        schema["format"] = "date-time"

    elif isinstance(field, models.DecimalField):
        schema["type"] = "number"
        schema["multipleOf"] = 10 ** (-field.decimal_places)
        if field.max_digits:
            # Calculate maximum based on max_digits and decimal_places
            max_val = 10 ** (field.max_digits - field.decimal_places) - 10 ** (-field.decimal_places)
            min_val = -max_val if not isinstance(field, models.PositiveIntegerField) else 0
            schema["maximum"] = max_val
            schema["minimum"] = min_val

    elif isinstance(field, models.ForeignKey):
        # For foreign keys, we just use the ID reference pattern
        schema["type"] = "integer"
        schema["description"] += f" (Foreign key to {field.related_model._meta.verbose_name})"

    else:
        # Fall back for other field types
        schema["type"] = "string"

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
