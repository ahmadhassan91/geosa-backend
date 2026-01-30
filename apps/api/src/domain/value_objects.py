"""
Domain Value Objects

Immutable value objects that represent domain concepts.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BoundingBox:
    """Geographic bounding box."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    
    def to_dict(self) -> dict[str, float]:
        return {
            "minx": self.min_x,
            "miny": self.min_y,
            "maxx": self.max_x,
            "maxy": self.max_y,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "BoundingBox":
        return cls(
            min_x=data["minx"],
            min_y=data["miny"],
            max_x=data["maxx"],
            max_y=data["maxy"],
        )
    
    def contains_point(self, x: float, y: float) -> bool:
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y
    
    @property
    def width(self) -> float:
        return self.max_x - self.min_x
    
    @property
    def height(self) -> float:
        return self.max_y - self.min_y
    
    @property
    def center(self) -> tuple[float, float]:
        return (
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
        )


@dataclass(frozen=True)
class FeatureVector:
    """
    Feature vector for a single cell/point.
    
    Used as input to anomaly detection models.
    """
    z_value: float
    z_score: float
    slope: float
    curvature: float
    roughness: float
    laplacian: float
    neighbor_mean: float
    neighbor_std: float
    density: float | None = None  # For point data
    
    def to_array(self) -> list[float]:
        """Convert to array for ML models."""
        values = [
            self.z_value,
            self.z_score,
            self.slope,
            self.curvature,
            self.roughness,
            self.laplacian,
            self.neighbor_mean,
            self.neighbor_std,
        ]
        if self.density is not None:
            values.append(self.density)
        return values
    
    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for explainability."""
        result = {
            "z_value": round(self.z_value, 4),
            "z_score": round(self.z_score, 4),
            "slope": round(self.slope, 4),
            "curvature": round(self.curvature, 4),
            "roughness": round(self.roughness, 4),
            "laplacian": round(self.laplacian, 4),
            "neighbor_mean": round(self.neighbor_mean, 4),
            "neighbor_std": round(self.neighbor_std, 4),
        }
        if self.density is not None:
            result["density"] = round(self.density, 4)
        return result


@dataclass(frozen=True)
class AnomalyScore:
    """
    Composite anomaly score from multiple detectors.
    
    Provides transparency into how the final score was calculated.
    """
    final_score: float  # 0.0 to 1.0
    isolation_forest_score: float | None = None
    zscore_score: float | None = None
    spatial_consistency_score: float | None = None
    
    # Which detectors flagged this as anomalous
    detectors_triggered: tuple[str, ...] = ()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "final_score": round(self.final_score, 4),
            "isolation_forest_score": (
                round(self.isolation_forest_score, 4) 
                if self.isolation_forest_score is not None else None
            ),
            "zscore_score": (
                round(self.zscore_score, 4)
                if self.zscore_score is not None else None
            ),
            "spatial_consistency_score": (
                round(self.spatial_consistency_score, 4)
                if self.spatial_consistency_score is not None else None
            ),
            "detectors_triggered": list(self.detectors_triggered),
        }


@dataclass(frozen=True)
class DatasetStats:
    """Statistics for a dataset."""
    z_min: float
    z_max: float
    z_mean: float
    z_std: float
    z_median: float
    valid_count: int
    nodata_count: int
    total_count: int
    
    @property
    def nodata_percentage(self) -> float:
        if self.total_count == 0:
            return 0.0
        return (self.nodata_count / self.total_count) * 100
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "z_min": round(self.z_min, 4),
            "z_max": round(self.z_max, 4),
            "z_mean": round(self.z_mean, 4),
            "z_std": round(self.z_std, 4),
            "z_median": round(self.z_median, 4),
            "valid_count": self.valid_count,
            "nodata_count": self.nodata_count,
            "total_count": self.total_count,
            "nodata_percentage": round(self.nodata_percentage, 2),
        }


@dataclass(frozen=True)
class ProcessingConfig:
    """Immutable snapshot of processing configuration."""
    config_hash: str
    isolation_forest_contamination: float
    isolation_forest_n_estimators: int
    zscore_threshold: float
    mad_threshold: float
    anomaly_threshold: float
    min_area_pixels: int
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "config_hash": self.config_hash,
            "isolation_forest_contamination": self.isolation_forest_contamination,
            "isolation_forest_n_estimators": self.isolation_forest_n_estimators,
            "zscore_threshold": self.zscore_threshold,
            "mad_threshold": self.mad_threshold,
            "anomaly_threshold": self.anomaly_threshold,
            "min_area_pixels": self.min_area_pixels,
        }
