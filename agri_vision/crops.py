"""Catálogo de culturas agrícolas por identificador padronizado."""

CROPS: dict[str, str] = {
    "soja": "Soja",
    "cafe": "Café",
    "cacau": "Cacau",
}


def is_supported_crop(crop_id: str) -> bool:
    """Verifica o identificador exato, em minúsculas e sem acentos."""
    return crop_id in CROPS
