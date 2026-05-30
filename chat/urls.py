from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('channel/<int:channel_id>/', views.channel_view, name='channel'),
    path('channel/create/', views.create_channel_view, name='create_channel'),
    path('channel/<int:channel_id>/delete/', views.delete_channel_view, name='delete_channel'),
    path('channel/<int:channel_id>/send/', views.send_message_view, name='send_message'),
    path('channel/message/<int:message_id>/delete/', views.delete_message_view, name='delete_message'),
    path('channel/message/<int:message_id>/react/', views.react_message_view, name='react_message'),
    path('dm/<str:username>/', views.dm_view, name='dm'),
    path('dm/<str:username>/send/', views.send_dm_file_view, name='send_dm_file'),
    path('user/<str:username>/report/', views.report_user_view, name='report_user'),
    path('user/<str:username>/block/', views.block_user_view, name='block_user'),
    path('reports/', views.reports_view, name='reports'),
    path('reports/<int:report_id>/resolve/', views.resolve_report_view, name='resolve_report'),
    path('unread/', views.unread_count_view, name='unread_count'),
]