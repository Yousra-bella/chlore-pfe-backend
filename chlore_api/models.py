from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class Centre(models.Model):
    nom   = models.CharField(max_length=100)
    ville = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.nom


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        extra_fields.setdefault('role', 'agent')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin',        'Administrateur'),
        ('chef_centre',  'Chef Centre'),
        ('agent',        'Agent Exploitation'),
        ('consultation', 'Consultation'),
    ]
    objects   = UserManager()
    role      = models.CharField(max_length=20, choices=ROLE_CHOICES, default='agent')
    centre    = models.ForeignKey(
                    Centre,
                    on_delete=models.SET_NULL,
                    null=True, blank=True,
                    related_name='users',
                )
    telephone = models.CharField(max_length=20, blank=True, default='')

    def __str__(self):
        return f"{self.username} ({self.role})"