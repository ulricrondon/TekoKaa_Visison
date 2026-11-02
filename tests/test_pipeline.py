import unittest
from unittest.mock import patch, sentinel

from agri_vision.pipeline import process_frame


class ProcessFrameTest(unittest.TestCase):
    def test_delega_processamento_e_preserva_retorno(self):
        retorno = (sentinel.frame_mapa_bgr, {"area_planta": 42.0})

        with patch(
            "agri_vision.pipeline.processar_com_plantcv", return_value=retorno
        ) as processar:
            resultado = process_frame(sentinel.frame)

        processar.assert_called_once_with(sentinel.frame)
        self.assertIs(resultado, retorno)


if __name__ == "__main__":
    unittest.main()
