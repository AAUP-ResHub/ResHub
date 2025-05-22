import pytest
from flask import session


def test_register_page_loads(client):
    """Test that the registration page loads correctly"""
    resp = client.get('/auth/register')
    assert resp.status_code == 200
    assert b'Create an Account' in resp.data
    assert b'Username' in resp.data
    assert b'Email' in resp.data
    assert b'Password' in resp.data
    assert b'Confirm Password' in resp.data


def test_login_page_loads(client):
    """Test that the login page loads correctly"""
    resp = client.get('/auth/login')
    assert resp.status_code == 200
    assert b'Login' in resp.data
    assert b'Email' in resp.data
    assert b'Password' in resp.data
    assert b'Remember me' in resp.data


def test_valid_registration(client):
    """Test user registration with valid data"""
    resp = client.post('/auth/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    
    assert resp.status_code == 200
    assert b'Registration successful' in resp.data


def test_registration_validation(client):
    """Test registration validation for duplicate email"""
    # Register a user first
    client.post('/auth/register', data={
        'username': 'testuser1',
        'email': 'duplicate@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    
    # Try to register with the same email
    resp = client.post('/auth/register', data={
        'username': 'testuser2',
        'email': 'duplicate@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    
    assert b'Email already registered' in resp.data


def test_login_success(client):
    """Test successful login"""
    # Register a user first
    client.post('/auth/register', data={
        'username': 'logintest', 
        'email': 'login@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    
    # Login
    resp = client.post('/auth/login', data={
        'email': 'login@example.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert resp.status_code == 200
    assert b'Logged in successfully' in resp.data


def test_bad_login_fails(client):
    """Test that invalid login credentials fail"""
    resp = client.post('/auth/login', data={
        'email': 'nonexistent@example.com',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    
    assert resp.status_code == 200
    assert b'Invalid email or password' in resp.data


def test_logout(client):
    """Test that users can logout"""
    # Register and login first
    client.post('/auth/register', data={
        'username': 'logouttest',
        'email': 'logout@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    
    client.post('/auth/login', data={
        'email': 'logout@example.com',
        'password': 'password123'
    })
    
    # Logout
    resp = client.get('/auth/logout', follow_redirects=True)
    
    assert resp.status_code == 200
    assert b'You have been logged out' in resp.data
