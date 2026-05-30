from django.contrib import admin
from .models import Channel, Message, DirectMessage, Reaction, Report


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel_type', 'is_public', 'created_by', 'created_at']
    list_filter = ['channel_type', 'is_public']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['author', 'channel', 'content', 'message_type', 'is_deleted', 'created_at']
    list_filter = ['message_type', 'is_deleted']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['reporter', 'reported_user', 'reason', 'status', 'created_at']
    list_filter = ['status']