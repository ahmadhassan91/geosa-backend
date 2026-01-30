/**
 * TypeScript types for the HydroQ-QC-Assistant API
 */

export interface User {
    id: string;
    username: string;
    email: string;
    role: 'admin' | 'hydrographer' | 'viewer';
    is_active: boolean;
    created_at: string;
}

export interface Dataset {
    id: string;
    name: string;
    description: string;
    file_path: string;
    file_type: 'geotiff' | 'csv' | 'parquet';
    file_size_bytes: number;
    crs: string | null;
    bounds: {
        minx: number;
        miny: number;
        maxx: number;
        maxy: number;
    } | null;
    width: number | null;
    height: number | null;
    resolution: [number, number] | null;
    point_count: number | null;
    z_min: number | null;
    z_max: number | null;
    z_mean: number | null;
    z_std: number | null;
    nodata_percentage: number | null;
    created_by: string | null;
    created_at: string;
}

export type RunStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Run {
    id: string;
    dataset_id: string;
    status: RunStatus;
    config_hash: string;
    model_version: string;
    started_at: string | null;
    completed_at: string | null;
    duration_seconds: number | null;
    total_anomalies: number;
    high_confidence_count: number;
    medium_confidence_count: number;
    low_confidence_count: number;
    heatmap_path: string | null;
    geojson_path: string | null;
    report_path: string | null;
    error_message: string | null;
    created_by: string | null;
    created_at: string;
}

export interface RunStatus {
    id: string;
    status: string;
    progress_percent: number;
    current_step: string | null;
    error_message: string | null;
}

export type ConfidenceLevel = 'low' | 'medium' | 'high';
export type ReviewDecision = 'pending' | 'accepted' | 'rejected';
export type AnomalyType = 'spike' | 'hole' | 'seam' | 'noise_band' | 'discontinuity' | 'density_gap' | 'unknown';

export interface AnomalyExplanation {
    primary_reason: string;
    features: Record<string, number>;
    thresholds: Record<string, number>;
    detector_flags: string[];
    pixel_count?: number;
}

export interface Anomaly {
    id: string;
    run_id: string;
    centroid_x: number;
    centroid_y: number;
    geometry: GeoJSON.Geometry;
    area_sq_meters: number | null;
    anomaly_type: AnomalyType;
    anomaly_probability: number;
    confidence_level: ConfidenceLevel;
    qc_priority: number;
    explanation: AnomalyExplanation;
    local_depth_mean: number | null;
    local_depth_std: number | null;
    neighbor_count: number | null;
    review_decision: ReviewDecision;
    created_at: string;
}

export interface AnomalyListResponse {
    items: Anomaly[];
    total: number;
    page: number;
    page_size: number;
    by_confidence: Record<string, number>;
    by_type: Record<string, number>;
    by_decision: Record<string, number>;
}

export interface ReviewLog {
    id: string;
    anomaly_id: string;
    run_id: string;
    decision: ReviewDecision;
    comment: string | null;
    reviewer_id: string | null;
    reviewer_username: string | null;
    model_version: string | null;
    created_at: string;
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
    expires_in: number;
}

// GeoJSON types
export interface GeoJSONFeature {
    type: 'Feature';
    id: string;
    geometry: GeoJSON.Geometry;
    properties: {
        anomaly_id: string;
        run_id: string;
        anomaly_type: AnomalyType;
        anomaly_probability: number;
        confidence_level: ConfidenceLevel;
        qc_priority: number;
        review_decision: ReviewDecision;
        explanation: AnomalyExplanation;
    };
}

export interface GeoJSONFeatureCollection {
    type: 'FeatureCollection';
    features: GeoJSONFeature[];
    properties?: {
        run_id: string;
        model_version: string;
        generated_at: string;
    };
}
