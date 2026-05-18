"""Custom User model for NexusPay"""
import uuid
import pyotp
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    USER = "USER", "User"
    ADMIN = "ADMIN", "Admin"
    SUPERADMIN = "SUPERADMIN", "Super Admin"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        extra_fields.setdefault("role", UserRole.USER)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.SUPERADMIN)
        extra_fields.setdefault("is_verified", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True, unique=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.USER)

    # Verification
    is_verified = models.BooleanField(default=False)
    kyc_status = models.CharField(
        max_length=20,
        choices=[("PENDING", "Pending"), ("VERIFIED", "Verified"), ("REJECTED", "Rejected")],
        default="PENDING",
    )

    # OTP
    otp_secret = models.CharField(max_length=64, blank=True, null=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    # Django internals
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    # Metadata
    profile_picture = models.ImageField(upload_to="profiles/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def generate_otp(self):
        """Generate a time-based OTP secret and return the 6-digit code"""
        self.otp_secret = pyotp.random_base32()
        self.otp_created_at = timezone.now()
        self.save(update_fields=["otp_secret", "otp_created_at"])
        totp = pyotp.TOTP(self.otp_secret, interval=300)
        return totp.now()

    def verify_otp(self, otp_code: str) -> bool:
        """Verify OTP — valid for 5 minutes"""
        if not self.otp_secret or not self.otp_created_at:
            return False
        elapsed = (timezone.now() - self.otp_created_at).total_seconds()
        if elapsed > 300:
            return False
        totp = pyotp.TOTP(self.otp_secret, interval=300)
        return totp.verify(otp_code, valid_window=1)

    def clear_otp(self):
        self.otp_secret = None
        self.otp_created_at = None
        self.save(update_fields=["otp_secret", "otp_created_at"])
