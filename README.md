Contact Application (Flask)

Features added for internship-ready resume:
- Registration (username/password)
- Login + session
- User-wise contacts (contacts belong to users)
- REST APIs protected with JWT (`/api/*`)
- JWT authentication (12h expiry)
- Pagination and search for contacts
- Simple RBAC: `role` on `User` (user/admin)

Quick setup

1. Create a virtualenv and install requirements:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements_extra.txt
```

2. Run the app:

```bash
python app.py
```

API examples

- Register: `POST /register` form data `username`, `password`
- Login: `POST /login` form data `username`, `password` -> returns token
- List contacts (API): `GET /api/contacts` with header `Authorization: Bearer <token>`

Notes

- This is a simple, minimal implementation meant to demonstrate backend features for a resume. Add templates or frontend as needed.
