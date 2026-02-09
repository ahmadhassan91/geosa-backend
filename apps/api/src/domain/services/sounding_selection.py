"""
Sounding Selection Service

AI-powered sounding selection for chart compilation.
Implements shoal-biased, density-based selection algorithms.
"""

from dataclasses import dataclass
from typing import Literal
import numpy as np
from shapely.geometry import Point, mapping


@dataclass
class SoundingPoint:
    """Represents a selected sounding."""
    x: float  # Longitude or Easting
    y: float  # Latitude or Northing
    depth: float
    selection_type: str  # 'shoal', 'deep', 'representative'
    cell_id: tuple[int, int]


class SoundingSelector:
    """
    Selects representative soundings from a bathymetric grid.
    
    Implements IHO-aligned selection logic:
    - Shoal-biased: Always preserve minimum depths (safety critical)
    - Density-based: Control output density by cell size
    - Scale-aware: Adjust density based on target chart scale
    """
    
    def __init__(
        self,
        cell_size_meters: float = 100.0,
        selection_mode: Literal["shoal", "deep", "representative"] = "shoal",
    ):
        """
        Args:
            cell_size_meters: Grid cell size for density control
            selection_mode: 'shoal' (min depth), 'deep' (max), or 'representative' (median)
        """
        self.cell_size = cell_size_meters
        self.mode = selection_mode
    
    def select_from_grid(
        self,
        depth_grid: np.ndarray,
        transform: tuple,
        nodata_value: float = None,
    ) -> list[SoundingPoint]:
        """
        Select soundings from a depth grid.
        
        Args:
            depth_grid: 2D numpy array of depths (negative = below water)
            transform: Affine transform tuple (a, b, c, d, e, f)
            nodata_value: Value representing no-data pixels
            
        Returns:
            List of SoundingPoint objects
        """
        from rasterio.transform import Affine
        
        affine = Affine(*transform) if not isinstance(transform, Affine) else transform
        
        # Get pixel resolution
        pixel_size_x = abs(affine.a)
        pixel_size_y = abs(affine.e)
        
        # Calculate cell dimensions in pixels
        cell_pixels_x = max(1, int(self.cell_size / pixel_size_x))
        cell_pixels_y = max(1, int(self.cell_size / pixel_size_y))
        
        rows, cols = depth_grid.shape
        soundings = []
        
        # Iterate over grid cells
        for row_start in range(0, rows, cell_pixels_y):
            for col_start in range(0, cols, cell_pixels_x):
                row_end = min(row_start + cell_pixels_y, rows)
                col_end = min(col_start + cell_pixels_x, cols)
                
                # Extract cell
                cell = depth_grid[row_start:row_end, col_start:col_end]
                
                # Mask nodata
                if nodata_value is not None:
                    valid_mask = cell != nodata_value
                else:
                    valid_mask = ~np.isnan(cell)
                
                valid_depths = cell[valid_mask]
                
                if len(valid_depths) == 0:
                    continue
                
                # Select depth based on mode
                if self.mode == "shoal":
                    # For bathymetry, shoal = minimum absolute depth
                    # If depths are negative (below water), shoal = max (closest to 0)
                    # If depths are positive, shoal = min
                    selected_depth = float(np.nanmin(np.abs(valid_depths)))
                    # Find actual value (preserving sign)
                    abs_depths = np.abs(valid_depths)
                    idx = np.nanargmin(abs_depths)
                    selected_depth = float(valid_depths.flat[idx])
                    
                elif self.mode == "deep":
                    selected_depth = float(np.nanmax(np.abs(valid_depths)))
                    abs_depths = np.abs(valid_depths)
                    idx = np.nanargmax(abs_depths)
                    selected_depth = float(valid_depths.flat[idx])
                    
                else:  # representative
                    selected_depth = float(np.nanmedian(valid_depths))
                
                # Find pixel location of selected depth
                flat_idx = np.nanargmin(np.abs(cell - selected_depth))
                local_row, local_col = np.unravel_index(flat_idx, cell.shape)
                
                pixel_row = row_start + local_row
                pixel_col = col_start + local_col
                
                # Convert to coordinates
                x, y = affine * (pixel_col + 0.5, pixel_row + 0.5)
                
                soundings.append(SoundingPoint(
                    x=x,
                    y=y,
                    depth=selected_depth,
                    selection_type=self.mode,
                    cell_id=(row_start // cell_pixels_y, col_start // cell_pixels_x),
                ))
        
        return soundings
    
    def to_geojson(self, soundings: list[SoundingPoint]) -> dict:
        """Convert soundings to GeoJSON FeatureCollection."""
        features = []
        for s in soundings:
            features.append({
                "type": "Feature",
                "geometry": mapping(Point(s.x, s.y)),
                "properties": {
                    "depth": round(s.depth, 2),
                    "selection_type": s.selection_type,
                    "cell_row": s.cell_id[0],
                    "cell_col": s.cell_id[1],
                },
            })
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "cell_size_meters": self.cell_size,
                "selection_mode": self.mode,
                "total_soundings": len(features),
            },
        }


def select_soundings_for_scale(
    depth_grid: np.ndarray,
    transform: tuple,
    target_scale: int = 50000,
    nodata_value: float = None,
) -> dict:
    """
    Convenience function to select soundings appropriate for a target chart scale.
    
    IHO guidelines suggest sounding density of approximately:
    - 1:10,000  -> 50m spacing
    - 1:25,000  -> 100m spacing
    - 1:50,000  -> 200m spacing
    - 1:100,000 -> 400m spacing
    
    Returns GeoJSON FeatureCollection.
    """
    # Scale to cell size mapping (approximate)
    scale_to_cell = {
        10000: 50,
        25000: 100,
        50000: 200,
        100000: 400,
        200000: 800,
    }
    
    # Find closest scale
    closest_scale = min(scale_to_cell.keys(), key=lambda k: abs(k - target_scale))
    cell_size = scale_to_cell[closest_scale]
    
    selector = SoundingSelector(cell_size_meters=cell_size, selection_mode="shoal")
    soundings = selector.select_from_grid(depth_grid, transform, nodata_value)
    
    result = selector.to_geojson(soundings)
    result["properties"]["target_scale"] = target_scale
    result["properties"]["applied_cell_size"] = cell_size
    
    return result
