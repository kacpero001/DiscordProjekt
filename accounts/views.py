from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .forms import RegisterForm, LoginForm, ProfileEditForm, AdminUserEditForm
from .models import User


def register_view(request):
    if request.user.is_authenticated:
        return redirect('chat:index')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Witaj, {user.username}! Konto zostało utworzone.')
            return redirect('chat:index')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('chat:index')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_blocked:
                messages.error(request, 'Twoje konto zostało zablokowane.')
                return redirect('accounts:login')
            login(request, user)
            user.status = User.STATUS_ONLINE
            user.last_seen = timezone.now()
            user.save(update_fields=['status', 'last_seen'])
            messages.success(request, f'Witaj z powrotem, {user.username}!')
            return redirect('chat:index')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


@login_required
def logout_view(request):
    request.user.status = User.STATUS_OFFLINE
    request.user.last_seen = timezone.now()
    request.user.save(update_fields=['status', 'last_seen'])
    logout(request)
    messages.info(request, 'Zostałeś wylogowany.')
    return redirect('accounts:login')


@login_required
def profile_view(request, username=None):
    if username:
        profile_user = get_object_or_404(User, username=username)
    else:
        profile_user = request.user
    return render(request, 'profile.html', {'profile_user': profile_user})


@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil zaktualizowany!')
            return redirect('accounts:profile')
    else:
        form = ProfileEditForm(instance=request.user)
    return render(request, 'edit_profile.html', {'form': form})


@login_required
def admin_users_view(request):
    if not request.user.is_admin:
        messages.error(request, 'Brak uprawnień.')
        return redirect('chat:index')
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'admin_users.html', {'users': users})


@login_required
def admin_edit_user_view(request, user_id):
    if not request.user.is_admin:
        messages.error(request, 'Brak uprawnień.')
        return redirect('chat:index')
    target_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Użytkownik {target_user.username} zaktualizowany.')
            return redirect('accounts:admin_users')
    else:
        form = AdminUserEditForm(instance=target_user)
    return render(request, 'admin_edit_user.html', {'form': form, 'target_user': target_user})


@login_required
def search_users_view(request):
    q = request.GET.get('q', '')
    users = []
    if q:
        users = User.objects.filter(username__icontains=q).exclude(id=request.user.id)[:10]
    data = [{'id': u.id, 'username': u.username, 'status': u.status, 'avatar': u.get_avatar_url()} for u in users]
    return JsonResponse({'users': data})


@login_required
def set_status_view(request):
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in [User.STATUS_ONLINE, User.STATUS_AWAY, User.STATUS_DND, User.STATUS_OFFLINE]:
            request.user.status = status
            request.user.save(update_fields=['status'])
            return JsonResponse({'ok': True, 'status': status})
    return JsonResponse({'ok': False}, status=400)
