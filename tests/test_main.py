def test_index_page_loads(client):
    """Test that the index page loads successfully."""
    resp = client.get('/')
    assert resp.status_code == 200
    assert b"Welcome to ResHub" in resp.data


def test_about_page_loads(client):
    """Test that the about page loads successfully."""
    resp = client.get('/about')
    assert resp.status_code == 200
    assert b"About ResHub" in resp.data
