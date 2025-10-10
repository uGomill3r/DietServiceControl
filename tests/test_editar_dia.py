def test_editar_dia_post(client):
    # Simula envío de formulario con datos válidos
    response = client.post('/editar_dia', data={
        'fecha': '09-10-2025',
        'almuerzo': 'on',
        'cena': 'on',
        'entregado_almuerzo': 'on',
        'entregado_cena': 'on',
        'obs_pedido': 'Pedido completo',
        'obs_entrega': 'Entrega sin problemas',
        'feriado': 'on'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Semana' in response.data or b'semana' in response.data
