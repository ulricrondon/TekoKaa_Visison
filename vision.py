import cv2
import numpy as np
from skimage.feature import local_binary_pattern


# ===============================
# SEGMENTAÇÃO DA VEGETAÇÃO
# ===============================

def segmentar_folha(frame):
    """
    Segmenta regiões verdes da imagem usando o espaço de cor HSV.
    Retorna:
    - folha: imagem original mantendo apenas as regiões verdes
    - mask: máscara binária da vegetação detectada
    """

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])

    mask = cv2.inRange(hsv, lower_green, upper_green)

    kernel = np.ones((5, 5), np.uint8)

    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    folha = cv2.bitwise_and(frame, frame, mask=mask)

    return folha, mask


# ===============================
# CÁLCULO DO ÍNDICE DE VERDE
# ===============================

def calcular_exg(frame, mask):
    """
    Calcula o índice ExG, usado para medir intensidade de verde.
    Fórmula:
    ExG = 2G - R - B
    """

    b, g, r = cv2.split(frame.astype("float"))

    exg = 2 * g - r - b
    valores = exg[mask > 0]

    if len(valores) == 0:
        return 0

    return float(np.mean(valores))


# ===============================
# CÁLCULO DE TEXTURA
# ===============================

def calcular_textura(frame, mask):
    """
    Calcula a variação de textura da folha usando LBP.
    """

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray[mask == 0] = 0

    lbp = local_binary_pattern(gray, 16, 2, method="uniform")
    valores = lbp[mask > 0]

    if len(valores) == 0:
        return 0

    return float(np.var(valores))


# ===============================
# ÁREA VERDE DETECTADA
# ===============================

def calcular_area_verde(mask):
    """
    Calcula a porcentagem da imagem detectada como área verde.
    """

    if mask.size == 0:
        return 0

    area_verde = (np.count_nonzero(mask) / mask.size) * 100

    return float(area_verde)


# ===============================
# CLASSIFICAÇÃO DA SAÚDE DA PLANTA
# ===============================

def classificar_saude(exg, textura):
    """
    Classifica a saúde da planta com base em regras simples.
    """

    if exg > 20 and textura < 500:
        return "SAUDÁVEL", "#10B981"

    elif exg > 5:
        return "ATENÇÃO", "#F59E0B"

    else:
        return "NÃO SAUDÁVEL", "#DC2626"


# ===============================
# PROCESSAMENTO COMPLETO DO FRAME
# ===============================

def processar_frame(frame):
    """
    Executa todo o fluxo de visão computacional em um frame:
    - segmentação
    - ExG
    - textura
    - área verde
    - classificação
    """

    folha, mask = segmentar_folha(frame)

    exg = calcular_exg(folha, mask)
    textura = calcular_textura(folha, mask)
    area_verde = calcular_area_verde(mask)

    status, cor_status = classificar_saude(exg, textura)

    resultado = {
        "exg": round(exg, 2),
        "textura": round(textura, 2),
        "area_verde": round(area_verde, 2),
        "status": status,
        "cor_status": cor_status
    }

    return folha, mask, resultado