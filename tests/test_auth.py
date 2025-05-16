import pytest


@pytest.mark.xfail(reason="Auth not implemented yet")
def test_register_page_loads(client):
    resp = client.get('/auth/register')
    assert resp.status_code == 200


@pytest.mark.xfail(reason="Auth not implemented yet")
def test_login_page_loads(client):
    resp = client.get('/auth/login')
    assert resp.status_code == 200


@pytest.mark.xfail
def test_bad_login_fails(client):
    resp = client.post('/auth/login', data=dict(email="x@x", password="bad"))
    assert b"Invalid" in resp.data
