import unittest
from unittest.mock import patch
import sys
import types

# A câmera e o processamento de imagem não participam dos testes HTTP.
processor = types.ModuleType('plantcv_processor')
processor.processar_com_plantcv = lambda frame: None
with patch.dict(sys.modules, {'plantcv_processor': processor}):
    import app


class RotasHistoricoTest(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_consulta(self):
        with patch.object(app, 'listar_historico', return_value=[{'id': 1}]):
            resposta = self.client.get('/historico')
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json, [{'id': 1}])

    def test_falha_do_banco_nao_parece_historico_vazio(self):
        with patch.object(app, 'listar_historico', side_effect=RuntimeError('offline')):
            with self.assertLogs(app.app.logger, level='ERROR'):
                resposta = self.client.get('/historico')
        self.assertEqual(resposta.status_code, 503)
        self.assertIn('erro', resposta.json)

    def test_exclusao(self):
        with patch.object(app, 'limpar_historico') as limpar:
            resposta = self.client.delete('/historico')
        limpar.assert_called_once()
        self.assertEqual(resposta.status_code, 200)

    def test_falha_exclusao(self):
        with patch.object(app, 'limpar_historico', side_effect=RuntimeError('offline')):
            with self.assertLogs(app.app.logger, level='ERROR'):
                resposta = self.client.delete('/historico')
        self.assertEqual(resposta.status_code, 503)


if __name__ == '__main__':
    unittest.main()
