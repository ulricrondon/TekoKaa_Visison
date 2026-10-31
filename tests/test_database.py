"""Testes isolados: não acessam nem apagam o banco real."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Carrega somente o módulo de persistência; dispensa câmera e MySQL nos testes.
mysql = types.ModuleType('mysql')
mysql.connector = types.ModuleType('mysql.connector')
dotenv = types.ModuleType('dotenv')
dotenv.load_dotenv = lambda *args: None
spec = importlib.util.spec_from_file_location('database_testado', Path(__file__).parents[1] / 'database.py')
database = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'mysql': mysql, 'mysql.connector': mysql.connector, 'dotenv': dotenv}):
    spec.loader.exec_module(database)


class HistoricoTest(unittest.TestCase):
    def setUp(self):
        self.snapshot = dict(monitoramento_ativo=True, analise_valida=True,
                             indice_saude_visual=80, area_verde=75, exg=0.5,
                             textura=2, status='SAUDÁVEL')
        self.banco = MagicMock()
        self.cursor = self.banco.cursor.return_value.__enter__.return_value
        self.conexao = patch.object(database, 'conexao')
        self.mock_conexao = self.conexao.start()
        self.addCleanup(self.conexao.stop)
        self.mock_conexao.return_value.__enter__.return_value = self.banco

    def test_ignora_analise_invalida_e_monitoramento_inativo(self):
        for campo in ('monitoramento_ativo', 'analise_valida'):
            snapshot = dict(self.snapshot, **{campo: False})
            self.assertFalse(database.registrar_se_devido(snapshot))
        self.mock_conexao.assert_not_called()

    def test_status_invalido_bloqueado_mesmo_com_flag_true(self):
        for status in ('AGUARDANDO', 'CÂMERA INDISPONÍVEL', 'PLANTA NÃO DETECTADA',
                       'ERRO NA ANÁLISE', 'ERRO', '', None):
            self.assertFalse(database.registrar_se_devido(dict(self.snapshot, status=status)))
        self.mock_conexao.assert_not_called()

    def test_primeira_analise_valida_e_salva(self):
        self.cursor.fetchone.side_effect = [(1000,), None]
        self.assertTrue(database.registrar_se_devido(self.snapshot))
        self.banco.commit.assert_called_once()
        sql, parametros = self.cursor.execute.call_args.args
        self.assertEqual(sql.count('%s'), len(parametros))
        self.assertEqual(self.cursor.execute.call_args.args[1],
                         (1000, 80.0, 75.0, 0.5, 2.0, 'SAUDÁVEL'))

    def test_intervalo_persistido_inclusive_apos_reinicio(self):
        for decorrido, esperado in ((3599999, False), (3600000, True)):
            with self.subTest(decorrido=decorrido):
                self.cursor.fetchone.side_effect = [(1000 + decorrido,), (1000,)]
                self.assertEqual(database.registrar_se_devido(self.snapshot), esperado)

    def test_falha_de_insert_nao_confirma_gravacao(self):
        self.cursor.fetchone.side_effect = [(1000,), None]
        self.cursor.execute.side_effect = [None, None, RuntimeError('offline')]
        with self.assertRaises(RuntimeError):
            database.registrar_se_devido(self.snapshot)
        self.banco.commit.assert_not_called()

    def test_limpeza_confirma_transacao(self):
        database.limpar_historico()
        self.cursor.execute.assert_called_once_with('DELETE FROM historico')
        self.banco.commit.assert_called_once()

    def test_listagem_preserva_registros(self):
        self.cursor.fetchall.return_value = [{'id': 7, 'timestamp': 1000}]
        self.assertEqual(database.listar_historico(), [{'id': 7, 'timestamp': 1000}])


if __name__ == '__main__':
    unittest.main()
