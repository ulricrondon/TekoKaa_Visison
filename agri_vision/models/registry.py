"""Registro de metadados e verificação de arquivos, sem carregar pesos."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agri_vision.crops import is_supported_crop


@dataclass(frozen=True)
class ModelInfo:
    model_id: str
    crop_id: str
    task: str
    version: str
    weights_path: str


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, ModelInfo] = {}

    def register(self, model: ModelInfo) -> None:
        """Registra metadados; rejeita IDs duplicados e culturas inválidas."""
        if model.model_id in self._models:
            raise ValueError(f"Modelo já registrado: {model.model_id}")
        if not is_supported_crop(model.crop_id):
            raise ValueError(f"Cultura inválida: {model.crop_id}")
        self._models[model.model_id] = model

    def get(self, model_id: str) -> ModelInfo | None:
        """Retorna os metadados ou None quando o ID não está registrado."""
        return self._models.get(model_id)

    def list_models(self) -> list[ModelInfo]:
        """Retorna uma nova lista de metadados na ordem de cadastro."""
        return list(self._models.values())

    def check_weights(
        self, model_id: str
    ) -> Literal["not_registered", "missing", "empty", "found"]:
        """Verifica somente a presença e o tamanho do arquivo de pesos.

        Caminhos relativos partem da raiz do projeto, não do diretório atual.
        'found' indica arquivo não vazio; não garante pesos válidos.
        Diretórios são tratados como arquivo ausente ('missing').
        """
        model = self.get(model_id)
        if model is None:
            return "not_registered"

        weights_path = Path(model.weights_path)
        if not weights_path.is_absolute():
            weights_path = Path(__file__).resolve().parents[2] / weights_path

        if not weights_path.is_file():
            return "missing"
        if weights_path.stat().st_size == 0:
            return "empty"
        return "found"
