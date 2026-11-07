from __future__ import annotations

from helmet_workbench.db.models import RecognitionModel
from helmet_workbench.ml.faceCnn import FaceModelBundle, loadFaceModel
from helmet_workbench.services.storage import StorageLayout


class RecognitionService:
    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout
        self._cache: dict[str, FaceModelBundle] = {}

    def load(self, model: RecognitionModel) -> FaceModelBundle:
        path = self.layout.resolve(model.artifact_path)
        if not path.is_dir():
            raise FileNotFoundError("人脸模型文件不存在")
        cached = self._cache.get(model.id)
        if cached is not None:
            return cached
        bundle = loadFaceModel(path)
        self._cache[model.id] = bundle
        return bundle
