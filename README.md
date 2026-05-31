# Nexus Chat – Django Discord-like Application

Kompletna aplikacja komunikacyjna inspirowana platformą Discord, zbudowana z Django, WebSockets i Channels.

## 🚀 Funkcjonalności

### Użytkownicy
- ✅ Rejestracja i logowanie
- ✅ Edycja profilu (avatar, bio, status)
- ✅ System ról: Administrator, Moderator, Użytkownik
- ✅ Status użytkownika (Online/Away/DND/Offline)
- ✅ Blokowanie użytkowników

### Komunikacja
- ✅ Kanały tekstowe (publiczne/prywatne)
- ✅ Wiadomości prywatne (DM) 1:1
- ✅ WebSocket dla komunikacji real-time
- ✅ Historia wiadomości
- ✅ Typowanie w czasie rzeczywistym

### Multimedia
- ✅ Wysyłanie obrazów
- ✅ Wysyłanie audio (nagrania głosowe)
- ✅ Podgląd obrazów (lightbox)
- ✅ Obsługa różnych formatów plików

### Moderacja
- ✅ Usuwanie wiadomości
- ✅ Blokowanie użytkowników
- ✅ System zgłoszeń
- ✅ Panel administratora

### UI/UX
- ✅ Dark theme inspirowany Discordem
- ✅ Responsywny design (mobile-friendly)
- ✅ Emotikony i reakcje na wiadomości
- ✅ Notyfikacje toast

## 📋 Wymagania

- Python 3.11+
- Django 4.2+
- Channels 4.0+
- Pillow (dla obsługi obrazów)

## 🔧 Lokalna instalacja

### 1. Klonowanie i setup

```bash
cd discordapp
python -m venv venv
source venv/bin/activate  # Linux/Mac
# lub
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 2. Migracje bazy danych

```bash
python manage.py migrate
```

### 3. Utworzenie superusera (admin)

```bash
python manage.py createsuperuser
```

### 4. Zbieranie plików statycznych

```bash
python manage.py collectstatic --noinput
```

### 5. Uruchomienie serwera developerskiego

```bash
python manage.py runserver
# lub z Channels:
daphne -b 0.0.0.0 -p 8000 discordapp.asgi:application
```

Aplikacja będzie dostępna na: http://localhost:8000

## 🌐 Deployment na Render.com

### 1. Przygotowanie

- Utwórz konto na [render.com](https://render.com)
- Skopuj kod na GitHub
- Zaloguj się na Render i połącz z repozytorium GitHub

### 2. Ustawienia zmiennych środowiskowych

W panelu Render w sekcji "Environment" dodaj:

```
DJANGO_SETTINGS_MODULE=discordapp.settings
DEBUG=False
SECRET_KEY=<losowy-string-256-znaków>
ALLOWED_HOSTS=yourdomain.onrender.com
DATABASE_URL=<postgres-connection-string>
```

### 3. Konfiguracja WebSockets

Channels wymaga konfiguracji dla WebSockets:

```python
# W settings.py (już skonfigurowane)
INSTALLED_APPS = [
    'daphne',  # Musi być pierwszy
    ...
]

ASGI_APPLICATION = 'discordapp.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}
```

### 4. Deployment

Render automatycznie:
1. Uruchomi migracje (z Procfile: `release: python manage.py migrate`)
2. Zbierze statyczne pliki
3. Uruchomi serwer Daphne (WebSocket-compatible)

## 📁 Struktura projektu

```
discordapp/
├── discordapp/           # Główne ustawienia Django
│   ├── settings.py       # Konfiguracja
│   ├── urls.py          # Routing
│   ├── asgi.py          # WebSocket config
│   └── wsgi.py
├── accounts/            # App użytkowników
│   ├── models.py        # User model z rolami
│   ├── views.py         # Logowanie, profil
│   ├── forms.py         # Formularze rejestracji
│   └── admin.py
├── chat/                # App czatu
│   ├── models.py        # Channel, Message, DM
│   ├── views.py         # Widoki kanałów i DM
│   ├── consumers.py      # WebSocket handlers
│   ├── routing.py       # WebSocket routing
│   └── admin.py
├── templates/           # HTML szablony
│   ├── base.html
│   ├── registration/    # Login, register, profile
│   ├── chat/           # Channel, DM widoki
│   ├── components/      # Reusable komponenty
│   └── errors/         # 404, 500
├── static/             # CSS, JS, obrazy
│   ├── css/            # app.css, auth.css
│   └── js/             # app.js
├── media/              # User uploads (avatary, pliki)
├── requirements.txt
├── manage.py
├── Procfile            # Instrukcje deployment
└── runtime.txt         # Python version

```

## 🔐 Role i uprawnienia

### Administrator
- Pełny dostęp do wszystkich funkcji
- Zarządzanie użytkownikami i kanałami
- Usuwanie wiadomości
- Blokowanie użytkowników
- Panel administracyjny

### Moderator
- Zarządzanie wiadomościami
- Usuwanie wiadomości
- Blokowanie użytkowników
- Przeglądanie zgłoszeń

### Użytkownik
- Wysyłanie wiadomości
- Korzystanie z kanałów
- Tworzenie DM
- Zgłaszanie użytkowników
- Edycja własnego profilu

## 🎨 Customizacja

### Zmiana kolorów (Dark/Light Theme)

Edytuj zmienne CSS w `static/css/app.css`:

```css
:root {
  --bg-primary: #0f0f13;
  --accent: #5865f2;
  --text-primary: #e8e8f0;
  /* ... */
}
```

### Zmiana logo

Zmień "💬" lub "NC" w szablonach oraz CSS:
- `templates/components/sidebar.html` - linia z `.server-icon`
- `templates/registration/login.html` - logo na stronie logowania

## 🐛 Troubleshooting

### WebSocket nie łączy się
- Sprawdź, że serwer używa Daphne, nie runserver
- Websoket URL to `ws://domain/ws/chat/channel_id/`
- W Render zaloguj się do shell i sprawdź logi: `python manage.py shell`

### Statyczne pliki nie ładują się (404)
```bash
python manage.py collectstatic --noinput
# Sprawdź STATIC_ROOT i MEDIA_ROOT w settings.py
```

### Baza danych nie znaleziona
```bash
python manage.py migrate
python manage.py createsuperuser
```

### Błąd przy wysyłaniu plików
- Sprawdź limit: `DATA_UPLOAD_MAX_MEMORY_SIZE` w settings.py
- Domyślnie 10MB
- Folder `media/` musi istnieć i być writable

## 📊 Monitoring

### Logi w Render
```bash
# W konsoli Render
tail -f render.log
```

### Baza danych
- SQLite (dev): `db.sqlite3`
- PostgreSQL (production): Render automatycznie tworzy

## 🚀 Optymalizacje dla produkcji

1. **Cache**
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
```

2. **Redis dla Channels** (zamiast InMemoryChannelLayer)
```bash
pip install channels-redis
# W settings.py:
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}
```

3. **Gzip kompresja**
```python
MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',
    ...
]
```

4. **HTTPS/SSL** (automatycznie na Render)

## 📝 API Endpoints

### Autentykacja
- `POST /accounts/register/` - Rejestracja
- `POST /accounts/login/` - Logowanie
- `GET /accounts/logout/` - Wylogowanie

### Użytkownicy
- `GET /accounts/profile/` - Mój profil
- `GET /accounts/profile/<username>/` - Profil użytkownika
- `POST /accounts/profile/edit/` - Edytuj profil
- `POST /accounts/status/` - Zmień status

### Chat
- `GET /chat/` - Główna strona
- `GET /chat/channel/<id>/` - Widok kanału
- `GET /chat/dm/<username>/` - Konwersacja DM
- `POST /chat/channel/create/` - Utwórz kanał
- `POST /chat/channel/<id>/send/` - Wyślij wiadomość

### WebSocket
- `ws://domain/ws/chat/<channel_id>/` - Kanał real-time
- `ws://domain/ws/dm/<username>/` - DM real-time

## 📞 Support

Problemy? Sprawdź:
1. Logi serwera
2. Konsolę przeglądarki (F12)
3. Panel administracyjny Django (/admin/)

---

**Stworzono z ❤️ dla społeczności Django**

Ostatnia aktualizacja: 2026-05-31
