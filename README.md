# Веб-система файлового хранилища

## Развёртывание проекта

Инструкция предназначена для повторного развёртывания проекта на Windows с использованием PowerShell.

### 1. Необходимое программное обеспечение

До начала установки необходимо установить:

- Python 3.13;
- PostgreSQL 17 или выше;
- Node.js с npm;
- Git.

Проверка установки:

```powershell
python --version
node --version
npm --version
psql --version
```

Другие зависимости вручную устанавливать не требуется: зависимости Python устанавливаются из `backend/requirements.txt`, зависимости JavaScript — из `frontend/package.json`.

### 2. Получение проекта

```powershell
git clone <(https://github.com/LostFeniks/diplom)>
cd diplom
```

### 3. Настройка PostgreSQL

Запустите службу PostgreSQL и подключитесь к серверу:

```powershell
psql -U postgres -h localhost -p 5432
```

Создайте пользователя и базу данных:

```sql
CREATE USER admin WITH PASSWORD 'your_database_password';
CREATE DATABASE diplom OWNER admin;
GRANT ALL PRIVILEGES ON DATABASE diplom TO admin;
\q
```

Если пользователь `admin` или база `diplom` уже существуют, повторно создавать их не нужно.

### 4. Настройка `.env`

В корне проекта находится `.env.example`. Создайте рабочий `.env`:

```powershell
Copy-Item .env.example .env
```

Проверьте значения:

```env
DEBUG=True
SECRET_KEY=change-this-secret-key
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=diplom
DB_USER=admin
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432

MEDIA_ROOT=media
MAX_UPLOAD_SIZE=52428800

ADMIN_LOGIN=admin
ADMIN_PASSWORD=your_admin_password
ADMIN_EMAIL=admin@example.com
ADMIN_FULL_NAME=Администратор
```

Файл `.env` не должен загружаться в GitHub. В репозитории хранится только `.env.example`.

### 5. Установка backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Если PowerShell блокирует запуск скрипта активации:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 6. Создание таблиц базы данных

```powershell
python manage.py migrate
```

Проверка конфигурации:

```powershell
python manage.py check
```

### 7. Создание администратора

```powershell
python manage.py seed_admin
```

Команда создаёт административного пользователя, если его ещё нет, и создаёт каталог его файлового хранилища.

Данные администратора задаются в `.env` переменными `ADMIN_LOGIN` и `ADMIN_PASSWORD`. Например:

```env
ADMIN_LOGIN=admin
ADMIN_PASSWORD=your_admin_password
ADMIN_EMAIL=admin@example.com
ADMIN_FULL_NAME=Администратор
```

Используйте значение `ADMIN_PASSWORD` для первого входа.

### 8. Сборка frontend

**Перед запуском Django необходимо выполнить production-сборку frontend.** Это обязательный шаг для запуска приложения одним сервером.

Откройте новое окно PowerShell и выполните:

```powershell
cd frontend
npm install
npm run build
```

Сборка автоматически помещается в:

```text
backend/frontend_dist/
```

Этот каталог является результатом сборки и не хранится в Git-репозитории. Поэтому при повторном развёртывании `npm run build` необходимо выполнить до запуска Django.

### 9. Запуск приложения

После сборки frontend вернитесь в окно PowerShell с backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

Откройте в браузере:

```text
http://127.0.0.1:8000/
```

Django отдаёт одновременно React-приложение и REST API.

### 10. Запуск frontend в режиме разработки

Если требуется разрабатывать интерфейс отдельно от Django, используйте:

```powershell
cd frontend
npm install
npm run dev
```

После запуска Vite приложение доступно по адресу:

```text
http://localhost:5173/
```

Vite проксирует запросы `/api` на Django-сервер `http://127.0.0.1:8000`.

### 11. Проверка

После запуска проверьте:

1. открытие главной страницы;
2. регистрацию нового пользователя;
3. вход в систему;
4. загрузку файла;
5. скачивание файла;
6. переименование файла;
7. изменение комментария;
8. создание публичной ссылки;
9. удаление файла;
10. вход администратора;
11. просмотр списка пользователей;
12. изменение признака администратора;
13. удаление пользователя;
14. переход администратора в хранилище другого пользователя.

### 12. Тесты backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py test
```

### 13. Важные каталоги

После развёртывания создаются:

```text
backend/frontend_dist/   # production-сборка React
backend/media/           # физические файлы пользователей
```

Они не должны добавляться в Git-репозиторий.

### 14. API

Основные маршруты:

```text
POST   /api/auth/register/
POST   /api/auth/login/
POST   /api/auth/logout/
GET    /api/auth/me/

GET    /api/users/
DELETE /api/users/<id>/
PATCH  /api/users/<id>/admin/

GET    /api/files/
POST   /api/files/upload/
PATCH  /api/files/<id>/
DELETE /api/files/<id>/
GET    /api/files/<id>/download/
POST   /api/files/<id>/share/
GET    /api/shared/<token>/
```

Администратор может получить хранилище конкретного пользователя:

```text
GET /api/files/?user_id=<id>
```

### 15. Ограничение размера файла

Максимальный размер загружаемого файла задаётся переменной:

```env
MAX_UPLOAD_SIZE=52428800
```

Значение указывается в байтах. В приведённой конфигурации максимальный размер составляет 50 МБ.

### 16. Публичные ссылки

Публичная ссылка создаётся с использованием уникального UUID-токена и не содержит логин пользователя или исходное имя файла.

При локальном запуске ссылка содержит локальный адрес сервера. При размещении приложения на другом домене Django формирует URL на основе адреса текущего запроса.
