"""
DRISHTRA Format Adapter Registry
Provides extensible, pluggable format adapters for computer vision datasets and model architectures.
Ensures new dataset formats (COCO, YOLO, VOC, CSV, IMAGE_FOLDER) and model types (ONNX, PyTorch, TorchScript)
can be registered and inspected without modifying core assurance logic.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type
from app.schemas.all_schemas import CanonicalImageRecord
from app.ingestion.dataset_parsers import DatasetParser
from app.ingestion.model_inspectors import ModelInspector

class BaseDatasetAdapter(ABC):
    format_name: str = "BASE"

    @abstractmethod
    def parse(self, raw_data: Any, dataset_id: str, contributor_id: Optional[str] = None) -> List[CanonicalImageRecord]:
        pass

class COCODatasetAdapter(BaseDatasetAdapter):
    format_name: str = "COCO"

    def parse(self, raw_data: Any, dataset_id: str, contributor_id: Optional[str] = None) -> List[CanonicalImageRecord]:
        if isinstance(raw_data, str):
            return DatasetParser.parse_coco_json(raw_data, dataset_id=dataset_id, contributor_id=contributor_id)
        elif isinstance(raw_data, dict):
            return DatasetParser.normalize_coco(raw_data, dataset_id=dataset_id, contributor_id=contributor_id)
        else:
            raise ValueError("COCO adapter requires file path string or dict data")

class YOLODatasetAdapter(BaseDatasetAdapter):
    format_name: str = "YOLO"

    def parse(self, raw_data: Any, dataset_id: str, contributor_id: Optional[str] = None) -> List[CanonicalImageRecord]:
        if isinstance(raw_data, list):
            return DatasetParser.normalize_yolo(raw_data, dataset_id=dataset_id, contributor_id=contributor_id)
        elif isinstance(raw_data, dict) and "images_dir" in raw_data and "labels_dir" in raw_data:
            return DatasetParser.parse_yolo_dir(
                raw_data["images_dir"],
                raw_data["labels_dir"],
                dataset_id=dataset_id,
                contributor_id=contributor_id
            )
        else:
            raise ValueError("YOLO adapter requires annotations list or dict with images_dir & labels_dir")

class BaseModelInspectorAdapter(ABC):
    format_name: str = "BASE"

    @abstractmethod
    def inspect(self, file_path_or_bytes: Any, model_name: str) -> Dict[str, Any]:
        pass

class ONNXModelAdapter(BaseModelInspectorAdapter):
    format_name: str = "ONNX"

    def inspect(self, file_path_or_bytes: Any, model_name: str) -> Dict[str, Any]:
        return ModelInspector.inspect_onnx_model(file_path_or_bytes, model_name=model_name)

class PyTorchModelAdapter(BaseModelInspectorAdapter):
    format_name: str = "PyTorch"

    def inspect(self, file_path_or_bytes: Any, model_name: str) -> Dict[str, Any]:
        return ModelInspector.inspect_pytorch_model(file_path_or_bytes, model_name=model_name)

class AdapterRegistry:
    _dataset_adapters: Dict[str, BaseDatasetAdapter] = {}
    _model_adapters: Dict[str, BaseModelInspectorAdapter] = {}

    @classmethod
    def register_dataset_adapter(cls, adapter: BaseDatasetAdapter):
        cls._dataset_adapters[adapter.format_name.upper()] = adapter

    @classmethod
    def register_model_adapter(cls, adapter: BaseModelInspectorAdapter):
        cls._model_adapters[adapter.format_name.upper()] = adapter

    @classmethod
    def get_dataset_adapter(cls, format_name: str) -> Optional[BaseDatasetAdapter]:
        return cls._dataset_adapters.get(format_name.upper())

    @classmethod
    def get_model_adapter(cls, format_name: str) -> Optional[BaseModelInspectorAdapter]:
        return cls._model_adapters.get(format_name.upper())

    @classmethod
    def supported_dataset_formats(cls) -> List[str]:
        return list(cls._dataset_adapters.keys())

    @classmethod
    def supported_model_formats(cls) -> List[str]:
        return list(cls._model_adapters.keys())

# Register default sovereign adapters
AdapterRegistry.register_dataset_adapter(COCODatasetAdapter())
AdapterRegistry.register_dataset_adapter(YOLODatasetAdapter())
AdapterRegistry.register_model_adapter(ONNXModelAdapter())
AdapterRegistry.register_model_adapter(PyTorchModelAdapter())
