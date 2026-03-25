from django.contrib import admin
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField


class UserManager(BaseUserManager):
    """Менеджер с логином по email."""

    def _create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("Email обязателен"))

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if not extra_fields.get("is_staff"):
            raise ValueError(_("Superuser must have is_staff=True"))
        if not extra_fields.get("is_superuser"):
            raise ValueError(_("Superuser must have is_superuser=True"))

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):

    username = None  # отключаем username
    email = models.EmailField(_("Email"), unique=True)

    phone_number = PhoneNumberField(
        _("Номер телефона"),
        blank=False,
        unique=True,
        help_text="Введите в формате 0 или 996"
    )

    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    middle_name = models.CharField(_("Отчество"), max_length=150, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # email уже обязателен

    objects = UserManager()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.email} - {self.full_name}"

    @property
    @admin.display(description="ФИО")
    def full_name(self):
        return f" {self.first_name} {self.last_name} {self.middle_name}".strip()
