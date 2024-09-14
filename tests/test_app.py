import pytest
from app import create_app

def test_get_users():
    app = create_app()
    client = app.test_client()
    response = client.get('/users')
    assert response.status_code == 200
    assert b'List of users' in response.data
