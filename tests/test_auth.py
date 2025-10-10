def test_login_logout(client):
    # Simula login con credenciales válidas
    response = client.post('/login', data={
        'usuario': 'admin',
        'clave': '1234'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Dashboard' in response.data or b'dashboard' in response.data

    # Simula logout
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'login' in response.data
