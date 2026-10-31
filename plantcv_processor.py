import cv2
import numpy as np
from plantcv import plantcv as pcv


def limitar_percentual(valor):
    return max(0, min(100, float(valor)))


def calcular_status_visual(percent_verde, percent_amarelo, percent_marrom, percent_escuro, area_planta):
    """
    Define o status visual da planta com base na composição de cores.
    Os percentuais são relativos à área da planta detectada.
    """

    if area_planta < 2:
        return "PLANTA NÃO DETECTADA"

    if percent_marrom >= 25:
        return "NÃO SAUDÁVEL"

    if percent_verde < 30:
        return "NÃO SAUDÁVEL"

    if percent_amarelo >= 25 or percent_marrom >= 10 or percent_escuro >= 35:
        return "ATENÇÃO"

    if percent_verde >= 60 and percent_amarelo < 25 and percent_marrom < 10:
        return "SAUDÁVEL"

    return "ATENÇÃO"


def calcular_indice_saude_visual(percent_verde, percent_amarelo, percent_marrom, percent_escuro, area_planta):
    """
    Índice inicial de saúde visual.
    Quanto maior a predominância de verde saudável, maior o índice.
    Tons amarelos, marrons e excesso de regiões escuras reduzem a pontuação.
    """

    if area_planta < 2:
        return 0

    indice = (
        percent_verde * 1.00
        - percent_amarelo * 0.45
        - percent_marrom * 0.85
        - percent_escuro * 0.25
    )

    return round(limitar_percentual(indice), 2)


def obter_cor_status(status):
    texto = (status or "").upper()

    if texto == "PLANTA NÃO DETECTADA":
        return "#64748B"

    if "NÃO" in texto or "NAO" in texto or "ERRO" in texto:
        return "#DC2626"

    if "ATEN" in texto:
        return "#F59E0B"

    if "SAUD" in texto:
        return "#10B981"

    return "#64748B"


def limpar_mascara(mascara, tamanho_minimo=250):
    """
    Remove ruídos pequenos e fecha pequenas falhas na máscara.
    """

    mascara = mascara.astype(np.uint8)

    kernel_pequeno = np.ones((3, 3), np.uint8)
    kernel_medio = np.ones((5, 5), np.uint8)

    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel_pequeno)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel_medio)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mascara, connectivity=8)

    mascara_filtrada = np.zeros_like(mascara)

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]

        if area >= tamanho_minimo:
            mascara_filtrada[labels == i] = 255

    return mascara_filtrada


def metricas_vazias(status):
    metricas = dict.fromkeys(("area_verde", "area_planta", "verde_saudavel", "amarelo",
                             "marrom", "escuro", "exg", "textura", "indice_saude_visual"), 0)
    metricas.update(status=status, cor_status=obter_cor_status(status))
    return metricas


def processar_com_plantcv(frame_bgr):
    """
    Recebe um frame BGR vindo do OpenCV.

    Retorna:
    - frame_mapa_bgr: imagem segmentada colorida por composição visual
    - metricas: indicadores calculados no backend
    """

    if (not isinstance(frame_bgr, np.ndarray) or frame_bgr.size == 0
            or frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3
            or frame_bgr.dtype != np.uint8):
        return np.zeros((480, 640, 3), dtype=np.uint8), metricas_vazias("ERRO NA ANÁLISE")

    try:
        frame_bgr = cv2.resize(frame_bgr, (640, 480))
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        altura, largura = frame_rgb.shape[:2]
        area_total = altura * largura

        # PlantCV: canais HSV para apoiar a análise visual.
        canal_s = pcv.rgb2gray_hsv(rgb_img=frame_rgb, channel="s")
        canal_v = pcv.rgb2gray_hsv(rgb_img=frame_rgb, channel="v")

        # OpenCV HSV para classificação por faixas de cor.
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)

        h = hsv[:, :, 0]

        # Classes exclusivas: um pixel escuro não conta também como verde/marrom.
        s, v = canal_s, canal_v
        mascara_verde = ((h >= 35) & (h <= 90) & (s >= 35) & (v >= 55)).astype(np.uint8) * 255
        mascara_amarelo = ((h >= 20) & (h < 35) & (s >= 35) & (v >= 55)).astype(np.uint8) * 255
        mascara_marrom = (
            ((h >= 5) & (h < 20) & (s >= 35) & (v >= 55) & (v <= 210))
            | ((h < 12) & (s >= 45) & (v >= 55) & (v <= 190))
        ).astype(np.uint8) * 255

        # A região candidata nasce das cores vegetais, não do fundo escuro.
        candidata = mascara_verde | mascara_amarelo | mascara_marrom
        candidata = limpar_mascara(candidata, tamanho_minimo=250)
        contornos, _ = cv2.findContours(candidata, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        regiao = np.zeros_like(candidata)
        cv2.drawContours(regiao, contornos, -1, 255, cv2.FILLED)
        # Sombras, inclusive pretas/cinzentas, só entram dentro desses contornos.
        mascara_escuro = ((v < 55) & (regiao > 0)).astype(np.uint8) * 255
        mascara_verde &= regiao
        mascara_amarelo &= regiao
        mascara_marrom &= regiao
        # Denominador: exatamente os pixels classificados, sem inventar cores
        # nas pequenas falhas preenchidas pelo fechamento morfológico.
        mascara_planta = mascara_verde | mascara_amarelo | mascara_marrom | mascara_escuro

        pixels_planta = cv2.countNonZero(mascara_planta)
        pixels_verde = cv2.countNonZero(mascara_verde)
        pixels_amarelo = cv2.countNonZero(mascara_amarelo)
        pixels_marrom = cv2.countNonZero(mascara_marrom)
        pixels_escuro = cv2.countNonZero(mascara_escuro)

        area_planta = (pixels_planta / area_total) * 100 if area_total > 0 else 0

        if pixels_planta > 0:
            percent_verde = (pixels_verde / pixels_planta) * 100
            percent_amarelo = (pixels_amarelo / pixels_planta) * 100
            percent_marrom = (pixels_marrom / pixels_planta) * 100
            percent_escuro = (pixels_escuro / pixels_planta) * 100
        else:
            percent_verde = 0
            percent_amarelo = 0
            percent_marrom = 0
            percent_escuro = 0

        # ExG calculado apenas dentro da região detectada como planta.
        r = frame_rgb[:, :, 0].astype(np.float32)
        g = frame_rgb[:, :, 1].astype(np.float32)
        b = frame_rgb[:, :, 2].astype(np.float32)

        exg_img = (2 * g) - r - b

        if pixels_planta > 0:
            exg_medio = float(np.mean(exg_img[mascara_planta > 0]))
        else:
            exg_medio = 0

        # Textura: desvio padrão em tons de cinza dentro da região da planta.
        gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)

        if pixels_planta > 0:
            textura = float(np.std(gray[mascara_planta > 0]))
        else:
            textura = 0

        indice_saude_visual = calcular_indice_saude_visual(
            percent_verde,
            percent_amarelo,
            percent_marrom,
            percent_escuro,
            area_planta
        )

        status = calcular_status_visual(
            percent_verde,
            percent_amarelo,
            percent_marrom,
            percent_escuro,
            area_planta
        )

        # Mapa colorido:
        # verde = saudável, amarelo = atenção, marrom = seco/risco, cinza = escuro/sombra.
        mapa_bgr = np.zeros_like(frame_bgr)
        mapa_bgr[mascara_verde > 0] = (60, 200, 60)
        mapa_bgr[mascara_amarelo > 0] = (0, 220, 255)
        mapa_bgr[mascara_marrom > 0] = (35, 95, 170)
        mapa_bgr[mascara_escuro > 0] = (90, 90, 90)

        original_suave = cv2.bitwise_and(frame_bgr, frame_bgr, mask=mascara_planta)
        frame_mapa_bgr = cv2.addWeighted(original_suave, 0.35, mapa_bgr, 0.65, 0)

        metricas = {
            # Mantém area_verde para compatibilidade com a dashboard atual.
            # Nesta fase, area_verde representa a área total de planta detectada.
            "area_verde": round(area_planta, 2),
            "area_planta": round(area_planta, 2),
            "verde_saudavel": round(percent_verde, 2),
            "amarelo": round(percent_amarelo, 2),
            "marrom": round(percent_marrom, 2),
            "escuro": round(percent_escuro, 2),
            "exg": round(exg_medio, 2),
            "textura": round(textura, 2),
            "indice_saude_visual": round(indice_saude_visual, 2),
            "status": status,
            "cor_status": obter_cor_status(status)
        }

        return frame_mapa_bgr, metricas

    except Exception as erro:
        print(f"[ERRO PlantCV] Falha no processamento: {erro}")

        status = "ERRO NA ANÁLISE"

        return np.zeros((480, 640, 3), dtype=np.uint8), metricas_vazias(status)
