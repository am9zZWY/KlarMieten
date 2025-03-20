from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid


class User(AbstractUser):
    """Enhanced user model with subscription-related fields"""
    phone = models.CharField(max_length=15, blank=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    is_student = models.BooleanField(default=False)
    student_verified_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username

    def has_active_capability(self, capability_code):
        """Check if user has an active entitlement for the given capability"""
        now = timezone.now()
        return Entitlement.objects.filter(
            models.Q(purchase__user=self) | models.Q(subscription__user=self),
            capability__code=capability_code,
            start_date__lte=now,
            end_date__gt=now
        ).exists()

    def get_entitlement_value(self, capability_code):
        """Get the value of an entitlement for a specific capability"""
        now = timezone.now()
        entitlement = Entitlement.objects.filter(
            models.Q(purchase__user=self) | models.Q(subscription__user=self),
            capability__code=capability_code,
            start_date__lte=now,
            end_date__gt=now
        ).order_by('-value_int', '-end_date').first()

        if entitlement:
            return entitlement.value
        return None

    def activate_student_status(self):
        """Activate student status for the user"""
        self.is_student = True
        self.student_verified_until = timezone.now() + timezone.timedelta(days=365)
        self.save()


class Product(models.Model):
    """Product types offered (Analysis, Chat)"""
    PRODUCT_TYPES = [
        ('ANALYSIS', 'Contract Analysis'),
        ('CHAT', 'Legal Chat'),
    ]

    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Plan(models.Model):
    """Plan configuration (Student, Basic, Pro, Chat+)"""
    BILLING_TYPES = [
        ('ONE_TIME', 'One-Time Purchase'),
        ('SUBSCRIPTION', 'Recurring Subscription'),
    ]

    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='plans')
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")
    billing_type = models.CharField(max_length=20, choices=BILLING_TYPES)
    billing_interval = models.CharField(max_length=20, blank=True)  # "month", "year", etc.
    is_student_plan = models.BooleanField(default=False)
    student_discount_percentage = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.billing_type == 'SUBSCRIPTION':
            return f"{self.name} ({self.price} {self.currency}/{self.billing_interval})"
        return f"{self.name} ({self.price} {self.currency})"


class Capability(models.Model):
    """System capabilities that can be granted to users"""
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Type of capability value
    VALUE_TYPES = [
        ('BOOLEAN', 'Boolean Value'),  # Access to feature (yes/no)
        ('INTEGER', 'Integer Value'),  # Quantifiable (analyses count, storage days)
        ('STRING', 'String Value'),    # Text value if needed
    ]
    value_type = models.CharField(max_length=10, choices=VALUE_TYPES)

    def __str__(self):
        return self.name


class PlanCapability(models.Model):
    """Capabilities granted by each plan"""
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='capabilities')
    capability = models.ForeignKey(Capability, on_delete=models.CASCADE)
    value_int = models.IntegerField(null=True, blank=True)
    value_bool = models.BooleanField(default=False)
    value_text = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('plan', 'capability')

    def __str__(self):
        return f"{self.plan.name} - {self.capability.name}"

    @property
    def value(self):
        """Return the appropriate value based on capability type"""
        if self.capability.value_type == 'INTEGER':
            return self.value_int
        elif self.capability.value_type == 'STRING':
            return self.value_text
        else:  # BOOLEAN
            return self.value_bool


class Purchase(models.Model):
    """One-time purchase model (Student, Basic)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    purchase_date = models.DateTimeField(auto_now_add=True)
    price_paid = models.DecimalField(max_digits=6, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")
    stripe_payment_id = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} - {self.purchase_date}"

    def create_entitlements(self):
        """Create entitlements based on plan capabilities"""
        storage_days = 0

        # Get storage days to calculate expiration
        storage_capability = self.plan.capabilities.filter(
            capability__code='storage_days'
        ).first()

        if storage_capability:
            storage_days = storage_capability.value_int or 0

        expiry_date = timezone.now() + timezone.timedelta(days=storage_days)

        # Create entitlements for all capabilities in the plan
        for plan_capability in self.plan.capabilities.all():
            Entitlement.objects.create(
                purchase=self,
                capability=plan_capability.capability,
                value_int=plan_capability.value_int,
                value_bool=plan_capability.value_bool,
                value_text=plan_capability.value_text,
                start_date=timezone.now(),
                end_date=expiry_date
            )


class Subscription(models.Model):
    """Recurring subscription model (Pro, Chat+)"""
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('CANCELED', 'Canceled'),
        ('PAST_DUE', 'Past Due'),
        ('EXPIRED', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    canceled_at = models.DateTimeField(null=True, blank=True)
    price_paid = models.DecimalField(max_digits=6, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")
    student_discount_applied = models.BooleanField(default=False)
    stripe_subscription_id = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"

    def create_entitlements(self):
        """Create entitlements based on subscription plan capabilities"""
        # Delete any existing entitlements for this subscription
        self.entitlements.all().delete()

        # Create new entitlements for all capabilities in the plan
        for plan_capability in self.plan.capabilities.all():
            Entitlement.objects.create(
                subscription=self,
                capability=plan_capability.capability,
                value_int=plan_capability.value_int,
                value_bool=plan_capability.value_bool,
                value_text=plan_capability.value_text,
                start_date=self.start_date,
                end_date=self.end_date
            )


class Entitlement(models.Model):
    """Rights granted to users from purchases or subscriptions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Link to either a purchase or subscription (not both)
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE,
                                 null=True, blank=True, related_name='entitlements')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE,
                                     null=True, blank=True, related_name='entitlements')
    capability = models.ForeignKey(Capability, on_delete=models.CASCADE)

    # Value fields matching the capability type
    value_int = models.IntegerField(null=True, blank=True)
    value_bool = models.BooleanField(default=False)
    value_text = models.CharField(max_length=255, blank=True)

    # Usage tracking for consumable entitlements (e.g., analyses)
    usage_count = models.IntegerField(default=0)

    # Validity period
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                        models.Q(purchase__isnull=False, subscription__isnull=True) |
                        models.Q(purchase__isnull=True, subscription__isnull=False)
                ),
                name='one_source_per_entitlement'
            )
        ]

    def __str__(self):
        source = self.purchase or self.subscription
        user = source.user if source else "Unknown"
        return f"{user} - {self.capability.code}"

    @property
    def value(self):
        """Return the appropriate value based on capability type"""
        if self.capability.value_type == 'INTEGER':
            # For consumable capabilities, subtract usage
            if self.capability.code == 'analyses':
                return max(0, self.value_int - self.usage_count)
            return self.value_int
        elif self.capability.value_type == 'STRING':
            return self.value_text
        else:  # BOOLEAN
            return self.value_bool

    @property
    def is_valid(self):
        """Check if this entitlement is currently valid"""
        now = timezone.now()
        return self.start_date <= now and self.end_date > now

    def use(self, count=1):
        """Use this entitlement (for consumable capabilities)"""
        if self.capability.value_type == 'INTEGER':
            self.usage_count += count
            self.save()
            return self.value >= 0
        return True
