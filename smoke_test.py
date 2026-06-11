#!/usr/bin/env python
"""Smoke test for the Flask Contact app"""
import requests
import json

base_url = 'http://127.0.0.1:5000'

# Test 1: Login
print('Test 1: Login with admin credentials')
session = requests.Session()
resp = session.post(base_url + '/login', data={'email': 'admin@example.com', 'password': 'admin123'}, allow_redirects=False)
print('  Status:', resp.status_code, '(expected 302 redirect)')
print('  Location:', resp.headers.get('Location', 'N/A'))

# Test 2: Index page (requires login)
print('\nTest 2: GET / (index page with login session)')
resp = session.get(base_url + '/')
print('  Status:', resp.status_code, '(expected 200)')
print('  Contains "Administrator":', 'Administrator' in resp.text)
print('  Contains contacts table:', '<table' in resp.text.lower())

# Test 3: Register page (public)
print('\nTest 3: GET /register (public page)')
resp = session.get(base_url + '/register')
print('  Status:', resp.status_code, '(expected 200)')
print('  Contains password field:', 'password' in resp.text.lower())

# Test 4: API endpoint - get contacts (without JWT - should fail)
print('\nTest 4: GET /api/contacts without JWT')
resp = session.get(base_url + '/api/contacts')
print('  Status:', resp.status_code, '(expected 401)')
if resp.text:
    data = json.loads(resp.text)
    print('  Message:', data.get('message', 'N/A'))

print('\n✓ Smoke tests complete. App is responding correctly.')
