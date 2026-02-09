"""
Noise Cleaning Service

Provides algorithms to clean raw bathymetric data and compute difference masks.
"""

from dataclasses import dataclass
from typing import Literal, Optional
import numpy as np
from scipy import ndimage
from skimage import filters, morphology
import logging
import rasterio

logger = logging.getLogger(__name__)


@dataclass
class CleaningResult:
    """Result of a cleaning operation."""
    cleaned_grid: np.ndarray
    diff_mask: np.ndarray  # Boolean mask where |raw - cleaned| > threshold
    stats: dict


class CleaningService:
    """
    Service for cleaning bathymetric grids.
    """
    
    def clean_grid(
        self,
        grid: np.ndarray,
        method: Literal["median", "gaussian", "opening"] = "median",
        kernel_size: int = 3,
        threshold: float = 0.1,
    ) -> CleaningResult:
        """
        Clean the input grid using the specified method.
        
        Args:
            grid: Input depth grid (2D numpy array).
            method: Cleaning algorithm ("median", "gaussian", "opening").
            kernel_size: Size of the filter kernel/footprint.
            threshold: Depth difference threshold to consider a pixel "modified".
            
        Returns:
            CleaningResult containing cleaned grid and diff mask.
        """
        logger.info(f"Cleaning grid with method={method}, kernel_size={kernel_size}")
        
        # Handle nodata (assume NaN)
        mask = np.isnan(grid)
        filled_grid = grid.copy()
        
        # Simple fill for processing (replace NaNs with nearest VALID value or mean)
        # For now, replace with mean to avoid filter issues at edges
        if np.any(mask):
            mean_val = np.nanmean(grid)
            filled_grid[mask] = mean_val

        cleaned = filled_grid.copy()
        
        if method == "median":
            # Median filter removes salt-and-pepper noise (speckle)
            # footprint size = kernel_size
            cleaned = ndimage.median_filter(filled_grid, size=kernel_size)
            
        elif method == "gaussian":
            # Gaussian smoothing
            cleaned = filters.gaussian(filled_grid, sigma=kernel_size/2, preserve_range=True)
            
        elif method == "opening":
            # Morphological opening (erosion then dilation) removes bright spots (shoals)
            # BE CAREFUL: This removes shoals! Maybe closing is better for holes.
            # Usually for bathymetry we want to remove 'spikes' (deep or shallow).
            # Opening removes small light spots (shallow spikes in some renderings, or deep in others depending on sign).
            # Let's use disk footprint.
            footprint = morphology.disk(kernel_size)
            cleaned = morphology.opening(filled_grid, footprint)
            
        else:
            raise ValueError(f"Unknown cleaning method: {method}")
            
        # Restore NaNs
        cleaned[mask] = np.nan
        
        # Calculate difference mask
        # Diff = |Original - Cleaned| > threshold
        # Ignore NaNs in comparison
        diff = np.abs(grid - cleaned)
        diff_mask = diff > threshold
        diff_mask[mask] = False
        
        # Stats
        num_changed = np.sum(diff_mask)
        percent_changed = (num_changed / diff_mask.size) * 100
        
        stats = {
            "pixels_changed": int(num_changed),
            "percent_changed": float(percent_changed),
            "method": method,
            "kernel_size": kernel_size
        }
        
        return CleaningResult(cleaned_grid=cleaned, diff_mask=diff_mask, stats=stats)

    def to_geojson_diff(
        self,
        diff_mask: np.ndarray,
        transform: tuple,
    ) -> dict:
        """
        Convert the difference mask to a GeoJSON FeatureCollection of polygons.
        """
        from rasterio.features import shapes
        from shapely.geometry import shape, mapping
        
        # Normalize mask to uint8 for shapes()
        mask_uint8 = diff_mask.astype(np.uint8)
        
        features = []
        # Extract shapes where value is 1 (True)
        for geom, val in shapes(mask_uint8, mask=diff_mask, transform=transform):
            if val == 1:
                features.append({
                    "type": "Feature",
                    "geometry": geom,
                    "properties": {
                        "type": "modification"
                    }
                })
                
        return {
            "type": "FeatureCollection",
            "features": features
        }
