from typing import TypeAlias, TypedDict

import numpy as np


class PipelineMetrics(TypedDict):
    area_verde: int | float
    area_planta: int | float
    verde_saudavel: int | float
    amarelo: int | float
    marrom: int | float
    escuro: int | float
    exg: int | float
    textura: int | float
    indice_saude_visual: int | float
    status: str
    cor_status: str


PipelineResult: TypeAlias = tuple[np.ndarray, PipelineMetrics]
