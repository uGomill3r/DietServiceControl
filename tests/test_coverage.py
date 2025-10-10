import os

def test_blueprints_have_tests():
    blueprints = ['auth', 'dashboard', 'semana', 'pagos', 'log']
    tested = [f.replace('test_', '').replace('.py', '') for f in os.listdir('tests') if f.startswith('test_')]
    for bp in blueprints:
        assert bp in tested, f"Blueprint {bp} no tiene test asociado"
