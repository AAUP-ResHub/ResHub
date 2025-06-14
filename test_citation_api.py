from app import create_app
from app.models import User

app = create_app()

with app.app_context():
    user = User.query.filter_by(username='testuser').first()
    assert user, 'Test user does not exist'
    with app.test_client() as c:
        # Simulate login via POST to /auth/login
        login_data = {'email': 'testuser@example.com', 'password': 'test'}
        login_resp = c.post('/auth/login', data=login_data, follow_redirects=True)
        print('Login status:', login_resp.status_code)
        print('Login response data:')
        print(login_resp.data.decode())
        # Now access the citation API
        resp = c.get('/citation/api/citation/3', follow_redirects=False)
        print('Status:', resp.status_code)
        print('Headers:', resp.headers)
        if resp.status_code == 302:
            print('Redirected to:', resp.headers.get('Location'))
            resp2 = c.get('/citation/api/citation/3', follow_redirects=True)
            print('Followed redirect status:', resp2.status_code)
            print('Followed redirect JSON:', resp2.get_json())
        else:
            print('JSON:', resp.get_json())
