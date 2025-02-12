# models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=15, blank=True)


class Contract(models.Model):
    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("processing", "Processing"),
        ("analyzed", "Analyzed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    contract_file = models.FileField(upload_to="contracts/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploaded")
    ai_model_version = models.CharField(max_length=20)


class ContractClause(models.Model):
    contract = models.ForeignKey(
        Contract, on_delete=models.CASCADE, related_name="clauses"
    )
    clause_text = models.TextField()
    line_number = models.IntegerField()


class ContractAnalysis(models.Model):
    clause = models.ForeignKey(
        ContractClause, on_delete=models.CASCADE, related_name="analyses"
    )
    is_valid = models.BooleanField(default=False)
    explanation = models.TextField()  # AI-generated rationale
    legal_reference = models.CharField(max_length=255)  # e.g., § BGB 536
    compliance_status = models.CharField(
        max_length=50, choices=[("compliant", "Compliant"), ("violation", "Violation")]
    )


class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    stripe_subscription_id = models.CharField(max_length=255)
    status = models.CharField(max_length=20)
    current_period_end = models.DateTimeField()


class PaymentHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
