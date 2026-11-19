# KanMind Backend

REST API for **KanMind**, a kanban board application. Built with Django and
Django REST framework. The matching vanilla JavaScript frontend is provided
separately by the Developer Akademie and is **not** part of this repository.

## Features

- Registration and login with email and password (token authentication)
- Boards with an owner and members, including task counters
- Tasks with status, priority, assignee, reviewer and due date
- Comments on tasks
- Dashboard lists: tasks assigned to me and tasks I review
- Email check to find registered users when adding board members
- Django admin for all models

## Requirements

- Python 3.10 or newer
- pip

## Getting started

```bash
# 1. Clone the repository
git clone https://github.com/ChrisNo86/KanMind.git
cd KanMind

# 2. Create and activate a virtual environment
python -m venv env
# Windows
env\Scripts\activate
# macOS / Linux
source env/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create the database
python manage.py migrate

# 5. Create the guest account used by the frontend's "Guest log in" button
python manage.py create_guest_user

# 6. (Optional) Create an admin account for http://127.0.0.1:8000/admin/
python manage.py createsuperuser

# 7. Start the development server
python manage.py runserver
```

The API is now available at `http://127.0.0.1:8000/api/`.

### Connecting the frontend

The frontend expects the API at `http://127.0.0.1:8000/api/` (see
`shared/js/config.js` in the frontend project). Start the frontend with the
VS Code **Live Server** extension (port 5500). CORS is enabled for
`http://127.0.0.1:5500` and `http://localhost:5500` in `core/settings.py`;
add your origin there if you use a different port.

## Project structure

```
core/            Project settings and central URL routing
auth_app/        Registration, login, email check
  api/           serializers, views, urls
  management/    create_guest_user command
kanban_app/      Boards, tasks, comments
  api/           serializers, views, urls, permissions
```

## API overview

All endpoints except registration and login require the header
`Authorization: Token <token>`.

| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/api/registration/` | Register, returns token | open |
| POST | `/api/login/` | Log in with email and password, returns token | open |
| GET | `/api/email-check/?email=` | Find a user by email | authenticated |
| GET | `/api/boards/` | Boards the user owns or is a member of | authenticated |
| POST | `/api/boards/` | Create a board (user becomes owner) | authenticated |
| GET | `/api/boards/{id}/` | Board with members and tasks | owner or member |
| PATCH | `/api/boards/{id}/` | Update title and members | owner or member |
| DELETE | `/api/boards/{id}/` | Delete board incl. tasks and comments | owner |
| GET | `/api/tasks/assigned-to-me/` | Tasks where the user is assignee | authenticated |
| GET | `/api/tasks/reviewing/` | Tasks where the user is reviewer | authenticated |
| POST | `/api/tasks/` | Create a task | board member |
| PATCH | `/api/tasks/{id}/` | Update a task (board cannot change) | board member |
| DELETE | `/api/tasks/{id}/` | Delete a task | task creator or board owner |
| GET | `/api/tasks/{id}/comments/` | Comments of a task (oldest first) | board member |
| POST | `/api/tasks/{id}/comments/` | Add a comment | board member |
| DELETE | `/api/tasks/{id}/comments/{comment_id}/` | Delete a comment | comment author |

## Special notes

- **Users:** Django's built-in `User` model is used. The email address is
  stored as the (unique) Django `username`; the `fullname` from registration
  is split into `first_name` (first word) and `last_name` (rest). The full
  name must contain at least two words.
- **Board owner as member:** the owner always has member rights on their
  board, even if they are not in the `members` list. `member_count` counts
  the entries of the `members` list only.
- **Assignee and reviewer** must be the board owner or a board member,
  otherwise the API responds with `400`.
- **Task creation:** a missing board returns `404`, a board the user is not a
  member of returns `403`.
- **Secret key / debug:** for local development defaults are used. For any
  deployment set the environment variables `DJANGO_SECRET_KEY` and
  `DJANGO_DEBUG=False`.
- The SQLite database is **not** part of the repository; run
  `python manage.py migrate` after cloning.

## Running the tests

```bash
python manage.py test
```

With coverage report:

```bash
pip install coverage
coverage run --source=auth_app,kanban_app,core --omit="*/migrations/*,*/tests/*" manage.py test
coverage report
```
