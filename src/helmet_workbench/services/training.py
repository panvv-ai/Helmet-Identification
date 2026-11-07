from __future__ import annotations

from pathlib import Path

from helmet_workbench.db.database import Database
from helmet_workbench.db.models import ModelLabel, RecognitionModel
from helmet_workbench.ml.faceCnn import FaceCnnTrainer, TrainingOptions
from helmet_workbench.services.employees import EmployeeService
from helmet_workbench.services.storage import StorageLayout


class TrainingService:
    def __init__(
        self,
        database: Database,
        layout: StorageLayout,
        employees: EmployeeService,
        trainer: FaceCnnTrainer,
    ) -> None:
        self.database = database
        self.layout = layout
        self.employees = employees
        self.trainer = trainer

    def train(
        self,
        *,
        threshold: float = 0.7,
        options: TrainingOptions | None = None,
        progress: object | None = None,
    ) -> RecognitionModel:
        dataset = self.employees.trainingDataset()
        artifact_dir = self.layout.root / "models" / "face" / "pending"
        result = self.trainer.train(
            images=dataset.images,
            class_indices=dataset.class_indices,
            labels=dataset.labels,
            artifact_dir=artifact_dir,
            options=options,
            threshold=threshold,
        )
        with self.database.session() as session:
            has_active = session.query(RecognitionModel).filter_by(active=True).first() is not None
            model = RecognitionModel(
                name=f"人脸模型 {len(dataset.labels)} 类",
                artifact_path=self.layout.relative(result.artifact_dir),
                threshold=result.threshold,
                input_size=result.input_size,
                metrics=result.metrics,
                active=not has_active,
            )
            session.add(model)
            session.flush()
            final_dir = self.layout.root / "models" / "face" / model.id
            final_dir.parent.mkdir(parents=True, exist_ok=True)
            if artifact_dir.exists():
                artifact_dir.rename(final_dir)
            model.artifact_path = self.layout.relative(final_dir)
            for index, (employee_id, employee_no, employee_name) in enumerate(
                zip(
                    dataset.employee_ids,
                    dataset.employee_numbers,
                    dataset.employee_names,
                    strict=True,
                )
            ):
                session.add(
                    ModelLabel(
                        model_id=model.id,
                        class_index=index,
                        employee_id=employee_id,
                        employee_no=employee_no,
                        employee_name=employee_name,
                    )
                )
            session.flush()
            session.expunge(model)
            return model

    def activate(self, model_id: str) -> RecognitionModel:
        with self.database.session() as session:
            model = session.get(RecognitionModel, model_id)
            if model is None:
                raise LookupError("模型不存在")
            for candidate in session.query(RecognitionModel).all():
                candidate.active = candidate.id == model_id
            session.flush()
            session.expunge(model)
            return model

    def modelPath(self, model: RecognitionModel) -> Path:
        return self.layout.resolve(model.artifact_path)
