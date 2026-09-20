@echo off
cd backend
call .venv\Scripts\activate
python manage.py migrate
python manage.py seed_admin
python manage.py runserver
