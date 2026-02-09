"""
Contour Generation Service

Generates smoothed depth contours from bathymetric grids.
"""

from dataclasses import dataclass
from typing import Literal
import numpy as np
from shapely.geometry import LineString, mapping
from shapely.ops import linemerge
import logging

logger = logging.getLogger(__name__)


@dataclass
class ContourLine:
    """Represents a depth contour."""
    depth: float
    geometry: LineString
    length_meters: float
    is_closed: bool


class ContourGenerator:
    """
    Generates and smooths depth contours from bathymetric grids.
    
    Uses scikit-image for contour extraction and implements
    Chaikin corner-cutting for smooth cartographic output.
    """
    
    def __init__(
        self,
        contour_interval: float = 5.0,
        smoothing_iterations: int = 3,
        min_length_pixels: int = 10,
        max_levels: int = 50,
    ):
        """
        Args:
            contour_interval: Depth interval between contours (meters)
            smoothing_iterations: Number of Chaikin smoothing passes
            min_length_pixels: Minimum contour length to keep
            max_levels: Maximum number of contour levels to generate
        """
        self.interval = contour_interval
        self.smoothing_iterations = smoothing_iterations
        self.min_length = min_length_pixels
        self.max_levels = max_levels
    
    def generate(
        self,
        depth_grid: np.ndarray,
        transform: tuple,
        depth_range: tuple[float, float] = None,
    ) -> list[ContourLine]:
        """
        Generate smoothed contours from a depth grid.
        
        Args:
            depth_grid: 2D numpy array of depths
            transform: Affine transform tuple
            depth_range: Optional (min, max) depth range for contours
            
        Returns:
            List of ContourLine objects
        """
        from skimage.measure import find_contours
        from rasterio.transform import Affine
        
        affine = Affine(*transform) if not isinstance(transform, Affine) else transform
        
        # Determine contour levels
        valid_depths = depth_grid[~np.isnan(depth_grid)]
        if len(valid_depths) == 0:
            return []
        
        if depth_range:
            min_depth, max_depth = depth_range
        else:
            min_depth = float(np.nanmin(valid_depths))
            max_depth = float(np.nanmax(valid_depths))
        
        # Generate contour levels
        # Round to nearest interval
        start_level = np.floor(min_depth / self.interval) * self.interval
        end_level = np.ceil(max_depth / self.interval) * self.interval
        levels = np.arange(start_level, end_level + self.interval, self.interval)
        
        # Limit number of levels to prevent hanging
        if len(levels) > self.max_levels:
            logger.info(f"Reducing contour levels from {len(levels)} to {self.max_levels}")
            # Sample levels evenly across the range
            indices = np.linspace(0, len(levels) - 1, self.max_levels, dtype=int)
            levels = levels[indices]
        
        logger.info(f"Generating {len(levels)} contours from {min_depth:.1f}m to {max_depth:.1f}m")
        
        contours = []
        
        for i, level in enumerate(levels):
            if i % 10 == 0:
                logger.debug(f"Processing level {i+1}/{len(levels)}: {level}m")
            
            # Find contours at this level
            raw_contours = find_contours(depth_grid, level)
            
            for coords in raw_contours:
                # Filter short contours
                if len(coords) < self.min_length:
                    continue
                
                # Apply Chaikin smoothing
                smoothed_coords = self._chaikin_smooth(coords, self.smoothing_iterations)
                
                # Convert pixel coords to CRS coords
                world_coords = []
                for row, col in smoothed_coords:
                    x, y = affine * (col, row)
                    world_coords.append((x, y))
                
                if len(world_coords) < 2:
                    continue
                
                line = LineString(world_coords)
                
                # Check if closed
                is_closed = line.is_ring
                
                contours.append(ContourLine(
                    depth=float(level),
                    geometry=line,
                    length_meters=line.length,
                    is_closed=is_closed,
                ))
        
        return contours
    
    def _chaikin_smooth(self, coords: np.ndarray, iterations: int) -> np.ndarray:
        """
        Apply Chaikin corner-cutting algorithm for smooth curves.
        
        This produces aesthetically pleasing contours suitable for charts.
        """
        result = coords.copy()
        
        for _ in range(iterations):
            new_coords = []
            n = len(result)
            
            for i in range(n - 1):
                p0 = result[i]
                p1 = result[i + 1]
                
                # Quarter points
                q = 0.75 * p0 + 0.25 * p1
                r = 0.25 * p0 + 0.75 * p1
                
                new_coords.append(q)
                new_coords.append(r)
            
            # Add last point if not a closed loop
            if not np.allclose(result[0], result[-1]):
                new_coords.append(result[-1])
            
            result = np.array(new_coords)
        
        return result
    
    def to_geojson(self, contours: list[ContourLine]) -> dict:
        """Convert contours to GeoJSON FeatureCollection."""
        features = []
        
        for c in contours:
            features.append({
                "type": "Feature",
                "geometry": mapping(c.geometry),
                "properties": {
                    "depth": round(c.depth, 1),
                    "length_m": round(c.length_meters, 1),
                    "is_closed": c.is_closed,
                },
            })
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "contour_interval": self.interval,
                "smoothing_iterations": self.smoothing_iterations,
                "total_contours": len(features),
            },
        }


def generate_chart_contours(
    depth_grid: np.ndarray,
    transform: tuple,
    interval: float = 5.0,
    smoothing: int = 3,
) -> dict:
    """
    Convenience function to generate chart-ready contours.
    
    Returns GeoJSON FeatureCollection.
    """
    generator = ContourGenerator(
        contour_interval=interval,
        smoothing_iterations=smoothing,
    )
    contours = generator.generate(depth_grid, transform)
    return generator.to_geojson(contours)
