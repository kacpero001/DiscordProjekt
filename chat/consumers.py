import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.channel_id = self.scope['url_route']['kwargs']['channel_id']
        self.room_group_name = f'chat_{self.channel_id}'
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'user_status', 'username': user.username, 'status': 'online', 'action': 'joined'}
        )

    async def disconnect(self, code):
        user = self.scope['user']
        if user.is_authenticated:
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'user_status', 'username': user.username, 'status': 'offline', 'action': 'left'}
            )
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        msg_type = data.get('type', 'message')
        user = self.scope['user']

        if msg_type == 'message':
            content = data.get('content', '').strip()
            if not content:
                return
            message = await self.save_message(user, content)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': message['id'],
                    'content': content,
                    'username': user.username,
                    'avatar': message['avatar'],
                    'initials': message['initials'],
                    'timestamp': message['timestamp'],
                    'role': message['role'],
                }
            )
        elif msg_type == 'reaction':
            msg_id = data.get('message_id')
            emoji = data.get('emoji')
            if msg_id and emoji:
                result = await self.toggle_reaction(user, msg_id, emoji)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'reaction_update', 'message_id': msg_id, 'emoji': emoji,
                     'username': user.username, 'action': result}
                )
        elif msg_type == 'delete':
            msg_id = data.get('message_id')
            if msg_id:
                ok = await self.delete_message(user, msg_id)
                if ok:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {'type': 'message_deleted', 'message_id': msg_id}
                    )
        elif msg_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'typing_indicator', 'username': user.username, 'is_typing': data.get('is_typing', False)}
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'type': 'message', **event}))

    async def user_status(self, event):
        await self.send(text_data=json.dumps({'type': 'user_status', **event}))

    async def reaction_update(self, event):
        await self.send(text_data=json.dumps({'type': 'reaction', **event}))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({'type': 'deleted', **event}))

    async def typing_indicator(self, event):
        if event['username'] != self.scope['user'].username:
            await self.send(text_data=json.dumps({'type': 'typing', **event}))

    @database_sync_to_async
    def save_message(self, user, content):
        from .models import Message, Channel
        channel = Channel.objects.get(id=self.channel_id)
        msg = Message.objects.create(author=user, channel=channel, content=content)
        return {
            'id': msg.id,
            'avatar': user.get_avatar_url(),
            'initials': user.get_initials(),
            'timestamp': msg.created_at.strftime('%H:%M'),
            'role': user.role,
        }

    @database_sync_to_async
    def toggle_reaction(self, user, message_id, emoji):
        from .models import Reaction
        obj, created = Reaction.objects.get_or_create(message_id=message_id, user=user, emoji=emoji)
        if not created:
            obj.delete()
            return 'removed'
        return 'added'

    @database_sync_to_async
    def delete_message(self, user, message_id):
        from .models import Message
        try:
            msg = Message.objects.get(id=message_id)
            if msg.author == user or user.is_moderator:
                msg.is_deleted = True
                msg.save(update_fields=['is_deleted'])
                return True
        except Message.DoesNotExist:
            pass
        return False


class DMConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
        self.other_username = self.scope['url_route']['kwargs']['username']
        users = sorted([user.username, self.other_username])
        self.room_group_name = f'dm_{"_".join(users)}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        user = self.scope['user']
        content = data.get('content', '').strip()
        if not content:
            return
        message = await self.save_dm(user, content)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'dm_message',
                'message_id': message['id'],
                'content': content,
                'username': user.username,
                'avatar': message['avatar'],
                'initials': message['initials'],
                'timestamp': message['timestamp'],
            }
        )

    async def dm_message(self, event):
        await self.send(text_data=json.dumps({'type': 'dm', **event}))

    @database_sync_to_async
    def save_dm(self, user, content):
        from .models import DirectMessage
        from accounts.models import User
        try:
            receiver = User.objects.get(username=self.other_username)
            msg = DirectMessage.objects.create(sender=user, receiver=receiver, content=content)
            return {
                'id': msg.id,
                'avatar': user.get_avatar_url(),
                'initials': user.get_initials(),
                'timestamp': msg.created_at.strftime('%H:%M'),
            }
        except User.DoesNotExist:
            return {'id': None, 'avatar': None, 'initials': '??', 'timestamp': ''}