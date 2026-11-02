import cv2
import math
import sys
import threading
import time
import atexit
import numpy as np

from flask import Flask, Response, jsonify, render_template

from agri_vision.pipeline import process_frame
from database import inicializar_banco, registrar_se_devido, listar_historico, limpar_historico


app = Flask(__name__)


# ===============================
# CONFIGURAÇÕES
# ===============================
# CAMERA_SOURCE pode receber:
# - número inteiro para webcam local: 0, 1, 2...
# - URL de câmera IP: "http://IP_DO_CELULAR:8080/video"
#
# Exemplo webcam local:
# CAMERA_SOURCE = 1
#
# Exemplo IP Webcam:
# CAMERA_SOURCE = "http://192.168.0.25:8080/video"

CAMERA_SOURCE = 0

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
CAMERA_FPS = 30
LOOP_DELAY_SECONDS = 0.03


# ===============================
# ESTADO GLOBAL
# ===============================

camera = None
camera_disponivel = False
monitoramento_ativo = False
sessao_monitoramento = 0
rodando = True

frame_original_atual = None
frame_segmentado_atual = None

lock = threading.Lock()
parar_historico = threading.Event()


def loop_historico():
    """Grava sem bloquear a captura da câmera e sem depender do navegador."""
    while not parar_historico.is_set():
        with lock:
            snapshot = dict(dados_atuais)
            snapshot['monitoramento_ativo'] = monitoramento_ativo
        try:
            registrar_se_devido(snapshot)
        except Exception:
            app.logger.exception('Falha ao salvar no MySQL; nova tentativa em 5 segundos.')
        parar_historico.wait(5)


# ===============================
# HELPERS DE ESTADO
# ===============================

def criar_dados_padrao(status="AGUARDANDO", cor_status="#64748B", monitoramento=False, camera_ok=False):
    return {
        "exg": 0,
        "textura": 0,
        "area_verde": 0,
        "area_planta": 0,
        "verde_saudavel": 0,
        "amarelo": 0,
        "marrom": 0,
        "escuro": 0,
        "indice_saude_visual": 0,
        "status": status,
        "cor_status": cor_status,
        "monitoramento_ativo": monitoramento,
        "camera_disponivel": camera_ok,
        "analise_valida": False
    }


def montar_dados_processados(metricas, monitoramento=True, camera_ok=True):
    status = metricas.get("status") or "AGUARDANDO"
    resultado = criar_dados_padrao(status=status, monitoramento=monitoramento, camera_ok=camera_ok)
    resultado.update(metricas)
    resultado["area_planta"] = metricas.get("area_planta", metricas.get("area_verde", 0))
    resultado["area_verde"] = resultado["area_planta"]
    for campo in ("area_planta", "area_verde", "verde_saudavel", "amarelo", "marrom",
                  "escuro", "exg", "textura", "indice_saude_visual"):
        resultado[campo] = float(resultado[campo])
        if not math.isfinite(resultado[campo]):
            raise ValueError(f"Métrica inválida: {campo}")
    resultado.update(status=status, monitoramento_ativo=monitoramento, camera_disponivel=camera_ok,
                     analise_valida=(monitoramento and camera_ok
                                     and status in ("SAUDÁVEL", "ATENÇÃO", "NÃO SAUDÁVEL")
                                     and metricas.get("analise_valida", True)))
    return resultado


dados_atuais = criar_dados_padrao()


# ===============================
# PLACEHOLDERS
# ===============================

def criar_frame_placeholder(texto="Monitoramento inativo", subtitulo="Clique no botão para iniciar"):
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    cv2.putText(frame, texto, (95, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (255, 255, 255), 2)
    cv2.putText(frame, subtitulo, (120, 275), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (180, 180, 180), 2)

    return frame


def criar_frame_segmentado_placeholder(texto="Segmentacao pausada"):
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    cv2.putText(frame, texto, (145, 245), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (120, 255, 120), 2)

    return frame


# ===============================
# CÂMERA
# ===============================

def abrir_camera():
    """
    Abre a câmera conforme o tipo configurado em CAMERA_SOURCE.

    - Se CAMERA_SOURCE for int, usa webcam local.
    - Se CAMERA_SOURCE for str, usa URL de câmera IP.
    """

    if isinstance(CAMERA_SOURCE, int):
        return cv2.VideoCapture(CAMERA_SOURCE, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)

    return cv2.VideoCapture(CAMERA_SOURCE)


def iniciar_camera():
    global camera
    global camera_disponivel
    global monitoramento_ativo
    global frame_original_atual
    global frame_segmentado_atual
    global dados_atuais

    camera = abrir_camera()

    if not camera.isOpened():
        print("[AVISO] Nenhuma câmera encontrada ou câmera IP indisponível.")

        camera_disponivel = False
        monitoramento_ativo = False

        with lock:
            frame_original_atual = criar_frame_placeholder(
                "Camera indisponivel",
                "Verifique webcam local ou URL da camera IP"
            )
            frame_segmentado_atual = criar_frame_segmentado_placeholder(
                "Segmentacao indisponivel"
            )

            dados_atuais = criar_dados_padrao(
                status="CÂMERA INDISPONÍVEL",
                cor_status="#64748B",
                monitoramento=False,
                camera_ok=False
            )

        return False

    if isinstance(CAMERA_SOURCE, int):
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        camera.set(cv2.CAP_PROP_FPS, CAMERA_FPS)

    camera_disponivel = True
    monitoramento_ativo = False

    with lock:
        frame_original_atual = criar_frame_placeholder()
        frame_segmentado_atual = criar_frame_segmentado_placeholder()

        dados_atuais = criar_dados_padrao(
            status="AGUARDANDO",
            cor_status="#64748B",
            monitoramento=False,
            camera_ok=True
        )

    print("[OK] Câmera encontrada. Monitoramento iniciado como inativo.")
    return True


# ===============================
# LOOP DA CÂMERA
# ===============================

def loop_camera():
    global frame_original_atual
    global frame_segmentado_atual
    global dados_atuais
    global rodando

    iniciar_camera()

    while rodando:
        with lock:
            ativo = monitoramento_ativo
            sessao = sessao_monitoramento
            camera_ok = camera_disponivel

        if not camera_ok:
            time.sleep(0.5)
            continue

        if not ativo:
            # Quando desativado, não sobrescreve os frames.
            # Assim a tela fica congelada no último frame capturado.
            time.sleep(0.2)
            continue

        try:
            ret, frame = camera.read()
        except cv2.error:
            ret, frame = False, None

        if not ret or frame is None:
            print("[AVISO] Não foi possível capturar frame.")

            with lock:
                if not monitoramento_ativo or sessao != sessao_monitoramento:
                    continue
                frame_original_atual = criar_frame_placeholder(
                    "Falha na captura",
                    "Verifique a camera"
                )
                frame_segmentado_atual = criar_frame_segmentado_placeholder(
                    "Segmentacao indisponivel"
                )

                dados_atuais = criar_dados_padrao(
                    status="CÂMERA INDISPONÍVEL",
                    cor_status="#DC2626",
                    monitoramento=monitoramento_ativo,
                    camera_ok=False
                )

            time.sleep(0.2)
            continue

        frame = cv2.flip(frame, 1)

        try:
            frame_segmentado, metricas = process_frame(frame)
            resultado = montar_dados_processados(metricas, monitoramento=True, camera_ok=True)

        except Exception as erro:
            print("[ERRO] Falha no processamento:", erro)

            frame_segmentado = criar_frame_segmentado_placeholder("Erro no processamento")

            resultado = criar_dados_padrao(
                status="ERRO NA ANÁLISE",
                cor_status="#DC2626",
                monitoramento=True,
                camera_ok=True
            )

        with lock:
            if not monitoramento_ativo or sessao != sessao_monitoramento:
                continue
            frame_original_atual = frame.copy()
            frame_segmentado_atual = frame_segmentado.copy()
            dados_atuais = resultado

        time.sleep(LOOP_DELAY_SECONDS)


# ===============================
# STREAM MJPEG
# ===============================

def gerar_stream(tipo="original"):
    while True:
        with lock:
            if tipo == "original":
                frame = frame_original_atual
            else:
                frame = frame_segmentado_atual

            if frame is None:
                if tipo == "original":
                    frame = criar_frame_placeholder()
                else:
                    frame = criar_frame_segmentado_placeholder()

            frame_copia = frame.copy()

        sucesso, buffer = cv2.imencode(".jpg", frame_copia)

        if not sucesso:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )
        time.sleep(1 / CAMERA_FPS)


# ===============================
# ROTAS
# ===============================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_original")
def video_original():
    return Response(
        gerar_stream("original"),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/video_segmentado")
def video_segmentado():
    return Response(
        gerar_stream("segmentado"),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/dados")
def dados():
    with lock:
        return jsonify(dados_atuais)


@app.route("/toggle_monitoramento", methods=["POST"])
def toggle_monitoramento():
    global monitoramento_ativo
    global dados_atuais
    global sessao_monitoramento

    with lock:
        if not camera_disponivel:
            monitoramento_ativo = False

            dados_atuais = criar_dados_padrao(
                status="CÂMERA INDISPONÍVEL",
                cor_status="#64748B",
                monitoramento=False,
                camera_ok=False
            )

            return jsonify(dados_atuais)

        monitoramento_ativo = not monitoramento_ativo
        sessao_monitoramento += 1
        if monitoramento_ativo:
            # Aguarda um frame novo; não reaproveita leitura da sessão anterior.
            dados_atuais = criar_dados_padrao(monitoramento=True, camera_ok=True)
        else:
            dados_atuais["monitoramento_ativo"] = False
            dados_atuais["analise_valida"] = False

        return jsonify(dados_atuais)


@app.route('/historico', methods=['GET'])
def historico():
    try:
        return jsonify(listar_historico())
    except Exception:
        app.logger.exception('Falha ao consultar histórico no MySQL.')
        return jsonify(erro='Histórico indisponível. Verifique a conexão com o MySQL.'), 503


@app.route('/historico', methods=['DELETE'])
def excluir_historico():
    try:
        limpar_historico()
        return jsonify(ok=True)
    except Exception:
        app.logger.exception('Falha ao limpar histórico no MySQL.')
        return jsonify(erro='Não foi possível limpar o histórico no MySQL.'), 503


# ===============================
# ENCERRAMENTO
# ===============================

def liberar_camera():
    global rodando
    global camera

    rodando = False
    parar_historico.set()

    if camera is not None:
        camera.release()
        print("[OK] Câmera liberada.")


atexit.register(liberar_camera)


# ===============================
# MAIN
# ===============================

if __name__ == "__main__":
    inicializar_banco()
    threading.Thread(target=loop_historico, daemon=True).start()
    thread_camera = threading.Thread(target=loop_camera)
    thread_camera.daemon = True
    thread_camera.start()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )
