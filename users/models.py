from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager

class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(_("email address"), unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    first_connection = models.BooleanField(default=True)

    first_name = models.CharField(default="", max_length=255)
    last_name = models.CharField(default="", max_length=255)

    ANSWER_GENERATION_CHOICES = [
        ('formal', 'Formal'),
        ('friendly', 'Friendly'),
        ('emoji', 'With Emojis')
    ]

    is_google_managed = models.BooleanField(default=False)
    answerGenerationPreferences = models.CharField(max_length=255, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = CustomUserManager()

    def toggleFirstConnection(self):
        self.first_connection = not self.first_connection
        self.save()

    def __str__(self):
        return self.username