from __future__ import annotations

from pathlib import Path

from helmet_workbench.config import Settings
from helmet_workbench.db.database import Database
from helmet_workbench.db.repository import Repository
from helmet_workbench.domain.models import FaceDetectorLike, HelmetDetectorLike
from helmet_workbench.ml.faceCnn import FaceCnnTrainer
from helmet_workbench.ml.helmetDetector import HelmetDetector
from helmet_workbench.services.analysis import AnalysisService
from helmet_workbench.services.camera import CameraService
from helmet_workbench.services.employees import EmployeeService
from helmet_workbench.services.jobs import JobManager
from helmet_workbench.services.recognition import RecognitionService
from helmet_workbench.services.storage import StorageLayout
from helmet_workbench.services.training import TrainingService
from helmet_workbench.vision.faceDetector import HaarFaceDetector


class AppServices:
    def __init__(
        self,
        settings: Settings,
        *,
        face_detector: FaceDetectorLike | None = None,
        helmet_detector: HelmetDetectorLike | None = None,
    ) -> None:
        settings.ensure_directories()
        self.settings = settings
        self.database = Database(settings.resolved_database_url)
        self.database.createAll()
        self.layout = StorageLayout(settings.storage_dir)
        self.repository = Repository()
        resolved_face_detector = face_detector
        if resolved_face_detector is None:
            resolved_face_detector = HaarFaceDetector()
        self.face_detector: FaceDetectorLike = resolved_face_detector
        if helmet_detector is None and settings.helmet_model_path.is_file():
            helmet_detector = HelmetDetector(settings.helmet_model_path)
        self.helmet_detector: HelmetDetectorLike | None = helmet_detector
        self.employees = EmployeeService(self.database, self.layout, self.face_detector)
        self.recognition = RecognitionService(self.layout)
        self.training = TrainingService(
            self.database,
            self.layout,
            self.employees,
            FaceCnnTrainer(),
        )
        self.jobs = JobManager(self.database)
        self.camera = CameraService(self)
        self.analysis = AnalysisService(self)

    @classmethod
    def forTesting(
        cls,
        root: Path,
        *,
        face_detector: FaceDetectorLike,
        helmet_detector: HelmetDetectorLike,
    ) -> AppServices:
        settings = Settings(
            storage_dir=root / "storage",
            testing=True,
        )
        return cls(
            settings,
            face_detector=face_detector,
            helmet_detector=helmet_detector,
        )

    def close(self) -> None:
        self.database.close()
