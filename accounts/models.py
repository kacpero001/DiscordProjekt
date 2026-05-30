from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_USER = 'user'
    ROLE_MODERATOR = 'moderator'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_USER, 'Użytkownik'),
        (ROLE_MODERATOR, 'Moderator'),
        (ROLE_ADMIN, 'Administrator'),
    ]

    STATUS_ONLINE = 'online'
    STATUS_AWAY = 'away'
    STATUS_DND = 'dnd'
    STATUS_OFFLINE = 'offline'

    STATUS_CHOICES = [
        (STATUS_ONLINE, 'Online'),
        (STATUS_AWAY, 'Nieobecny'),
        (STATUS_DND, 'Nie przeszkadzać'),
        (STATUS_OFFLINE, 'Offline'),
    ]

    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=300, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OFFLINE)
    is_blocked = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    blocked_users = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='blocked_by')

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    @property
    def is_moderator(self):
        return self.role in [self.ROLE_MODERATOR, self.ROLE_ADMIN] or self.is_superuser

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return None

    def get_initials(self):
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        return self.username[:2].upper()

    def get_status_color(self):
        colors = {
            'online': '#3ba55d',
            'away': '#faa81a',
            'dnd': '#ed4245',
            'offline': '#747f8d',
        }
        return colors.get(self.status, '#747f8d')