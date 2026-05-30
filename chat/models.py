from django.db import models
from django.conf import settings


class Channel(models.Model):
    TYPE_TEXT = 'text'
    TYPE_VOICE = 'voice'
    TYPE_CHOICES = [
        (TYPE_TEXT, 'Tekstowy'),
        (TYPE_VOICE, 'Głosowy'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    channel_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_TEXT)
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, related_name='created_channels')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='channels')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'#{self.name}'

    def get_icon(self):
        return '#' if self.channel_type == self.TYPE_TEXT else '🔊'


class Message(models.Model):
    TYPE_TEXT = 'text'
    TYPE_IMAGE = 'image'
    TYPE_AUDIO = 'audio'
    TYPE_CHOICES = [
        (TYPE_TEXT, 'Tekst'),
        (TYPE_IMAGE, 'Obraz'),
        (TYPE_AUDIO, 'Audio'),
    ]

    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='messages',
                                null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField(blank=True)
    message_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_TEXT)
    file = models.FileField(upload_to='uploads/', null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author.username}: {self.content[:50]}'

    def get_reactions_dict(self):
        reactions = {}
        for r in self.reactions.all():
            if r.emoji not in reactions:
                reactions[r.emoji] = []
            reactions[r.emoji].append(r.user.username)
        return reactions


class DirectMessage(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_dms')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_dms')
    content = models.TextField(blank=True)
    message_type = models.CharField(max_length=10, choices=Message.TYPE_CHOICES, default=Message.TYPE_TEXT)
    file = models.FileField(upload_to='uploads/', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'DM {self.sender} -> {self.receiver}: {self.content[:30]}'


class Reaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'user', 'emoji']


class Report(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_RESOLVED = 'resolved'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Oczekuje'),
        (STATUS_RESOLVED, 'Rozwiązane'),
    ]

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_made')
    reported_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_received')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Zgłoszenie: {self.reporter} -> {self.reported_user}'