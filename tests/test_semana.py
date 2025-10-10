def test_semana_requires_login(client):
    response = client.get('/semana', follow_redirects=True)
    assert b'login' in response.data
