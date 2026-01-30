"""
ML Pipeline Tests
"""

import numpy as np
import pytest

from src.infrastructure.config import ProcessingConfig


class TestFeatureExtractor:
    """Tests for feature extraction."""
    
    def test_z_score_computation(self):
        """Test local z-score computation."""
        from src.infrastructure.ml_pipeline import FeatureExtractor
        
        config = ProcessingConfig()
        extractor = FeatureExtractor(config)
        
        # Create simple test data
        data = np.ones((10, 10)) * 50.0  # Uniform depth
        data[5, 5] = 100.0  # Single spike
        
        features = extractor.extract_features(data)
        
        assert "z_score" in features
        assert features["z_score"].shape == data.shape
        
        # Spike should have high z-score
        spike_zscore = features["z_score"][5, 5]
        background_zscore = features["z_score"][0, 0]
        assert abs(spike_zscore) > abs(background_zscore)
    
    def test_slope_computation(self):
        """Test slope computation."""
        from src.infrastructure.ml_pipeline import FeatureExtractor
        
        config = ProcessingConfig()
        extractor = FeatureExtractor(config)
        
        # Create sloped surface
        x = np.arange(10)
        y = np.arange(10)
        X, Y = np.meshgrid(x, y)
        data = X.astype(float) * 2  # Linear slope
        
        features = extractor.extract_features(data)
        
        assert "slope" in features
        # Slope should be non-zero (except at edges)
        assert np.nanmax(features["slope"]) > 0


class TestAnomalyDetector:
    """Tests for anomaly detection."""
    
    def test_isolation_forest_detection(self):
        """Test Isolation Forest anomaly detection."""
        from src.infrastructure.ml_pipeline import AnomalyDetector, FeatureExtractor
        
        config = ProcessingConfig()
        extractor = FeatureExtractor(config)
        detector = AnomalyDetector(config)
        
        # Create data with embedded anomaly
        data = np.random.normal(50, 1, (50, 50))
        data[25, 25] = 100  # Obvious spike
        
        features = extractor.extract_features(data)
        result = detector.detect(data, features)
        
        assert result.score_grid.shape == data.shape
        assert result.anomaly_mask.shape == data.shape
        
        # Spike location should have higher score
        spike_score = result.score_grid[25, 25]
        mean_score = np.nanmean(result.score_grid)
        assert spike_score > mean_score
    
    def test_score_range(self):
        """Test that scores are in [0, 1] range."""
        from src.infrastructure.ml_pipeline import AnomalyDetector, FeatureExtractor
        
        config = ProcessingConfig()
        extractor = FeatureExtractor(config)
        detector = AnomalyDetector(config)
        
        data = np.random.normal(50, 5, (30, 30))
        features = extractor.extract_features(data)
        result = detector.detect(data, features)
        
        valid_scores = result.score_grid[~np.isnan(result.score_grid)]
        assert np.all(valid_scores >= 0)
        assert np.all(valid_scores <= 1)


class TestDatasetStats:
    """Tests for dataset statistics."""
    
    def test_statistics_computation(self):
        """Test basic statistics computation."""
        from src.infrastructure.ml_pipeline import RasterProcessor
        
        config = ProcessingConfig()
        processor = RasterProcessor(config)
        
        data = np.array([
            [10, 20, 30],
            [40, 50, 60],
            [70, 80, 90],
        ], dtype=float)
        
        stats = processor.compute_statistics(data)
        
        assert stats["z_min"] == 10
        assert stats["z_max"] == 90
        assert stats["z_mean"] == 50
        assert stats["valid_count"] == 9
        assert stats["nodata_count"] == 0
    
    def test_statistics_with_nodata(self):
        """Test statistics with NoData values."""
        from src.infrastructure.ml_pipeline import RasterProcessor
        
        config = ProcessingConfig()
        processor = RasterProcessor(config)
        
        data = np.array([
            [10, 20, np.nan],
            [40, 50, 60],
            [70, np.nan, 90],
        ], dtype=float)
        
        stats = processor.compute_statistics(data)
        
        assert stats["valid_count"] == 7
        assert stats["nodata_count"] == 2
        assert stats["z_min"] == 10
        assert stats["z_max"] == 90
