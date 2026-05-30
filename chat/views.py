from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib import messages
from django.db.models import Q, Max, Subquery, OuterRef
from django.utils import timezone
from .models import Channel, Message, DirectMessage, Report
from accounts.models import User
import json


@login_required
def index_view(request):
    channels = Channel.objects.filter(
        Q(is_public=True) | Q(members=request.user)
    ).distinct()
    first_channel = channels.filter(channel_type=Channel.TYPE_TEXT).first()
    if first_channel:
        return redirect('chat:channel', channel_id=first_channel.id)
    return render(request, 'no_channels.html', {'channels': channels})


@login_required
def channel_view(request, channel_id):
    channel = get_object_or_404(Channel, id=channel_id)
    if not channel.is_public and request.user not in channel.members.all():
        messages.error(request, 'Nie masz dostępu do tego kanału.')
        return redirect('chat:index')

    channel.members.add(request.user)
    all_channels = Channel.objects.filter(
        Q(is_public=True) | Q(members=request.user)
    ).distinct()

    msg_list = Message.objects.filter(channel=channel, is_deleted=False).select_related('author').prefetch_related('reactions')[:100]

    dm_list = get_dm_list(request.user)
    online_users = User.objects.filter(status='online').exclude(id=request.user.id)[:20]

    return render(request, 'channel.html', {
        'channel': channel,
        'channels': all_channels,
        'messages': msg_list,
        'dm_list': dm_list,
        'online_users': online_users,
    })


@login_required
def create_channel_view(request):
    if not (request.user.is_admin or request.user.is_moderator):
        return JsonResponse({'error': 'Brak uprawnień'}, status=403)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        channel_type = request.POST.get('channel_type', 'text')
        is_public = request.POST.get('is_public') == 'true'
        if not name:
            return JsonResponse({'error': 'Nazwa kanału jest wymagana'}, status=400)
        if Channel.objects.filter(name=name).exists():
            return JsonResponse({'error': 'Kanał o tej nazwie już istnieje'}, status=400)
        channel = Channel.objects.create(
            name=name.lower().replace(' ', '-'),
            description=description,
            channel_type=channel_type,
            is_public=is_public,
            created_by=request.user,
        )
        channel.members.add(request.user)
        return JsonResponse({'ok': True, 'id': channel.id, 'name': channel.name, 'type': channel.channel_type})
    return JsonResponse({'error': 'Tylko POST'}, status=405)


@login_required
def delete_channel_view(request, channel_id):
    if not request.user.is_admin:
        return JsonResponse({'error': 'Brak uprawnień'}, status=403)
    channel = get_object_or_404(Channel, id=channel_id)
    channel.delete()
    return JsonResponse({'ok': True})


@login_required
def dm_view(request, username):
    other_user = get_object_or_404(User, username=username)
    if other_user == request.user:
        return redirect('chat:index')

    dm_messages = DirectMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user)
    ).select_related('sender').order_by('created_at')[:100]

    DirectMessage.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)

    all_channels = Channel.objects.filter(
        Q(is_public=True) | Q(members=request.user)
    ).distinct()
    dm_list = get_dm_list(request.user)
    online_users = User.objects.filter(status='online').exclude(id=request.user.id)[:20]

    return render(request, 'dm.html', {
        'other_user': other_user,
        'channels': all_channels,
        'dm_messages': dm_messages,
        'dm_list': dm_list,
        'online_users': online_users,
    })


@login_required
def send_message_view(request, channel_id):
    """REST fallback for file uploads"""
    channel = get_object_or_404(Channel, id=channel_id)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        file = request.FILES.get('file')
        msg_type = Message.TYPE_TEXT

        if file:
            ct = file.content_type
            if ct.startswith('image/'):
                msg_type = Message.TYPE_IMAGE
            elif ct.startswith('audio/'):
                msg_type = Message.TYPE_AUDIO

        msg = Message.objects.create(
            channel=channel,
            author=request.user,
            content=content,
            message_type=msg_type,
            file=file,
        )
        return JsonResponse({
            'ok': True,
            'id': msg.id,
            'content': msg.content,
            'message_type': msg.message_type,
            'file_url': msg.file.url if msg.file else None,
            'username': request.user.username,
            'timestamp': msg.created_at.strftime('%H:%M'),
            'avatar': request.user.get_avatar_url(),
            'initials': request.user.get_initials(),
        })
    return JsonResponse({'error': 'POST only'}, status=405)


@login_required
def send_dm_file_view(request, username):
    other_user = get_object_or_404(User, username=username)
    if request.method == 'POST':
        file = request.FILES.get('file')
        content = request.POST.get('content', '')
        msg_type = Message.TYPE_TEXT
        if file:
            ct = file.content_type
            if ct.startswith('image/'):
                msg_type = Message.TYPE_IMAGE
            elif ct.startswith('audio/'):
                msg_type = Message.TYPE_AUDIO
        msg = DirectMessage.objects.create(
            sender=request.user, receiver=other_user,
            content=content, message_type=msg_type, file=file
        )
        return JsonResponse({
            'ok': True, 'id': msg.id, 'content': msg.content,
            'message_type': msg.message_type, 'file_url': msg.file.url if msg.file else None,
            'username': request.user.username, 'timestamp': msg.created_at.strftime('%H:%M'),
        })
    return JsonResponse({'error': 'POST only'}, status=405)


@login_required
def delete_message_view(request, message_id):
    msg = get_object_or_404(Message, id=message_id)
    if msg.author == request.user or request.user.is_moderator:
        msg.is_deleted = True
        msg.save(update_fields=['is_deleted'])
        return JsonResponse({'ok': True})
    return JsonResponse({'error': 'Brak uprawnień'}, status=403)


@login_required
def react_message_view(request, message_id):
    if request.method == 'POST':
        from .models import Reaction
        emoji = request.POST.get('emoji', '')
        if not emoji:
            return JsonResponse({'error': 'Brak emoji'}, status=400)
        msg = get_object_or_404(Message, id=message_id)
        obj, created = Reaction.objects.get_or_create(message=msg, user=request.user, emoji=emoji)
        if not created:
            obj.delete()
            action = 'removed'
        else:
            action = 'added'
        return JsonResponse({'ok': True, 'action': action})
    return JsonResponse({'error': 'POST only'}, status=405)


@login_required
def report_user_view(request, username):
    reported = get_object_or_404(User, username=username)
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if reason:
            Report.objects.create(reporter=request.user, reported_user=reported, reason=reason)
            return JsonResponse({'ok': True})
        return JsonResponse({'error': 'Podaj powód'}, status=400)
    return JsonResponse({'error': 'POST only'}, status=405)


@login_required
def block_user_view(request, username):
    if not request.user.is_moderator:
        return JsonResponse({'error': 'Brak uprawnień'}, status=403)
    target = get_object_or_404(User, username=username)
    target.is_blocked = not target.is_blocked
    target.save(update_fields=['is_blocked'])
    return JsonResponse({'ok': True, 'blocked': target.is_blocked})


@login_required
def reports_view(request):
    if not request.user.is_moderator:
        messages.error(request, 'Brak uprawnień.')
        return redirect('chat:index')
    reports = Report.objects.select_related('reporter', 'reported_user').order_by('-created_at')
    return render(request, 'reports.html', {'reports': reports})


@login_required
def resolve_report_view(request, report_id):
    if not request.user.is_moderator:
        return JsonResponse({'error': 'Brak uprawnień'}, status=403)
    report = get_object_or_404(Report, id=report_id)
    report.status = Report.STATUS_RESOLVED
    report.save(update_fields=['status'])
    return JsonResponse({'ok': True})


@login_required
def unread_count_view(request):
    count = DirectMessage.objects.filter(receiver=request.user, is_read=False).count()
    return JsonResponse({'count': count})


def get_dm_list(user):
    """Get list of DM conversations for a user"""
    sent = DirectMessage.objects.filter(sender=user).values_list('receiver_id', flat=True).distinct()
    received = DirectMessage.objects.filter(receiver=user).values_list('sender_id', flat=True).distinct()
    user_ids = set(list(sent) + list(received))
    dm_users = User.objects.filter(id__in=user_ids)
    dm_list = []
    for u in dm_users:
        unread = DirectMessage.objects.filter(sender=u, receiver=user, is_read=False).count()
        last_msg = DirectMessage.objects.filter(
            Q(sender=user, receiver=u) | Q(sender=u, receiver=user)
        ).order_by('-created_at').first()
        dm_list.append({'user': u, 'unread': unread, 'last_msg': last_msg})
    dm_list.sort(key=lambda x: x['last_msg'].created_at if x['last_msg'] else timezone.now(), reverse=True)
    return dm_list


def error_404(request, exception):
    return render(request, 'errors/404.html', status=404)


def error_500(request):
    return render(request, 'errors/500.html', status=500)