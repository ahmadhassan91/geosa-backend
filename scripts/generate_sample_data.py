#!/usr/bin/env python3
"""
Sample Bathymetry Data Generator

Generates synthetic multibeam bathymetry data for testing the HydroQ-QC-Assistant.
Creates realistic-looking data with intentional anomalies for testing the detection pipeline.
"""

import argparse
import os
from pathlib import Path
import numpy as np

# Delay imports for faster --help
def generate_sample_dataset(
    output_path: Path,
    width: int = 500,
    height: int = 500,
    resolution: float = 1.0,  # meters per pixel
    base_depth: float = -50.0,  # meters
    num_spikes: int = 5,
    num_holes: int = 5,
    num_seams: int = 2,
    noise_level: float = 0.5,
    seed: int = 42,
):
    """
    Generate a synthetic bathymetry GeoTIFF with embedded anomalies.
    
    Args:
        output_path: Path to save the GeoTIFF
        width: Raster width in pixels
        height: Raster height in pixels
        resolution: Pixel resolution in meters
        base_depth: Base depth in meters (negative = below sea level)
        num_spikes: Number of spike anomalies to embed
        num_holes: Number of hole anomalies to embed
        num_seams: Number of seam lines to embed
        noise_level: Standard deviation of random noise
        seed: Random seed for reproducibility
    """
    import rasterio
    from rasterio.transform import from_bounds
    
    np.random.seed(seed)
    
    print(f"Generating synthetic bathymetry: {width}x{height} @ {resolution}m resolution")
    
    # Create base bathymetry surface with gentle topography
    x = np.linspace(0, 4 * np.pi, width)
    y = np.linspace(0, 4 * np.pi, height)
    X, Y = np.meshgrid(x, y)
    
    # Combine multiple frequencies for realistic terrain
    surface = (
        np.sin(X / 2) * np.cos(Y / 2) * 5 +  # Large-scale features
        np.sin(X) * np.sin(Y) * 2 +          # Medium-scale features
        np.sin(X * 2) * np.cos(Y * 2) * 0.5  # Small-scale features
    )
    
    # Scale to depth range
    data = base_depth + surface
    
    # Add random noise
    data += np.random.normal(0, noise_level, (height, width))
    
    print(f"  Base surface: depth range {data.min():.1f} to {data.max():.1f}m")
    
    # =========================================================================
    # Embed Anomalies
    # =========================================================================
    
    anomaly_locations = []
    
    # 1. Spike Anomalies (depth significantly shallower)
    print(f"  Embedding {num_spikes} spike anomalies...")
    for i in range(num_spikes):
        cx = np.random.randint(50, width - 50)
        cy = np.random.randint(50, height - 50)
        radius = np.random.randint(5, 15)
        magnitude = np.random.uniform(5, 15)  # meters shallower
        
        yy, xx = np.ogrid[:height, :width]
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius ** 2
        data[mask] += magnitude  # Make shallower (less negative)
        
        anomaly_locations.append({
            "type": "spike",
            "center": (cx, cy),
            "radius": radius,
            "magnitude": magnitude,
        })
    
    # 2. Hole Anomalies (depth significantly deeper)
    print(f"  Embedding {num_holes} hole anomalies...")
    for i in range(num_holes):
        cx = np.random.randint(50, width - 50)
        cy = np.random.randint(50, height - 50)
        radius = np.random.randint(5, 15)
        magnitude = np.random.uniform(5, 15)  # meters deeper
        
        yy, xx = np.ogrid[:height, :width]
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius ** 2
        data[mask] -= magnitude  # Make deeper (more negative)
        
        anomaly_locations.append({
            "type": "hole",
            "center": (cx, cy),
            "radius": radius,
            "magnitude": magnitude,
        })
    
    # 3. Seam Anomalies (sharp discontinuities)
    print(f"  Embedding {num_seams} seam anomalies...")
    for i in range(num_seams):
        if np.random.random() > 0.5:
            # Horizontal seam
            row = np.random.randint(100, height - 100)
            offset = np.random.uniform(1, 3)
            data[row:, :] += offset
            anomaly_locations.append({
                "type": "seam_horizontal",
                "row": row,
                "offset": offset,
            })
        else:
            # Vertical seam
            col = np.random.randint(100, width - 100)
            offset = np.random.uniform(1, 3)
            data[:, col:] += offset
            anomaly_locations.append({
                "type": "seam_vertical",
                "col": col,
                "offset": offset,
            })
    
    # 4. Noise band (high-frequency noise in a region)
    if np.random.random() > 0.5:
        print("  Embedding noise band...")
        band_start = np.random.randint(0, height - 50)
        band_end = band_start + np.random.randint(20, 50)
        band_noise = np.random.normal(0, 3, (band_end - band_start, width))
        data[band_start:band_end, :] += band_noise
        anomaly_locations.append({
            "type": "noise_band",
            "row_start": band_start,
            "row_end": band_end,
        })
    
    # =========================================================================
    # Create GeoTIFF
    # =========================================================================
    
    # Define geographic bounds (sample location: offshore Adelaide, SA)
    # Using approximate coordinates
    min_lon = 138.4
    max_lon = min_lon + (width * resolution) / 111000  # Approx degrees from meters
    min_lat = -35.0
    max_lat = min_lat + (height * resolution) / 111000
    
    transform = from_bounds(min_lon, min_lat, max_lon, max_lat, width, height)
    
    # Write GeoTIFF
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": width,
        "height": height,
        "count": 1,
        "crs": "EPSG:4326",
        "transform": transform,
        "nodata": -9999,
        "compress": "lzw",
    }
    
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(data.astype(np.float32), 1)
        dst.update_tags(
            GENERATOR="HydroQ-QC-Assistant Sample Generator",
            ANOMALY_COUNT=str(len(anomaly_locations)),
        )
    
    print(f"\n✓ Generated: {output_path}")
    print(f"  Size: {width}x{height} pixels ({width * height:,} cells)")
    print(f"  Resolution: {resolution}m")
    print(f"  Depth range: {data.min():.1f}m to {data.max():.1f}m")
    print(f"  Embedded anomalies: {len(anomaly_locations)}")
    
    # Save anomaly locations as JSON for verification
    import json
    meta_path = output_path.with_suffix(".anomalies.json")
    with open(meta_path, "w") as f:
        json.dump({
            "embedded_anomalies": anomaly_locations,
            "dataset_info": {
                "width": width,
                "height": height,
                "resolution": resolution,
                "base_depth": base_depth,
                "seed": seed,
            }
        }, f, indent=2)
    print(f"  Anomaly metadata: {meta_path}")
    
    return output_path, anomaly_locations


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic bathymetry data for HydroQ-QC-Assistant testing"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="data/samples/sample_bathymetry.tif",
        help="Output GeoTIFF path",
    )
    parser.add_argument(
        "-w", "--width",
        type=int,
        default=500,
        help="Raster width in pixels (default: 500)",
    )
    parser.add_argument(
        "-H", "--height",
        type=int,
        default=500,
        help="Raster height in pixels (default: 500)",
    )
    parser.add_argument(
        "-r", "--resolution",
        type=float,
        default=1.0,
        help="Pixel resolution in meters (default: 1.0)",
    )
    parser.add_argument(
        "-d", "--base-depth",
        type=float,
        default=-50.0,
        help="Base depth in meters (default: -50.0)",
    )
    parser.add_argument(
        "-s", "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--spikes",
        type=int,
        default=5,
        help="Number of spike anomalies (default: 5)",
    )
    parser.add_argument(
        "--holes",
        type=int,
        default=5,
        help="Number of hole anomalies (default: 5)",
    )
    parser.add_argument(
        "--seams",
        type=int,
        default=2,
        help="Number of seam lines (default: 2)",
    )
    
    args = parser.parse_args()
    
    generate_sample_dataset(
        output_path=Path(args.output),
        width=args.width,
        height=args.height,
        resolution=args.resolution,
        base_depth=args.base_depth,
        num_spikes=args.spikes,
        num_holes=args.holes,
        num_seams=args.seams,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
