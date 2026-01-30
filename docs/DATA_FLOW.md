# Data Flow Documentation

## Overview

This document describes how data flows through the HydroQ-QC-Assistant system from initial upload to final review decision.

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                       │
│                                                                              │
│  ┌─────────┐    ┌─────────┐    ┌─────────────┐    ┌─────────────────────┐   │
│  │ Upload  │───▶│ Ingest  │───▶│   Extract   │───▶│      Detect         │   │
│  │         │    │         │    │  Features   │    │    Anomalies        │   │
│  └─────────┘    └─────────┘    └─────────────┘    └─────────────────────┘   │
│                                                              │               │
│                                                              ▼               │
│  ┌─────────┐    ┌─────────┐    ┌─────────────┐    ┌─────────────────────┐   │
│  │ Export  │◀───│ Review  │◀───│   Display   │◀───│       Score         │   │
│  │         │    │         │    │             │    │      & Rank         │   │
│  └─────────┘    └─────────┘    └─────────────┘    └─────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Stage 1: Data Upload

**Input**: GeoTIFF raster or CSV/Parquet point cloud

**Process**:
1. User uploads file via web UI
2. API validates file type and size
3. File saved to `data/uploads/` with unique naming
4. Metadata extracted:
   - CRS (coordinate reference system)
   - Bounds (geographic extent)
   - Dimensions (width x height for rasters)
   - Basic statistics (min, max, mean, std of depth values)
5. Dataset record created in PostgreSQL

**Output**: Dataset entity with file reference

```python
Dataset(
    id=uuid4(),
    name="Survey Block A",
    file_path="/data/uploads/survey_block_a.tif",
    file_type="geotiff",
    crs="EPSG:32754",
    bounds={"minx": 138.4, "miny": -35.0, ...},
    z_min=-65.5,
    z_max=-42.3,
    ...
)
```

## Stage 2: Feature Extraction

**Input**: Raster depth data array

**Process**:
1. Load raster into numpy array
2. Handle NoData values (replace with NaN)
3. Compute derived features for each cell:

| Feature | Description | Method |
|---------|-------------|--------|
| `z_score` | Local deviation from neighbors | (z - local_mean) / local_std |
| `slope` | Gradient magnitude | Sobel operators |
| `curvature` | Second derivative | Laplacian of Sobel |
| `roughness` | Local standard deviation | Moving window std |
| `laplacian` | Edge detection | 3x3 Laplacian kernel |
| `neighbor_mean` | Average of surrounding cells | 5x5 window mean |
| `neighbor_std` | Variability of surrounding cells | 5x5 window std |

**Output**: Dictionary of feature arrays, same shape as input

```python
features = {
    "z_score": np.array(...),      # shape: (H, W)
    "slope": np.array(...),
    "curvature": np.array(...),
    "roughness": np.array(...),
    "laplacian": np.array(...),
    "neighbor_mean": np.array(...),
    "neighbor_std": np.array(...),
}
```

## Stage 3: Anomaly Detection

**Input**: Feature arrays

**Process**:

### 3.1 Isolation Forest Detection
```python
# Flatten valid pixels into feature vectors
X = np.column_stack([features[name][valid_mask] for name in feature_names])

# Train Isolation Forest
model = IsolationForest(
    n_estimators=100,
    contamination=0.1,  # Expected 10% anomalies
    random_state=42
)

# Get anomaly scores
scores = -model.fit(X).decision_function(X)
scores = normalize_0_1(scores)  # Map to [0, 1]
```

### 3.2 Z-Score / MAD Detection
```python
# Using Median Absolute Deviation (robust to outliers)
median = np.median(z_values)
mad = median_abs_deviation(z_values)
modified_zscore = abs(z - median) / mad

# Normalize to [0, 1] based on threshold
scores = min(modified_zscore / threshold, 1.0)
```

### 3.3 Score Combination
```python
# Weighted combination
final_score = (
    0.5 * isolation_forest_score +
    0.3 * zscore_score +
    0.2 * spatial_consistency_score
)
```

**Output**: Score grid with values 0.0-1.0

## Stage 4: Scoring & Ranking

**Input**: Score grid, original data

**Process**:

### 4.1 Confidence Level Assignment
```python
if score >= 0.8:
    confidence = ConfidenceLevel.HIGH
elif score >= 0.5:
    confidence = ConfidenceLevel.MEDIUM
else:
    confidence = ConfidenceLevel.LOW
```

### 4.2 Priority Calculation
```python
qc_priority = (
    0.5 * anomaly_score +
    0.3 * depth_variance_factor +
    0.2 * area_factor
)
```

### 4.3 Polygonization
```python
# Threshold score grid
binary_mask = score_grid > 0.6

# Find connected components
labeled, num_features = ndimage.label(binary_mask)

# Convert each component to polygon
for component_id in range(1, num_features + 1):
    component_mask = labeled == component_id
    if pixel_count(component_mask) >= 9:  # Minimum size
        geometry = rasterio.features.shapes(component_mask)
        polygon = simplify(geometry)
        
        # Create anomaly entity with explanation
        anomaly = Anomaly(
            geometry=polygon,
            anomaly_probability=mean_score(component_mask),
            confidence_level=...,
            qc_priority=...,
            explanation={
                "primary_reason": "High local z-score",
                "features": {...},
                "thresholds": {...},
                "detector_flags": ["isolation_forest", "zscore"]
            }
        )
```

**Output**: List of Anomaly entities with geometries, scores, and explanations

## Stage 5: Display

**Input**: Anomaly list, source GeoTIFF

**Process**:
1. Frontend fetches anomaly list via API
2. Anomalies converted to GeoJSON for map display
3. MapLibre GL renders:
   - **Anomaly polygons** colored by confidence (High=Red, Medium=Orange, Low=Yellow)
   - **Density heatmap layer** showing anomaly concentration
   - Selected anomaly highlight
   - Popups with basic info
4. **Sidebar controls**:
   - Toggle: Anomaly Polygons (on/off)
   - Toggle: Density Heatmap (on/off)
   - Confidence filter chips
5. Side panel shows:
   - Ranked list (highest priority first)
   - Filter controls
   - Explanation accordion
6. **Quality Dashboard**:
   - Data quality grade (A-F)
   - Time savings estimate
   - Anomaly type breakdown (Spikes, Holes, Noise, etc.)

**Output**: Interactive map and review interface

## Stage 6: Review

**Input**: User decision (accept/reject) with optional comment

**Process**:
1. User clicks Accept or Reject
2. API endpoint called: `POST /anomalies/{id}/review`
3. Anomaly record updated with decision
4. Immutable review log created:
   ```python
   ReviewLog(
       anomaly_id=anomaly.id,
       decision=ReviewDecision.ACCEPTED,
       comment="Confirmed spike in survey line 42",
       reviewer_id=user.id,
       reviewer_username="john_hydrographer",
       model_version="0.1.0",
       anomaly_score_at_review=0.85,
       created_at=datetime.utcnow()
   )
   ```
5. UI advances to next pending anomaly

**Output**: Updated anomaly status, audit log entry

## Stage 7: Export

**Input**: Run ID, export format, filter options

**Process**:
1. User clicks Export button
2. API generates report based on format:
   - **JSON**: Full report with all metadata
   - **GeoJSON**: Anomaly geometries for GIS import
   - **S-102 HDF5**: IHO S-102 v2.2 binary bathymetric surface with:
     - Full depth grid from source GeoTIFF
     - Geographic bounds and resolution metadata
     - QC results embedded as HDF5 attributes
     - Anomaly summary in JSON attribute
   - **PDF**: Formatted review report (planned)
3. File served for download

**S-102 HDF5 Structure**:
```
root/
├── @productSpecification = "INT.IHO.S-102.2.2.0"
├── @issueDate, @issueTime
├── BathymetryCoverage/
│   └── BathymetryCoverage.01/
│       ├── @bounds (east, west, south, north)
│       ├── @gridSpacing
│       └── Group_001/
│           └── values (float32 depth grid, gzip compressed)
└── QualityControl/
    └── Anomalies/
        ├── @anomaly_count
        └── @json_summary
```

**Output**: Downloadable report file

## Data Storage Summary

| Data Type | Storage Location | Format |
|-----------|------------------|--------|
| Uploaded files | `data/uploads/` | Original format (GeoTIFF, CSV) |
| Heatmaps | `data/outputs/{run_id}/` | GeoTIFF |
| Anomaly polygons | `data/outputs/{run_id}/` | GeoJSON |
| S-102 exports | `data/exports/{run_id}/` | HDF5 (.h5) |
| Metadata | PostgreSQL | Relational tables |
| Review history | PostgreSQL | Append-only table |
| Audit logs | PostgreSQL | Append-only table |
