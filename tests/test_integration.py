import unittest
from unittest.mock import patch, MagicMock
import cv2
import numpy as np
import plantcv_processor as processor
import app


def quadro(h=60, s=200, v=180):
    hsv = np.full((480, 640, 3), (h, s, v), np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


class PlantCVIntegracaoTest(unittest.TestCase):
    def test_cores_bgr_classificadas_sem_sobreposicao(self):
        for hue, value, classe, status in [(60, 180, 'verde_saudavel', 'SAUDÁVEL'),
                                         (25, 180, 'amarelo', 'NÃO SAUDÁVEL'),
                                         (10, 120, 'marrom', 'NÃO SAUDÁVEL')]:
            with self.subTest(classe=classe):
                mapa, m = processor.processar_com_plantcv(quadro(hue, v=value))
                self.assertEqual(m['status'], status)
                self.assertAlmostEqual(m[classe], 100, places=1)
                self.assertEqual(m['area_verde'], m['area_planta'])
                self.assertEqual(mapa.shape, (480, 640, 3))
                self.assertTrue(np.all(np.isfinite([m[k] for k in ('exg','textura','indice_saude_visual')])))

    def test_composicao_quatro_cores_soma_100_e_mapa_mjpeg(self):
        frame = np.full((480, 640, 3), 245, np.uint8)
        frame[80:400, 100:540] = quadro()[0, 0]
        frame[80:240, 320:540] = quadro(25)[0, 0]
        frame[240:400, 320:540] = quadro(10, v=120)[0, 0]
        frame[180:300, 180:260] = quadro(60, v=45)[0, 0]
        mapa, m = processor.processar_com_plantcv(frame)
        self.assertAlmostEqual(sum(m[k] for k in ('verde_saudavel','amarelo','marrom','escuro')), 100, delta=.03)
        self.assertGreater(m['escuro'], 0)
        self.assertTrue(all(m[k] > 0 for k in ('verde_saudavel','amarelo','marrom')))
        with patch.object(app, 'frame_segmentado_atual', mapa):
            stream = app.gerar_stream('segmentado')
            bloco = next(stream)
            stream.close()
        jpeg = bloco.split(b'\r\n\r\n', 1)[1].rstrip(b'\r\n')
        imagem = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(imagem.shape, mapa.shape)
        self.assertGreater(int(imagem[120,150,1]), int(imagem[120,150,0]))
        with patch.object(app, 'dados_atuais', app.montar_dados_processados(m)):
            dados = app.app.test_client().get('/dados').json
        for key in m:
            self.assertEqual(dados[key], m[key])
        self.assertTrue(dados['analise_valida'])

    def test_fundo_escuro_nao_vira_planta(self):
        for frame in (quadro(110, v=45), quadro(s=0, v=0), quadro(s=0, v=245)):
            _, m = processor.processar_com_plantcv(frame)
            self.assertEqual(m['status'], 'PLANTA NÃO DETECTADA')
            self.assertFalse(app.montar_dados_processados(m)['analise_valida'])

    def test_sombra_sem_saturacao_dentro_da_planta(self):
        frame = quadro()
        frame[150:300, 200:400] = 0
        _, m = processor.processar_com_plantcv(frame)
        self.assertGreater(m['escuro'], 9)
        self.assertAlmostEqual(m['escuro'] + m['verde_saudavel'], 100, delta=.02)

    def test_entrada_invalida_e_erro_plantcv(self):
        for frame in (None, np.zeros((0,0,3),np.uint8), np.zeros((10,10),np.uint8)):
            mapa, m = processor.processar_com_plantcv(frame)
            self.assertEqual(m['status'], 'ERRO NA ANÁLISE')
            self.assertEqual(mapa.shape, (480,640,3))
        with patch.object(processor.pcv, 'rgb2gray_hsv', side_effect=RuntimeError('teste')):
            _, m = processor.processar_com_plantcv(quadro())
        self.assertEqual(m['status'], 'ERRO NA ANÁLISE')

    def test_alias_e_metrica_nao_finita(self):
        m = {'area_planta': 30, 'area_verde': 99, 'status': 'SAUDÁVEL'}
        self.assertEqual(app.montar_dados_processados(m)['area_verde'], 30)
        with self.assertRaises(ValueError):
            app.montar_dados_processados(dict(m, exg=float('nan')))

    def test_toggle_descarta_frame_da_sessao_anterior(self):
        frame = quadro()
        camera = MagicMock()
        camera.read.return_value = True, frame
        client = app.app.test_client()
        def processar(_):
            client.post('/toggle_monitoramento')
            app.rodando = False
            return frame, {'status': 'SAUDÁVEL', 'area_planta': 80}
        with patch.multiple(app, camera=camera, rodando=True, monitoramento_ativo=True,
                            camera_disponivel=True, sessao_monitoramento=1,
                            dados_atuais=app.criar_dados_padrao(monitoramento=True,camera_ok=True)):
            with patch.object(app, 'iniciar_camera'), patch.object(app, 'processar_com_plantcv', side_effect=processar):
                app.loop_camera()
            self.assertFalse(app.dados_atuais['monitoramento_ativo'])
            self.assertFalse(app.dados_atuais['analise_valida'])
            self.assertEqual(app.dados_atuais['area_planta'], 0)
            resposta = client.post('/toggle_monitoramento').json
            self.assertEqual(resposta['status'], 'AGUARDANDO')
            self.assertFalse(resposta['analise_valida'])

    def test_camera_local_e_ip(self):
        for fonte in (0, 'http://127.0.0.1:8080/video'):
            with patch.object(app, 'CAMERA_SOURCE', fonte), patch.object(app.cv2, 'VideoCapture') as captura:
                app.abrir_camera()
                self.assertEqual(captura.call_args.args[0], fonte)
                self.assertEqual(len(captura.call_args.args), 2 if isinstance(fonte,int) else 1)


if __name__ == '__main__':
    unittest.main()
