# models.py
import os
import uuid
import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db import models

from .utils import validate_file_size, validate_file_type


User = get_user_model()

logger = logging.getLogger(__name__)

class Contract(models.Model):
    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("processing", "Processing"),
        ("analyzed", "Analyzed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploaded")
    ai_model_version = models.CharField(max_length=20)

    def save(self, *args, **kwargs):
        if self.pk:
            logger.info(f"Updating Contract {self.pk} for user {self.user}")
        else:
            logger.info(f"Creating new Contract for user {self.user}")
        super().save(*args, **kwargs)


class ContractFile(models.Model):
    def get_file_path(instance, filename):
        ext = filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        return os.path.join("contracts", filename)

    contract = models.ForeignKey(
        "Contract", on_delete=models.CASCADE, related_name="files"
    )
    file_name = models.CharField(max_length=255, blank=True, default="")
    contract_file = models.FileField(
        upload_to=get_file_path, validators=[validate_file_size, validate_file_type]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            logger.info(f"Updating ContractFile {self.pk} for contract {self.contract}")
        else:
            logger.info(f"Creating new ContractFile for contract {self.contract}")
        super().save(*args, **kwargs)


class ContractDetails(models.Model):
    contract = models.ForeignKey(
        "Contract", on_delete=models.CASCADE, related_name="details"
    )
    contract_type = models.CharField(
        max_length=50, blank=True
    )  # e.g., "Wohnraummietvertrag"

    # Property Details
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    number_of_rooms = models.IntegerField(null=True, blank=True, default=0)
    kitchen = models.BooleanField(default=False)
    bathroom = models.BooleanField(default=False)
    separate_wc = models.BooleanField(default=False)
    balcony_or_terrace = models.BooleanField(default=False)
    garden = models.BooleanField(default=False)
    garage_or_parking_space = models.BooleanField(default=False)

    # Shared Facilities
    shared_facilities = models.TextField(
        blank=True
    )  # Comma-separated list of shared facilities

    # Keys Provided
    keys_provided = models.TextField(
        blank=True
    )  # Comma-separated list of keys provided

    # Rental Terms
    start_date = models.DateField(null=True, blank=True, default=None)
    end_date = models.DateField(
        null=True,
        blank=True,
        default=None,
        help_text="Leave blank for unlimited contracts",
    )
    duration = models.CharField(max_length=50, blank=True, null=True)
    termination_terms = models.TextField(blank=True, null=True)

    # Pricing
    monthly_rent = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    additional_costs = models.TextField(
        blank=True, null=True
    )  # Comma-separated list of additional costs
    total_rent = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Heating Type
    heating_type = models.CharField(
        max_length=50, blank=True, null=True
    )  # e.g., "Etagenheizung"

    # Additional Clauses
    additional_clauses = models.TextField(
        blank=True, null=True
    )  # Comma-separated list of additional clauses

    # Paragraphs
    paragraphs = models.TextField(
        blank=True, null=True
    )  # Store all paragraphs as a single text block

    def __str__(self):
        return f"Contract Details for {self.contract}"

    def save(self, *args, **kwargs):
        if self.pk:
            logger.info(f"Updating ContractDetails {self.pk} for contract {self.contract}")
        else:
            logger.info(f"Creating new ContractDetails for contract {self.contract}")
        super().save(*args, **kwargs)


class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    stripe_subscription_id = models.CharField(max_length=255)
    status = models.CharField(max_length=20)
    current_period_end = models.DateTimeField()

    def save(self, *args, **kwargs):
        if self.pk:
            logger.info(f"Updating Subscription {self.pk} for user {self.user}")
        else:
            logger.info(f"Creating new Subscription for user {self.user}")
        super().save(*args, **kwargs)


class PaymentHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            logger.info(f"Updating PaymentHistory {self.pk} for user {self.user}")
        else:
            logger.info(f"Creating new PaymentHistory for user {self.user}")
        super().save(*args, **kwargs)
