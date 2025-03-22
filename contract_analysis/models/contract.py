# models.py
import logging
import tempfile
import uuid
from typing import List

from django.db import models

from accounts.models import User, Entitlement
from contract_analysis.utils.encryption import encrypt_file, decrypt_file

logger = logging.getLogger(__name__)


class Contract(models.Model):
    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("processing", "Processing"),
        ("analyzed", "Analyzed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    name = models.CharField(max_length=255, blank=True, default="Mietervertrag")
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploaded")

    archived = models.BooleanField(default=False)
    archived_date = models.DateTimeField(null=True, blank=True)

    retention_days = models.IntegerField(default=365)
    scheduled_deletion_date = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            logger.info(f"Updating Contract {self.pk} for user {self.user}")
        else:
            logger.info(f"Creating new Contract for user {self.user}")

        if not self.scheduled_deletion_date and self.retention_days:
            # Set deletion date based on retention period
            from datetime import datetime, timedelta

            self.scheduled_deletion_date = datetime.now().date() + timedelta(
                days=self.retention_days
            )

        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"Contract {self.id} for {self.user.username}"

    def get_details(self):
        """Get contract details object for contract."""
        # Check if details already exist
        contract_details = ContractDetails.objects.filter(contract=self).first()
        if not contract_details:
            contract_details = ContractDetails.objects.create(contract=self)

        return contract_details

    def get_images(self) -> List[str]:
        """Create temporary image files from contract files."""
        contract_files = self.files.all()
        temp_images = []

        for file in contract_files:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_file.write(file.get_file_content())
                temp_images.append(temp_file.name)

        return temp_images

    def add_file(self, filename, content, content_type):
        """Helper function to create and save a contract file with encrypted content."""
        contract_file = ContractFile.objects.create(
            contract=self,
            file_name=filename,
            file_type=content_type,
        )
        contract_file.set_file_content(content)
        contract_file.save()
        logger.info(f"File {filename} saved for contract {self.id}")
        return contract_file


class ContractFile(models.Model):
    contract = models.ForeignKey(
        "Contract", on_delete=models.CASCADE, related_name="files"
    )
    file_name = models.CharField(max_length=255, blank=True, default="")
    file_content = models.BinaryField(null=True)
    file_type = models.CharField(max_length=20, default="image/png")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.IntegerField(default=0)

    def set_file_content(self, content):
        """Encrypt and store file content"""
        if content:
            self.file_size = len(content)
            self.encrypted_content = encrypt_file(content)

    def get_file_content(self):
        """Decrypt and return file content"""
        return decrypt_file(self.encrypted_content)

    def save(self, *args, **kwargs):
        if self.pk:
            logger.info(f"Updating ContractFile {self.pk} for {self.contract}")
        else:
            logger.info(f"Creating new ContractFile for {self.contract}")
        super().save(*args, **kwargs)

    encrypted_content = models.BinaryField(null=True)


class ContractDetails(models.Model):
    """
    Model for rental contract details including cost information.
    """

    contract = models.ForeignKey(
        "Contract",
        on_delete=models.CASCADE,
        related_name="details",
        null=True,
        blank=True,
    )

    # Basic Contract Information
    CONTRACT_TYPES = [
        ("unlimited", "Unbefristeter Mietvertrag"),
        ("limited", "Befristeter Mietvertrag"),
        ("sublease", "Untermietvertrag"),
    ]
    contract_type = models.CharField(
        max_length=20, choices=CONTRACT_TYPES, null=True, blank=True
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Property Information
    street = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=10, null=True, blank=True)

    PROPERTY_TYPES = [
        ("apartment", "Wohnung"),
        ("house", "Haus"),
        ("room", "Zimmer"),
        ("commercial", "Gewerbe"),
    ]
    property_type = models.CharField(
        max_length=20, choices=PROPERTY_TYPES, null=True, blank=True
    )
    number_of_rooms = models.DecimalField(
        max_digits=3, decimal_places=1, null=True, blank=True
    )
    living_space = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="In square meters",
        null=True,
        blank=True,
    )

    # Property Features (Boolean fields for quick filtering)
    kitchen = models.BooleanField(default=False)
    bathroom = models.BooleanField(default=False)
    separate_wc = models.BooleanField(default=False)
    balcony_or_terrace = models.BooleanField(default=False)
    garden = models.BooleanField(default=False)
    garage_or_parking = models.BooleanField(default=False)
    elevator = models.BooleanField(default=False)

    # Rental Costs (Consolidated)
    basic_rent = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    operating_costs = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, null=True, blank=True
    )
    heating_costs = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, null=True, blank=True
    )
    garage_costs = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, null=True, blank=True
    )
    other_costs = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, null=True, blank=True
    )

    # Cost Payment Structure
    PAYMENT_TYPES = [
        ("fixed", "Festbetrag"),
        ("advance", "Vorauszahlung mit Abrechnung"),
        ("allocation", "Pauschale ohne Abrechnung"),
    ]
    operating_costs_type = models.CharField(
        max_length=10, choices=PAYMENT_TYPES, default="advance", null=True, blank=True
    )
    heating_costs_type = models.CharField(
        max_length=10, choices=PAYMENT_TYPES, default="advance", null=True, blank=True
    )

    # Security Deposit
    deposit_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Termination Terms
    termination_notice_tenant = models.PositiveIntegerField(
        default=3, help_text="Notice period in months for tenant", null=True, blank=True
    )
    termination_notice_landlord = models.PositiveIntegerField(
        default=3,
        help_text="Notice period in months for landlord",
        null=True,
        blank=True,
    )

    # Maintenance Responsibilities
    RESPONSIBILITY_CHOICES = [
        ("tenant", "Mieter"),
        ("landlord", "Vermieter"),
        ("shared", "Geteilt"),
    ]
    cosmetic_repairs = models.CharField(
        max_length=10,
        choices=RESPONSIBILITY_CHOICES,
        default="tenant",
        null=True,
        blank=True,
    )
    small_repairs = models.CharField(
        max_length=10,
        choices=RESPONSIBILITY_CHOICES,
        default="tenant",
        null=True,
        blank=True,
    )
    small_repairs_limit = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )

    # Permissions
    pets_allowed = models.BooleanField(default=False, null=True, blank=True)
    subletting_allowed = models.BooleanField(default=False, null=True, blank=True)

    # Quiet Hours (Structured time fields)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)

    # Renovation Intervals (Structured to avoid free text)
    renovation_interval_years = models.PositiveIntegerField(null=True, blank=True)

    # Additional Legal Clauses (Optional structured data)
    has_stepped_rent = models.BooleanField(default=False, null=True, blank=True)
    has_indexed_rent = models.BooleanField(default=False, null=True, blank=True)

    # AI Extracted Data
    neighborhood_analysis = models.TextField(null=True, blank=True)
    full_contract_text = models.TextField(null=True, blank=True)
    simplified_paragraphs = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Rental Contract"
        verbose_name_plural = "Rental Contracts"

    def __str__(self):
        items = self.__dict__.items()
        return f"{self.contract} - {', '.join([f'{k}: {v}' for k, v in items])}"

    @property
    def total_rent(self):
        """Calculate total monthly rent including all cost components"""
        return (
                (self.basic_rent or 0)
                + (self.operating_costs or 0)
                + (self.heating_costs or 0)
                + (self.garage_costs or 0)
                + (self.other_costs or 0)
        )

    @property
    def is_unlimited(self):
        """Check if contract is unlimited"""
        return self.contract_type == "unlimited"

    @property
    def deposit_in_monthly_rents(self):
        """Calculate deposit in relation to monthly rent"""
        if self.basic_rent and self.basic_rent > 0:
            return self.deposit_amount / self.basic_rent
        return 0

    @property
    def has_valid_cosmetic_repair_clause(self):
        """Check if cosmetic repair clause meets legal requirements"""
        return (
                self.cosmetic_repairs == "tenant"
                and self.renovation_interval_years is not None
                and self.renovation_interval_years >= 5
        )

    def update(self, updated_contract_details: dict):
        # Update fields with extracted information
        valid_fields = [f.name for f in self._meta.fields]
        for key, value in updated_contract_details.items():
            if key in valid_fields:
                setattr(self, key, value)

        self.save()


class Analysis(models.Model):
    """Record of analyses performed by users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analyses')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_extended = models.BooleanField(default=False)

    # Source entitlement that was used for this analysis
    source_entitlement = models.ForeignKey(Entitlement, on_delete=models.SET_NULL,
                                           null=True, related_name='analyses')

    def __str__(self):
        return f"{self.user.username} - {'Extended' if self.is_extended else 'Basic'} - {self.created_at}"
