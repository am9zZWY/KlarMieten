# models.py
import base64
import logging
import uuid

from django.contrib.auth import get_user_model
from django.db import models

from .utils.encryption import decrypt_file, encrypt_file

User = get_user_model()

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
            logger.info(f"Updating ContractFile {self.pk} for contract {self.contract}")
        else:
            logger.info(f"Creating new ContractFile for contract {self.contract}")
        super().save(*args, **kwargs)

    def get_image_data(self):
        """Return decrypted image data"""
        if not self.encrypted_content:
            return None

        # Decrypt data
        decrypted_data = decrypt_data(self.encrypted_content)
        return base64.b64encode(decrypted_data).decode("utf-8")

    def get_data_url(self):
        """Return complete data URL for embedding in HTML"""
        if not self.file_content:
            return None
        return f"data:{self.file_type};base64,{self.get_image_data()}"

    encrypted_content = models.BinaryField(null=True)


class ContractDetails(models.Model):
    contract = models.ForeignKey(
        "Contract", on_delete=models.CASCADE, related_name="details"
    )
    contract_type = models.CharField(max_length=50, blank=True, null=True)

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

    # Information needed for Mietspiegel
    living_space = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    year_of_construction = models.IntegerField(null=True, blank=True)
    modernization = models.IntegerField(null=True, blank=True)
    floor = models.IntegerField(null=True, blank=True)
    elevator = models.BooleanField(default=False)
    energy_certificate = models.CharField(max_length=50, blank=True, null=True)
    energy_consumption = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    energy_class = models.CharField(max_length=50, blank=True, null=True)

    # Shared Facilities
    shared_facilities = models.TextField(blank=True, null=True)

    # Keys Provided
    keys_provided = models.TextField(blank=True, null=True)

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
    additional_costs = models.TextField(blank=True, null=True)
    total_rent = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Heating Type
    heating_type = models.CharField(max_length=50, blank=True, null=True)

    # Additional Clauses
    additional_clauses = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Contract Details for {self.contract}"

    def save(self, *args, **kwargs):
        if self.pk:
            logger.info(
                f"Updating ContractDetails {self.pk} for contract {self.contract}"
            )
        else:
            logger.info(f"Creating new ContractDetails for contract {self.contract}")
        try:
            super().save(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error saving ContractDetails: {e}")


class Paragraph(models.Model):
    contract_details = models.ForeignKey(
        "ContractDetails", on_delete=models.CASCADE, related_name="paragraphs"
    )
    title = models.CharField(max_length=100)
    content = models.TextField()
    summary = models.TextField()
    problems = models.TextField()

    def __str__(self):
        return f"Paragraph {self.title} for {self.contract_details}"

    def save(self, *args, **kwargs):
        if self.pk:
            logger.info(f"Updating Paragraph {self.pk} for contract {self.contract}")
        else:
            logger.info(f"Creating new Paragraph for contract {self.contract}")
        super().save(*args, **kwargs)


class Mietspiegel(models.Model):
    wohnflaeche_qm = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Wohnfläche (qm)"
    )
    baujahr = models.IntegerField(verbose_name="Baujahr")
    zone = models.CharField(max_length=50, verbose_name="Zone")
    laermbelastung = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Lärmbelastung"
    )
    heizungsart = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Heizungsart"
    )
    bodenbelag = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Bodenbelag"
    )
    sanitaerausstattung = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Sanitärausstattung"
    )

    souterrain = models.BooleanField(
        default=False, verbose_name="Wohnung im Souterrain"
    )
    einfacher_kuechenboden = models.BooleanField(
        default=False, verbose_name="Einfacher Küchenboden"
    )
    aufzug = models.BooleanField(default=False, verbose_name="Aufzug")
    zusatzlicher_sanitarraum = models.BooleanField(
        default=False, verbose_name="Zusätzlicher Sanitärraum"
    )
    maisonette = models.BooleanField(default=False, verbose_name="Maisonette")
    einfamilienhaus = models.BooleanField(default=False, verbose_name="Einfamilienhaus")

    sanitaerausstattung_erneuert = models.BooleanField(
        default=False, verbose_name="Sanitärausstattung erneuert"
    )
    bodenbelaege_erneuert = models.BooleanField(
        default=False, verbose_name="Bodenbeläge erneuert"
    )
    elektroinstallation_erneuert = models.BooleanField(
        default=False, verbose_name="Elektroinstallation erneuert"
    )
    energetisch_saniert = models.BooleanField(
        default=False, verbose_name="Energetisch saniert"
    )
    fussbodenheizung = models.BooleanField(
        default=False, verbose_name="Fußbodenheizung"
    )
    offene_kueche = models.BooleanField(default=False, verbose_name="Offene Küche")

    # Calculation-Related Fields
    gesamtpunktzahl = models.IntegerField(
        blank=True, null=True, verbose_name="Gesamtpunktzahl der Wohnung"
    )
    rechenweg_basismiete = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Rechenweg Basismiete (€/qm)",
    )

    def calculate_rent(self):
        """
        Calculates the rent based on the Mietspiegel data.
        """
        if self.rechenweg_basismiete is None or self.gesamtpunktzahl is None:
            return None  # Or raise an exception, depending on your needs

        # Calculate Spannenmitte (€/qm)
        punkte_faktor = (self.gesamtpunktzahl + 100) / 100
        spannenmitte_qm = self.rechenweg_basismiete * punkte_faktor
        self.spannenmitte_qm = round(spannenmitte_qm, 2)

        # You'll need to determine the logic for calculating
        # mietpreisspanne_min_qm and mietpreisspanne_max_qm based on
        # the specific Mietspiegel rules.  This is a placeholder.
        # Example:  Assume a +/- 15% range around the Spannenmitte
        spanne_percentage = 0.15
        self.mietpreisspanne_min_qm = round(
            self.spannenmitte_qm * (1 - spanne_percentage), 2
        )
        self.mietpreisspanne_max_qm = round(
            self.spannenmitte_qm * (1 + spanne_percentage), 2
        )

        # Calculate Gesamtmiete (Spannenmitte)
        self.gesamtmiete_spannenmitte = int(self.spannenmitte_qm * self.wohnflaeche_qm)

        # Calculate Gesamtmiete (Spanne)
        self.gesamtmiete_spanne_min = int(
            self.mietpreisspanne_min_qm * self.wohnflaeche_qm
        )
        self.gesamtmiete_spanne_max = int(
            self.mietpreisspanne_max_qm * self.wohnflaeche_qm
        )

        self.save()  # Save the calculated values

        return {
            "spannenmitte_qm": self.spannenmitte_qm,
            "mietpreisspanne_min_qm": self.mietpreisspanne_min_qm,
            "mietpreisspanne_max_qm": self.mietpreisspanne_max_qm,
            "gesamtmiete_spannenmitte": self.gesamtmiete_spannenmitte,
            "gesamtmiete_spanne_min": self.gesamtmiete_spanne_min,
            "gesamtmiete_spanne_max": self.gesamtmiete_spanne_max,
        }

    def __str__(self):
        return f"Mietspiegel: {self.wohnflaeche_qm} qm, Baujahr {self.baujahr}, Zone {self.zone}"


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
