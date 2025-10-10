def test_dashboard_requires_login(client):
    response = client.get('/dashboard', follow_redirects=True)
    assert b'login' in response.data
