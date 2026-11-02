import os
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from agri_vision.models.registry import ModelInfo, ModelRegistry


class ModelRegistryTest(unittest.TestCase):
    def setUp(self):
        self.registry = ModelRegistry()
        # Metadados exclusivos dos testes; não representam modelos disponíveis.
        self.model = ModelInfo(
            model_id="teste-soja",
            crop_id="soja",
            task="classificacao",
            version="1.0",
            weights_path="test-fixtures/pesos-inexistentes.bin",
        )

    def test_registro_inicia_vazio(self):
        self.assertEqual(self.registry.list_models(), [])

    def test_cadastro_e_consulta_preservam_metadados(self):
        for crop_id in ("soja", "cafe", "cacau"):
            with self.subTest(crop_id=crop_id):
                model = replace(self.model, model_id=f"teste-{crop_id}", crop_id=crop_id)
                self.registry.register(model)
                self.assertEqual(self.registry.get(model.model_id), model)

    def test_consulta_identificador_desconhecido(self):
        self.assertIsNone(self.registry.get("desconhecido"))

    def test_identificador_duplicado_nao_substitui_modelo(self):
        self.registry.register(self.model)
        with self.assertRaises(ValueError):
            self.registry.register(replace(self.model, version="2.0", crop_id="cafe"))
        self.assertEqual(self.registry.get(self.model.model_id), self.model)
        self.assertEqual(self.registry.list_models(), [self.model])

    def test_cultura_invalida_nao_registra_modelo(self):
        for crop_id in ("milho", "", "Soja", "café"):
            with self.subTest(crop_id=crop_id):
                with self.assertRaises(ValueError):
                    self.registry.register(replace(self.model, crop_id=crop_id))
                self.assertIsNone(self.registry.get(self.model.model_id))
                self.assertEqual(self.registry.list_models(), [])

    def test_listagem_preserva_cadastros(self):
        second = replace(self.model, model_id="teste-soja-2", version="2.0")
        self.registry.register(self.model)
        self.registry.register(second)
        models = self.registry.list_models()
        self.assertEqual(models, [self.model, second])
        models.clear()
        self.assertEqual(self.registry.list_models(), [self.model, second])


class ModelWeightsTest(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parents[1]
        temporary = TemporaryDirectory(dir=self.project_root)
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.file = self.directory / "arquivo-de-teste.dat"
        self.registry = ModelRegistry()
        self.model = ModelInfo(
            model_id="teste-arquivo",
            crop_id="soja",
            task="classificacao",
            version="1.0",
            weights_path=str(self.file),
        )

    def test_modelo_nao_registrado(self):
        self.assertEqual(self.registry.check_weights("desconhecido"), "not_registered")

    def test_arquivo_ausente(self):
        self.registry.register(self.model)
        self.assertEqual(self.registry.check_weights(self.model.model_id), "missing")

    def test_arquivo_vazio(self):
        self.file.touch()
        self.registry.register(self.model)
        self.assertEqual(self.registry.check_weights(self.model.model_id), "empty")

    def test_arquivo_encontrado_por_caminho_absoluto(self):
        # Conteúdo arbitrário: encontrar um arquivo não valida seus pesos.
        self.file.write_text("arquivo de teste, não um modelo", encoding="utf-8")
        self.registry.register(self.model)
        self.assertEqual(self.registry.check_weights(self.model.model_id), "found")

    def test_caminho_relativo_independe_do_diretorio_atual(self):
        self.file.write_text("arquivo de teste", encoding="utf-8")
        self.registry.register(replace(
            self.model, weights_path=str(self.file.relative_to(self.project_root))
        ))
        previous_directory = Path.cwd()
        try:
            os.chdir(self.directory)
            self.assertEqual(self.registry.check_weights(self.model.model_id), "found")
        finally:
            os.chdir(previous_directory)

    def test_diretorio_nao_e_arquivo_de_pesos(self):
        self.registry.register(replace(self.model, weights_path=str(self.directory)))
        self.assertEqual(self.registry.check_weights(self.model.model_id), "missing")


if __name__ == "__main__":
    unittest.main()
