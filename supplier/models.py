from django.core.validators import RegexValidator, EmailValidator
from django.db import models
from django.utils import timezone

# Create your models here.
phone_validator = RegexValidator(
    regex=r"^[0-9+\-\s]{7,20}$",
    message="Teléfono inválido. Usa dígitos, +, -, espacios. Mínimo 7 caracteres."
)


class Supplier(models.Model):
    """
    It stores general contact information, status, and notes.
    """
    # Full name of the supplier. Used as the main identifier in the system.
    name = models.CharField("Name", max_length=160, unique=True)
    # Optional field that may store the supplier’s age or contact representative’s age.
    age = models.IntegerField("Age", blank=True, null=True)
    # Email used for communication and sending documents or purchase orders.
    email = models.EmailField("Email", max_length=200, blank=True, validators=[EmailValidator()])
    #  Supplier phone number for direct communication.
    phone = models.CharField("Phone", max_length=20, blank=True, validators=[phone_validator])
    # City or municipality of the supplier’s business location.
    city = models.CharField("City", max_length=120, blank=True)
    # Country of operation or business registration.
    country = models.CharField("Country", max_length=120, default="Guatemala", blank=True)
    #  Observations, comments, or special details about this supplier.
    notes = models.TextField("Notes", blank=True)
    #  True if the supplier is active and available for transactions.
    active = models.BooleanField("Active", default=True)
    # Automatically saves the creation timestamp of the record.
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    #Automatically updates when the supplier information changes.
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["active"]),
        ]

    def __str__(self):
        return self.name
