import unittest

from agri_vision.crops import CROPS, is_supported_crop


class CropsTest(unittest.TestCase):
    def test_catalogo_inicial(self):
        self.assertEqual(CROPS, {
            "soja": "Soja",
            "cafe": "Café",
            "cacau": "Cacau",
        })

    def test_culturas_suportadas(self):
        for crop_id in ("soja", "cafe", "cacau"):
            with self.subTest(crop_id=crop_id):
                self.assertTrue(is_supported_crop(crop_id))

    def test_culturas_desconhecidas(self):
        for crop_id in ("milho", "", "trigo"):
            with self.subTest(crop_id=crop_id):
                self.assertFalse(is_supported_crop(crop_id))

    def test_exige_identificador_padronizado(self):
        for crop_id in ("Soja", "CAFE", "café", " cafe", "cacau "):
            with self.subTest(crop_id=crop_id):
                self.assertFalse(is_supported_crop(crop_id))


if __name__ == "__main__":
    unittest.main()
