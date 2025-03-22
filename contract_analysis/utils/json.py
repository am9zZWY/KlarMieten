import json
import logging
import re
from typing import Any

from django.db import models

logger = logging.getLogger(__name__)


def model_to_schema(model_class, exclude=None):
    fields = model_class._meta.get_fields()
    schema = {}

    for field in fields:
        # Skip primary keys (IDs) and relation fields (Foreign Keys)
        if field.primary_key or field.is_relation or not hasattr(field, 'get_internal_type'):
            continue

        field_type = field.get_internal_type()
        field_name = field.name

        # Skip excluded fields
        if exclude and field_name in exclude:
            continue

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
    and returns it as a Python dictionary.
    """
    if not json_string:
        return None

    # Remove markdown code block markers first
    if "" in json_string:
        pattern = r"(?:json)?(.*?)```"
        matches = re.findall(pattern, json_string, re.DOTALL)
        if matches:
            json_string = matches[0].strip()

    try:
        # Use json.loads directly
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")

        # Try with a more lenient parser for recovery
        try:
            return json.loads(json_string.replace("'", '"')
                              .replace("True", "true")
                              .replace("False", "false")
                              .replace("None", "null"))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to clean JSON after attempts")
            return None
