"""
S-102 Export Module

Provides export functionality to IHO S-102 (Bathymetric Surface) format.
S-102 is part of the S-100 framework for marine data exchange.

Note: Full S-102 compliance requires HDF5 with specific schema.
This module provides foundation for S-102 export capability.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
import h5py
import rasterio

def create_s102_metadata(
    dataset_name: str,
    bounds: dict[str, float],
    resolution: tuple[float, float],
    crs: str = "EPSG:4326",
    producer: str = "HydroQ-QC-Assistant",
) -> dict[str, Any]:
    """
    Create S-102 compliant metadata structure.
    """
    return {
        "S102_ProductSpecification": "2.2.0",
        "metadata": {
            "dateTime": datetime.utcnow().isoformat() + "Z",
            "producer": {
                "organisationName": producer,
                "role": "processor",
            },
            "extent": {
                "geographicBoundingBox": {
                    "westBoundLongitude": bounds.get("minx", 0),
                    "eastBoundLongitude": bounds.get("maxx", 0),
                    "southBoundLatitude": bounds.get("miny", 0),
                    "northBoundLatitude": bounds.get("maxy", 0),
                },
            },
            "spatialRepresentation": {
                "gridSpacingLongitudinal": resolution[0] if resolution else 0,
                "gridSpacingLatitudinal": resolution[1] if resolution else 0,
            },
            "horizontalCRS": crs,
            "verticalCRS": "EPSG:5831",  # Mean Sea Level
            "dataType": "bathymetricSurface",
            "datasetTitle": dataset_name,
        },
    }

def export_s102_h5(
    dataset_path: str,
    dataset_name: str,
    bounds: dict[str, float],
    resolution: tuple[float, float] | None,
    depth_stats: dict[str, float],
    anomalies: list[dict[str, Any]],
    output_path: Path,
    producer: str = "HydroQ-QC-Assistant",
) -> Path:
    """
    Export dataset to S-102 compliant HDF5 format.
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Open source GeoTIFF to read grid data
    try:
        with rasterio.open(dataset_path) as src:
            depth_data = src.read(1)
            
            # Ensure floating point for S-102 and NaN handling
            if not np.issubdtype(depth_data.dtype, np.floating):
                depth_data = depth_data.astype(np.float32)

            # Replace nodata with NaN for processing
            if src.nodata is not None:
                depth_data[depth_data == src.nodata] = np.nan
                
            # S-102 uses positive depth (downwards), so if data is negative (z), flip it?
            # Standard bathymetry is usually positive depth.
            # Assuming input is already depth or elevation. If elevation (negative underwater), we might flip.
            # For this PoC we write as-is but handle nodata.
            
            # Write HDF5
            with h5py.File(output_path, "w") as f:
                # Root attributes
                f.attrs["productSpecification"] = "INT.IHO.S-102.2.2.0"
                f.attrs["issueDate"] = datetime.utcnow().strftime("%Y%m%d")
                f.attrs["issueTime"] = datetime.utcnow().strftime("%H%M%S")
                
                # 1. BathymetryCoverage Group (The Grid)
                cov_grp = f.create_group("BathymetryCoverage")
                cov_01 = cov_grp.create_group("BathymetryCoverage.01")
                
                # Instance attributes
                cov_01.attrs["eastBoundLongitude"] = bounds.get("maxx", 0)
                cov_01.attrs["westBoundLongitude"] = bounds.get("minx", 0)
                cov_01.attrs["southBoundLatitude"] = bounds.get("miny", 0)
                cov_01.attrs["northBoundLatitude"] = bounds.get("maxy", 0)
                cov_01.attrs["gridSpacingLongitudinal"] = resolution[0] if resolution else 0
                cov_01.attrs["gridSpacingLatitudinal"] = resolution[1] if resolution else 0
                
                # Group_001 (The actual data values)
                grp_001 = cov_01.create_group("Group_001")
                
                # Prepare data for S-102 (float32)
                # Handle NaN -> S-102 fill value usually 1000000.0 or similar.
                fill_value = 1000000.0
                out_data = np.nan_to_num(depth_data, nan=fill_value).astype(np.float32)
                
                # Create dataset
                dset = grp_001.create_dataset(
                    "values", 
                    data=out_data, 
                    compression="gzip",
                    fillvalue=fill_value
                )
                
                # QC Extension: Store anomalies as a Group
                qc_grp = f.create_group("QualityControl")
                qc_list = qc_grp.create_group("Anomalies")
                
                # Store metadata as JSON attribute or structure
                # HDF5 doesn't like complex JSON attributes nicely, so we serialize string
                safe_anomalies = []
                for a in anomalies:
                    safe_a = {k: str(v) if isinstance(v, (UUID, datetime)) else v for k, v in a.items()}
                    safe_anomalies.append(safe_a)
                    
                qc_list.attrs["anomaly_count"] = len(anomalies)
                qc_list.attrs["json_summary"] = json.dumps(safe_anomalies[:100]) # truncated for performance attribute
                
                # Also store general metadata
                f.attrs["producer"] = producer
                f.attrs["datasetName"] = dataset_name

    except Exception as e:
        # If rasterio fails or file missing, fallback or raise
        raise RuntimeError(f"Failed to generate S-102 HDF5: {str(e)}")
            
    return output_path

def export_s102_json(*args, **kwargs):
    """Legacy JSON preview export (kept for compatibility)"""
    raise NotImplementedError("Use export_s102_h5 for S-102 export")

