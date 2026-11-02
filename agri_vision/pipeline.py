from plantcv_processor import processar_com_plantcv

from agri_vision.contracts import PipelineResult


def process_frame(frame) -> PipelineResult:
    return processar_com_plantcv(frame)
