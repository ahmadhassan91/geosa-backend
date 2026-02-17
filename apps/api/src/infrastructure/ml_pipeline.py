"""
Machine Learning Pipeline

Core anomaly detection pipeline with full explainability.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import numpy as np
from scipy import ndimage
from scipy.stats import median_abs_deviation
from sklearn.ensemble import IsolationForest

from src.domain.entities import (
    Anomaly,
    AnomalyType,
    ConfidenceLevel,
    Dataset,
    ReviewDecision,
)
from src.infrastructure.config import ProcessingConfig


@dataclass
class FeatureResult:
    """Result of feature extraction for a single cell."""
    row: int
    col: int
    z_value: float
    z_score: float
    slope: float
    curvature: float
    roughness: float
    laplacian: float
    neighbor_mean: float
    neighbor_std: float
    is_valid: bool = True


@dataclass
class DetectionResult:
    """Result of anomaly detection."""
    anomaly_mask: np.ndarray  # Boolean mask of anomalies
    score_grid: np.ndarray  # Continuous scores 0-1
    detector_results: dict[str, np.ndarray]  # Per-detector results


class RasterProcessor:
    """Processes raster bathymetry data."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
    
    def load_raster(self, file_path: str) -> tuple[np.ndarray, dict]:
        """
        Load a GeoTIFF raster and return data + metadata.
        
        Returns:
            Tuple of (data array, metadata dict)
        """
        import rasterio
        
        from rasterio.warp import transform_bounds
        
        # Check if file exists (handle ephemeral storage)
        if not Path(file_path).exists():
            raise FileNotFoundError(
                f"Dataset file not found at {file_path}. This likely happened because the server restarted (ephemeral storage). Please upload the dataset again."
            )

        with rasterio.open(file_path) as src:
            data = src.read(1)  # Read first band
            nodata = src.nodata
            
            # Replace nodata with NaN
            if nodata is not None:
                data = data.astype(np.float64)
                data[data == nodata] = np.nan
            
            # Default to raw bounds
            bounds = {
                "minx": src.bounds.left, "miny": src.bounds.bottom,
                "maxx": src.bounds.right, "maxy": src.bounds.top
            }

            # Ensure bounds are in WGS84 (EPSG:4326) for proper map display
            if src.crs:
                try:
                    left, bottom, right, top = transform_bounds(
                        src.crs, "EPSG:4326", 
                        src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top
                    )
                    bounds = {
                        "minx": left, "miny": bottom, "maxx": right, "maxy": top
                    }
                except Exception:
                    # Keep default bounds if transform fails
                    pass

            # Sanity check: If bounds are huge (>180/90), they are likely projected coordinates
            # that failed to transform. Don't send them to the frontend to avoid map glitches.
            if abs(bounds["minx"]) > 180 or abs(bounds["miny"]) > 90:
                bounds = None

            metadata = {
                "crs": str(src.crs) if src.crs else None,
                "bounds": bounds,
                "width": src.width,
                "height": src.height,
                "resolution": (src.res[0], src.res[1]),
                "transform": list(src.transform),
            }
        
        return data, metadata
    
    def compute_statistics(self, data: np.ndarray) -> dict[str, Any]:
        """Compute basic statistics for the raster."""
        valid_data = data[~np.isnan(data)]
        
        if len(valid_data) == 0:
            return {
                "z_min": None,
                "z_max": None,
                "z_mean": None,
                "z_std": None,
                "z_median": None,
                "valid_count": 0,
                "nodata_count": int(np.sum(np.isnan(data))),
                "total_count": int(data.size),
            }
        
        return {
            "z_min": float(np.nanmin(data)),
            "z_max": float(np.nanmax(data)),
            "z_mean": float(np.nanmean(data)),
            "z_std": float(np.nanstd(data)),
            "z_median": float(np.nanmedian(data)),
            "valid_count": int(len(valid_data)),
            "nodata_count": int(np.sum(np.isnan(data))),
            "total_count": int(data.size),
        }


class FeatureExtractor:
    """Extracts features from bathymetry data for anomaly detection."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
    
    def extract_features(
        self, 
        data: np.ndarray,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> dict[str, np.ndarray]:
        """
        Extract all features from the raster data.
        
        Returns:
            Dictionary of feature name -> 2D array
        """
        features = {}
        
        # 1. Z-Score (how different from neighbors)
        if progress_callback:
            progress_callback(10, "Computing z-scores")
        features["z_score"] = self._compute_local_zscore(data)
        
        # 2. Slope (gradient magnitude)
        if progress_callback:
            progress_callback(20, "Computing slope")
        features["slope"] = self._compute_slope(data)
        
        # 3. Curvature (second derivative)
        if progress_callback:
            progress_callback(30, "Computing curvature")
        features["curvature"] = self._compute_curvature(data)
        
        # 4. Roughness (local std)
        if progress_callback:
            progress_callback(40, "Computing roughness")
        features["roughness"] = self._compute_roughness(data)
        
        # 5. Laplacian (edge detection)
        if progress_callback:
            progress_callback(50, "Computing Laplacian")
        features["laplacian"] = self._compute_laplacian(data)
        
        # 6. Neighbor statistics
        if progress_callback:
            progress_callback(55, "Computing neighborhood statistics")
        features["neighbor_mean"], features["neighbor_std"] = self._compute_neighbor_stats(data)
        
        return features
    
    def _compute_local_zscore(self, data: np.ndarray) -> np.ndarray:
        """Compute local z-score using neighborhood mean/std."""
        window_size = self.config.get("features", "neighborhood", "window_size", default=5)
        
        # Compute local mean and std
        kernel = np.ones((window_size, window_size)) / (window_size ** 2)
        
        # Handle NaN values
        valid_mask = ~np.isnan(data)
        data_filled = np.nan_to_num(data, nan=0)
        
        local_sum = ndimage.convolve(data_filled * valid_mask, kernel, mode='constant')
        local_count = ndimage.convolve(valid_mask.astype(float), kernel, mode='constant')
        local_count = np.maximum(local_count, 1e-10)  # Avoid division by zero
        
        local_mean = local_sum / local_count
        
        # Local variance
        local_sq_sum = ndimage.convolve((data_filled ** 2) * valid_mask, kernel, mode='constant')
        local_var = (local_sq_sum / local_count) - (local_mean ** 2)
        local_std = np.sqrt(np.maximum(local_var, 0))
        local_std = np.maximum(local_std, 1e-10)
        
        z_score = (data - local_mean) / local_std
        z_score[~valid_mask] = np.nan
        
        return z_score
    
    def _compute_slope(self, data: np.ndarray) -> np.ndarray:
        """Compute slope using Sobel operator."""
        # Sobel gradients
        dx = ndimage.sobel(data, axis=1)
        dy = ndimage.sobel(data, axis=0)
        
        # Slope magnitude
        slope = np.sqrt(dx**2 + dy**2)
        slope[np.isnan(data)] = np.nan
        
        return slope
    
    def _compute_curvature(self, data: np.ndarray) -> np.ndarray:
        """Compute curvature using second derivatives."""
        # Second derivatives
        d2x = ndimage.sobel(ndimage.sobel(data, axis=1), axis=1)
        d2y = ndimage.sobel(ndimage.sobel(data, axis=0), axis=0)
        
        # Mean curvature approximation
        curvature = (np.abs(d2x) + np.abs(d2y)) / 2
        curvature[np.isnan(data)] = np.nan
        
        return curvature
    
    def _compute_roughness(self, data: np.ndarray) -> np.ndarray:
        """Compute roughness as local standard deviation."""
        window_size = self.config.get("features", "roughness", "window_size", default=3)
        
        # Similar to z-score computation
        kernel = np.ones((window_size, window_size)) / (window_size ** 2)
        valid_mask = ~np.isnan(data)
        data_filled = np.nan_to_num(data, nan=0)
        
        local_sum = ndimage.convolve(data_filled * valid_mask, kernel, mode='constant')
        local_count = ndimage.convolve(valid_mask.astype(float), kernel, mode='constant')
        local_count = np.maximum(local_count, 1e-10)
        
        local_mean = local_sum / local_count
        
        local_sq_sum = ndimage.convolve((data_filled ** 2) * valid_mask, kernel, mode='constant')
        local_var = (local_sq_sum / local_count) - (local_mean ** 2)
        roughness = np.sqrt(np.maximum(local_var, 0))
        roughness[~valid_mask] = np.nan
        
        return roughness
    
    def _compute_laplacian(self, data: np.ndarray) -> np.ndarray:
        """Compute Laplacian (edge detector)."""
        kernel_size = self.config.get("features", "laplacian", "kernel_size", default=3)
        
        laplacian = ndimage.laplace(np.nan_to_num(data, nan=0))
        laplacian[np.isnan(data)] = np.nan
        
        return laplacian
    
    def _compute_neighbor_stats(
        self, data: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute neighborhood mean and std."""
        window_size = self.config.get("features", "neighborhood", "window_size", default=5)
        
        kernel = np.ones((window_size, window_size)) / (window_size ** 2)
        valid_mask = ~np.isnan(data)
        data_filled = np.nan_to_num(data, nan=0)
        
        local_sum = ndimage.convolve(data_filled * valid_mask, kernel, mode='constant')
        local_count = ndimage.convolve(valid_mask.astype(float), kernel, mode='constant')
        local_count = np.maximum(local_count, 1e-10)
        
        neighbor_mean = local_sum / local_count
        
        local_sq_sum = ndimage.convolve((data_filled ** 2) * valid_mask, kernel, mode='constant')
        local_var = (local_sq_sum / local_count) - (neighbor_mean ** 2)
        neighbor_std = np.sqrt(np.maximum(local_var, 0))
        
        neighbor_mean[~valid_mask] = np.nan
        neighbor_std[~valid_mask] = np.nan
        
        return neighbor_mean, neighbor_std


class AnomalyDetector:
    """Detects anomalies using multiple methods."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
    
    def detect(
        self,
        data: np.ndarray,
        features: dict[str, np.ndarray],
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> DetectionResult:
        """
        Run all enabled detectors and combine results.
        
        Returns:
            DetectionResult with masks and scores
        """
        detector_results = {}
        
        # 1. Isolation Forest
        if self.config.get("anomaly_detection", "isolation_forest", "enabled", default=True):
            if progress_callback:
                progress_callback(60, "Running Isolation Forest")
            detector_results["isolation_forest"] = self._run_isolation_forest(data, features)
        
        # 2. Z-Score / MAD detector
        if self.config.get("anomaly_detection", "zscore", "enabled", default=True):
            if progress_callback:
                progress_callback(70, "Running Z-score detector")
            detector_results["zscore"] = self._run_zscore_detector(features["z_score"])
        
        # 3. Combine scores
        if progress_callback:
            progress_callback(80, "Combining detector scores")
        
        final_score = self._combine_scores(detector_results, data.shape)
        
        # 4. Create binary mask
        threshold = self.config.anomaly_threshold
        anomaly_mask = final_score > threshold
        anomaly_mask[np.isnan(data)] = False
        
        return DetectionResult(
            anomaly_mask=anomaly_mask,
            score_grid=final_score,
            detector_results=detector_results,
        )
    
    def _run_isolation_forest(
        self, 
        data: np.ndarray, 
        features: dict[str, np.ndarray]
    ) -> np.ndarray:
        """Run Isolation Forest on feature vectors."""
        config = self.config.isolation_forest_config
        
        # Prepare feature matrix
        valid_mask = ~np.isnan(data)
        
        feature_names = ["z_score", "slope", "curvature", "roughness", "laplacian"]
        feature_list = []
        
        for name in feature_names:
            if name in features:
                feature_list.append(features[name][valid_mask])
        
        if not feature_list:
            return np.zeros(data.shape)
        
        X = np.column_stack(feature_list)
        
        # Handle any remaining NaN/Inf
        X = np.nan_to_num(X, nan=0, posinf=0, neginf=0)
        
        # Train Isolation Forest
        model = IsolationForest(
            n_estimators=config.get("n_estimators", 100),
            contamination=config.get("contamination", 0.1),
            max_samples=config.get("max_samples", "auto"),
            random_state=config.get("random_state", 42),
            n_jobs=config.get("n_jobs", -1),
        )
        
        # Get anomaly scores (higher = more anomalous)
        # Isolation Forest returns -1 for anomalies, 1 for normal
        # decision_function returns negative for anomalies
        scores = -model.fit(X).decision_function(X)
        
        # Normalize to 0-1 range
        scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-10)
        
        # Map back to grid
        result = np.zeros(data.shape)
        result[valid_mask] = scores
        
        return result
    
    def _run_zscore_detector(self, z_score: np.ndarray) -> np.ndarray:
        """Detect anomalies using z-score threshold."""
        config = self.config.zscore_config
        
        if config.get("use_mad", True):
            # Use Median Absolute Deviation (more robust)
            valid = z_score[~np.isnan(z_score)]
            if len(valid) == 0:
                return np.zeros(z_score.shape)
            
            median = np.median(valid)
            mad = median_abs_deviation(valid, nan_policy="omit")
            threshold = config.get("mad_threshold", 3.5)
            
            # Modified z-score
            if mad < 1e-10:
                scores = np.abs(z_score - median)
            else:
                scores = np.abs(z_score - median) / mad
            
            # Normalize to 0-1
            scores = np.minimum(scores / threshold, 1.0)
        else:
            # Simple z-score
            threshold = config.get("threshold", 3.0)
            scores = np.abs(z_score) / threshold
            scores = np.minimum(scores, 1.0)
        
        scores = np.nan_to_num(scores, nan=0)
        return scores
    
    def _combine_scores(
        self, 
        detector_results: dict[str, np.ndarray],
        shape: tuple[int, int]
    ) -> np.ndarray:
        """Combine detector scores using configured weights."""
        weights = self.config.get("scoring", "weights", default={
            "isolation_forest": 0.5,
            "zscore": 0.3,
            "spatial_consistency": 0.2,
        })
        
        combined = np.zeros(shape)
        total_weight = 0
        
        for detector, score in detector_results.items():
            weight = weights.get(detector, 0.1)
            combined += weight * score
            total_weight += weight
        
        if total_weight > 0:
            combined /= total_weight
        
        return combined


class AnomalyPolygonizer:
    """Converts anomaly masks to GeoJSON polygons."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
    
    def polygonize(
        self,
        score_grid: np.ndarray,
        metadata: dict,
        detector_results: dict[str, np.ndarray],
        data: np.ndarray,
        config_thresholds: dict,
    ) -> list[Anomaly]:
        """
        Convert anomaly score grid to polygon anomalies.
        
        Returns:
            List of Anomaly entities with full explainability
        """
        from shapely.geometry import shape, mapping
        from shapely.ops import unary_union
        import rasterio.features
        from rasterio.transform import Affine
        
        threshold = self.config.anomaly_threshold
        # Increase default min_area to 25 to reduce noise
        min_area = self.config.get("outputs", "polygons", "min_area_pixels", default=25)
        
        # Create binary mask
        mask = score_grid > threshold
        mask[np.isnan(score_grid)] = False
        
        # OPTIMIZATION: Remove small noise BEFORE labeling
        # This reduces component count from Millions to Thousands
        if min_area > 1:
            mask = ndimage.binary_opening(mask, structure=np.ones((3,3)))
        
        # Label connected components
        labeled, num_features = ndimage.label(mask)
        objects = ndimage.find_objects(labeled)
        
        if num_features == 0:
            return []
        
        # Create transform from metadata
        transform = Affine(*metadata.get("transform", [1, 0, 0, 0, -1, 0]))
        resolution = metadata.get("resolution", (1.0, 1.0))
        
        # Prepare transformer (Optimization: do this once)
        transformer = None
        source_crs = metadata.get("crs")
        if source_crs and "EPSG:4326" not in str(source_crs) and "4326" not in str(source_crs):
            try:
                import pyproj
                transformer = pyproj.Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
            except Exception:
                pass
        
        anomalies = []
        max_anomalies = 2000  # Safety limit for noisy datasets (e.g. landcover)
        
        max_scan_count = 2000 # Strict limit for responsiveness
        for label_id, obj_slice in enumerate(objects, start=1):
            if label_id > max_scan_count:
                 print(f"Warning: Scan limit reached ({max_scan_count} components). Stopping.")
                 break
                 
            if obj_slice is None:
                continue
                
            if len(anomalies) >= max_anomalies:
                print(f"Warning: hit max anomaly limit ({max_anomalies}). Stopping polygonization.")
                break
            
            # Extract local slice to optimize processing speed
            sub_labeled = labeled[obj_slice]
            component_mask = sub_labeled == label_id
            pixel_count = np.sum(component_mask)
            
            # Skip small components
            if pixel_count < min_area:
                continue
            
            # Adjust transform for local slice
            y_offset = obj_slice[0].start
            x_offset = obj_slice[1].start
            sub_transform = transform * Affine.translation(x_offset, y_offset)
            
            # Get polygon geometry
            shapes_gen = rasterio.features.shapes(
                component_mask.astype(np.uint8),
                mask=component_mask,
                transform=sub_transform,
            )
            
            geom = None
            for geom_dict, val in shapes_gen:
                if val == 1:
                    geom = shape(geom_dict)
                    break
            
            if geom is None:
                continue
                
            # Reproject to WGS84 if needed
            if transformer:
                try:
                    from shapely.ops import transform as shapely_transform
                    geom = shapely_transform(transformer.transform, geom)
                except Exception:
                    pass

            # Simplify if configured
            simplify_tol = self.config.get("outputs", "polygons", "simplify_tolerance", default=0.0001)
            if simplify_tol > 0:
                # If using degrees (EPSG:4326), use a very small tolerance
                # If using meters (Projected), use a larger one
                if source_crs and ("EPSG:4326" in str(source_crs) or "4326" in str(source_crs)):
                    # 0.0001 degrees is ~11 meters, good for simplification
                    geom = geom.simplify(simplify_tol)
                else:
                    # Projected systems (meters)
                    geom = geom.simplify(simplify_tol * 10.0) if simplify_tol < 0.1 else geom.simplify(simplify_tol)
            
            # Calculate centroid
            centroid = geom.centroid
            
            # Calculate area in square meters (approximate)
            area = pixel_count * abs(resolution[0] * resolution[1])
            
            # Extract local statistics - Using Slicing
            local_scores = score_grid[obj_slice][component_mask]
            
            sub_data = data[obj_slice]
            local_depths = sub_data[component_mask]
            local_depths = local_depths[~np.isnan(local_depths)]
            
            # Determine which detectors flagged this region
            detectors_triggered = []
            detector_scores = {}
            for detector, scores in detector_results.items():
                # Slice logic
                detector_local = scores[obj_slice][component_mask]
                mean_score = np.nanmean(detector_local)
                detector_scores[detector] = float(mean_score)
                if mean_score > threshold:
                    detectors_triggered.append(detector)
            
            # Calculate average probability
            mean_prob = float(np.nanmean(local_scores))
            
            # Determine confidence level
            conf_thresholds = self.config.confidence_thresholds
            if mean_prob >= conf_thresholds.get("high", 0.8):
                confidence = ConfidenceLevel.HIGH
            elif mean_prob >= conf_thresholds.get("medium", 0.5):
                confidence = ConfidenceLevel.MEDIUM
            else:
                confidence = ConfidenceLevel.LOW
            
            # Calculate QC priority
            qc_priority = self._calculate_priority(
                mean_prob=mean_prob,
                area=area,
                local_depths=local_depths,
            )
            
            # Determine anomaly type
            anomaly_type = self._infer_anomaly_type(detector_scores, local_depths, data)
            
            # Build explanation
            explanation = {
                "primary_reason": self._get_primary_reason(detector_scores, detectors_triggered),
                "features": detector_scores,
                "thresholds": config_thresholds,
                "detector_flags": detectors_triggered,
                "pixel_count": int(pixel_count),
            }
            
            # Create anomaly entity
            anomaly = Anomaly(
                id=uuid4(),
                run_id=uuid4(),  # Will be set later
                centroid_x=centroid.x,
                centroid_y=centroid.y,
                geometry=mapping(geom),
                area_sq_meters=float(area),
                anomaly_type=anomaly_type,
                anomaly_probability=mean_prob,
                confidence_level=confidence,
                qc_priority=qc_priority,
                explanation=explanation,
                local_depth_mean=float(np.mean(local_depths)) if len(local_depths) > 0 else None,
                local_depth_std=float(np.std(local_depths)) if len(local_depths) > 0 else None,
                neighbor_count=int(pixel_count),
                review_decision=ReviewDecision.PENDING,
                created_at=datetime.utcnow(),
            )
            
            anomalies.append(anomaly)

            
        # Sort by priority
        anomalies.sort(key=lambda a: a.qc_priority, reverse=True)
        
        return anomalies
    
    def _calculate_priority(
        self,
        mean_prob: float,
        area: float,
        local_depths: np.ndarray,
    ) -> float:
        """Calculate QC priority score."""
        weights = self.config.get("scoring", "priority", default={
            "score_weight": 0.5,
            "depth_variance_weight": 0.3,
            "cluster_weight": 0.2,
        })
        
        # Score component
        score_priority = mean_prob * weights.get("score_weight", 0.5)
        
        # Depth variance component (higher variance = higher priority)
        if len(local_depths) > 1:
            depth_var = np.std(local_depths) / (np.mean(np.abs(local_depths)) + 1e-10)
            depth_priority = min(depth_var, 1.0) * weights.get("depth_variance_weight", 0.3)
        else:
            depth_priority = 0
        
        # Area component (larger areas = higher priority for review)
        area_normalized = min(area / 100, 1.0)  # Normalize to ~100 sq meters
        area_priority = area_normalized * weights.get("cluster_weight", 0.2)
        
        return score_priority + depth_priority + area_priority
    
    def _infer_anomaly_type(
        self,
        detector_scores: dict[str, float],
        local_depths: np.ndarray,
        full_data: np.ndarray,
    ) -> AnomalyType:
        """Infer the type of anomaly based on characteristics."""
        if len(local_depths) == 0:
            return AnomalyType.UNKNOWN
        
        # Compare local depth to global
        global_median = np.nanmedian(full_data)
        local_mean = np.mean(local_depths)
        
        # Spike: significantly shallower than surroundings
        if local_mean > global_median * 1.5:
            return AnomalyType.SPIKE
        
        # Hole: significantly deeper than surroundings
        if local_mean < global_median * 0.6:
            return AnomalyType.HOLE
        
        # High isolation forest score often indicates noise
        if detector_scores.get("isolation_forest", 0) > 0.8:
            return AnomalyType.NOISE_BAND
        
        return AnomalyType.UNKNOWN
    
    def _get_primary_reason(
        self, 
        detector_scores: dict[str, float],
        detectors_triggered: list[str],
    ) -> str:
        """Generate human-readable primary reason."""
        if not detectors_triggered:
            return "Score exceeded threshold"
        
        # Find highest scoring detector
        max_detector = max(detector_scores.items(), key=lambda x: x[1])
        
        reasons = {
            "isolation_forest": "Unusual feature combination detected by Isolation Forest",
            "zscore": "Depth significantly different from neighbors",
            "spatial_consistency": "Inconsistent with surrounding surface",
        }
        
        return reasons.get(max_detector[0], f"Flagged by {max_detector[0]}")


class HeatmapGenerator:
    """Generates heatmap raster outputs."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
    
    def generate(
        self,
        score_grid: np.ndarray,
        metadata: dict,
        output_path: Path,
    ) -> str:
        """Generate heatmap GeoTIFF."""
        import rasterio
        from rasterio.transform import Affine
        
        # Get config
        nodata = self.config.get("outputs", "heatmap", "nodata_value", default=-9999)
        
        # Replace NaN with nodata
        output_data = np.where(np.isnan(score_grid), nodata, score_grid)
        
        # Create transform
        transform = Affine(*metadata.get("transform", [1, 0, 0, 0, -1, 0]))
        
        # Write output
        profile = {
            "driver": "GTiff",
            "dtype": "float32",
            "width": score_grid.shape[1],
            "height": score_grid.shape[0],
            "count": 1,
            "crs": metadata.get("crs", "EPSG:4326"),
            "transform": transform,
            "nodata": nodata,
            "compress": "lzw",
        }
        
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(output_data.astype(np.float32), 1)
        
        return str(output_path)


class MLPipeline:
    """Main ML pipeline orchestrator."""
    
    VERSION = "0.1.0"
    
    def __init__(self, config: ProcessingConfig, output_dir: Path):
        self.config = config
        self.output_dir = output_dir
        
        self.processor = RasterProcessor(config)
        self.extractor = FeatureExtractor(config)
        self.detector = AnomalyDetector(config)
        self.polygonizer = AnomalyPolygonizer(config)
        self.heatmap_gen = HeatmapGenerator(config)
    
    async def run_analysis(
        self,
        dataset: Dataset,
        run_id,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> tuple[list[Anomaly], dict[str, str]]:
        """
        Run full analysis pipeline on a dataset.
        
        Args:
            dataset: Dataset entity to analyze
            run_id: UUID of the run
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (list of anomalies, dict of output paths)
        """
        import time
        import sys
        import json

        def log_step(msg):
            print(f"[PIPELINE {run_id}] {time.strftime('%H:%M:%S')} - {msg}")
            sys.stdout.flush()

        log_step(f"Starting analysis for dataset: {dataset.file_path}")

        # 1. Load data
        if progress_callback:
            progress_callback(5, "Loading raster data")
        
        log_step("Loading raster data...")
        data, metadata = self.processor.load_raster(dataset.file_path)
        log_step(f"Raster loaded. Shape: {data.shape}")
        
        # 2. Extract features
        log_step("Extracting features...")
        features = self.extractor.extract_features(data, progress_callback)
        log_step("Features extracted.")
        
        # 3. Detect anomalies
        log_step("Detecting anomalies...")
        detection_result = self.detector.detect(data, features, progress_callback)
        log_step(f"Detection complete. Score grid shape: {detection_result.score_grid.shape}")
        
        # 4. Create output directory
        run_output_dir = self.output_dir / str(run_id)
        run_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 5. Generate heatmap
        if progress_callback:
            progress_callback(85, "Generating heatmap")
        
        log_step("Generating heatmap...")
        heatmap_path = run_output_dir / "anomaly_heatmap.tif"
        self.heatmap_gen.generate(detection_result.score_grid, metadata, heatmap_path)
        log_step(f"Heatmap saved to {heatmap_path}")
        
        # 6. Polygonize anomalies
        if progress_callback:
            progress_callback(90, "Creating anomaly polygons")
        
        log_step("Polygonizing anomalies...")
        config_thresholds = {
            "anomaly_threshold": self.config.anomaly_threshold,
            "zscore_threshold": self.config.zscore_config.get("threshold", 3.0),
            "isolation_contamination": self.config.isolation_forest_config.get("contamination", 0.1),
        }
        
        anomalies = self.polygonizer.polygonize(
            score_grid=detection_result.score_grid,
            metadata=metadata,
            detector_results=detection_result.detector_results,
            data=data,
            config_thresholds=config_thresholds,
        )
        log_step(f"Polygonization complete. Found {len(anomalies)} anomalies.")
        
        # Set run_id on all anomalies
        for anomaly in anomalies:
            anomaly.run_id = run_id
        
        # 7. Export GeoJSON
        if progress_callback:
            progress_callback(95, "Exporting GeoJSON")
        
        log_step("Exporting GeoJSON...")
        geojson_path = run_output_dir / "anomalies.geojson"
        geojson = {
            "type": "FeatureCollection",
            "features": [a.to_geojson_feature() for a in anomalies],
        }
        with open(geojson_path, "w") as f:
            json.dump(geojson, f, indent=2)
        log_step("GeoJSON exported.")
        
        # 8. Return results
        output_paths = {
            "heatmap": str(heatmap_path),
            "geojson": str(geojson_path),
        }
        
        if progress_callback:
            progress_callback(100, "Analysis complete")
        
        log_step("Analysis pipeline finished successfully.")
        return anomalies, output_paths
