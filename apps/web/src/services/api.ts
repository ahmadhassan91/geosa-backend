/**
 * API Client for HydroQ-QC-Assistant
 */

import axios, { AxiosInstance } from 'axios';
import type {
    User,
    Dataset,
    Run,
    RunProgress,
    Anomaly,
    AnomalyListResponse,
    ReviewLog,
    TokenResponse,
    GeoJSONFeatureCollection,
} from '@/types/api';

// Use dynamic URL for cloud deployment, fallback to proxy for local dev
const API_BASE_URL = (import.meta.env.VITE_API_URL as string) || '/api/v1';

class ApiClient {
    private client: AxiosInstance;
    private token: string | null = null;

    constructor() {
        this.client = axios.create({
            baseURL: API_BASE_URL,
            headers: {
                'Content-Type': 'application/json',
            },
        });

        // Add auth interceptor
        this.client.interceptors.request.use((config) => {
            if (this.token) {
                config.headers.Authorization = `Bearer ${this.token}`;
            }
            return config;
        });

        // Load token from storage
        this.token = localStorage.getItem('hydroq_token');
    }

    setToken(token: string | null) {
        this.token = token;
        if (token) {
            localStorage.setItem('hydroq_token', token);
        } else {
            localStorage.removeItem('hydroq_token');
        }
    }

    // ========================================
    // Auth
    // ========================================

    async login(username: string, password: string): Promise<TokenResponse> {
        const response = await this.client.post<TokenResponse>('/auth/login', {
            username,
            password,
        });
        this.setToken(response.data.access_token);
        return response.data;
    }

    async register(username: string, email: string, password: string, role = 'viewer'): Promise<User> {
        const response = await this.client.post<User>('/auth/register', {
            username,
            email,
            password,
            role,
        });
        return response.data;
    }

    async getCurrentUser(): Promise<User> {
        const response = await this.client.get<User>('/auth/me');
        return response.data;
    }

    logout() {
        this.setToken(null);
    }

    // ========================================
    // Datasets
    // ========================================

    async listDatasets(page = 1, pageSize = 20): Promise<{ items: Dataset[]; total: number }> {
        const response = await this.client.get<{ items: Dataset[]; total: number }>('/datasets', {
            params: { page, page_size: pageSize },
        });
        return response.data;
    }

    async getDataset(id: string): Promise<Dataset> {
        const response = await this.client.get<Dataset>(`/datasets/${id}`);
        return response.data;
    }

    async uploadDataset(name: string, description: string, file: File): Promise<Dataset> {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('description', description);
        formData.append('file', file);

        const response = await this.client.post<Dataset>('/datasets', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    }

    async deleteDataset(id: string): Promise<void> {
        await this.client.delete(`/datasets/${id}`);
    }

    // ========================================
    // Runs
    // ========================================

    async listRuns(datasetId?: string, page = 1, pageSize = 20): Promise<{ items: Run[]; total: number }> {
        const response = await this.client.get<{ items: Run[]; total: number }>('/runs', {
            params: { dataset_id: datasetId, page, page_size: pageSize },
        });
        return response.data;
    }

    async getRun(id: string): Promise<Run> {
        const response = await this.client.get<Run>(`/runs/${id}`);
        return response.data;
    }

    async getRunStatus(id: string): Promise<RunProgress> {
        const response = await this.client.get<RunProgress>(`/runs/${id}/status`);
        return response.data;
    }

    async createRun(datasetId: string, configOverrides?: Record<string, unknown>): Promise<Run> {
        const response = await this.client.post<Run>('/runs', {
            dataset_id: datasetId,
            config_overrides: configOverrides,
        });
        return response.data;
    }

    // ========================================
    // Anomalies
    // ========================================

    async listAnomalies(
        runId: string,
        options: {
            page?: number;
            pageSize?: number;
            confidence?: string;
            decision?: string;
            sortBy?: string;
            sortDesc?: boolean;
        } = {}
    ): Promise<AnomalyListResponse> {
        const response = await this.client.get<AnomalyListResponse>(`/runs/${runId}/anomalies`, {
            params: {
                page: options.page ?? 1,
                page_size: options.pageSize ?? 20,
                confidence: options.confidence,
                decision: options.decision,
                sort_by: options.sortBy ?? 'qc_priority',
                sort_desc: options.sortDesc ?? true,
            },
        });
        return response.data;
    }

    async getAnomaly(runId: string, anomalyId: string): Promise<Anomaly> {
        const response = await this.client.get<Anomaly>(`/runs/${runId}/anomalies/${anomalyId}`);
        return response.data;
    }

    async submitReview(
        runId: string,
        anomalyId: string,
        decision: 'accepted' | 'rejected',
        comment?: string
    ): Promise<ReviewLog> {
        const response = await this.client.post<ReviewLog>(`/runs/${runId}/anomalies/${anomalyId}/review`, {
            decision,
            comment,
        });
        return response.data;
    }

    async bulkReview(
        runId: string,
        anomalyIds: string[],
        decision: 'accepted' | 'rejected',
        comment?: string
    ): Promise<ReviewLog[]> {
        const response = await this.client.post<ReviewLog[]>(`/runs/${runId}/anomalies/bulk-review`, {
            anomaly_ids: anomalyIds,
            decision,
            comment,
        });
        return response.data;
    }

    async getReviewHistory(runId: string, anomalyId: string): Promise<ReviewLog[]> {
        const response = await this.client.get<{ items: ReviewLog[] }>(
            `/runs/${runId}/anomalies/${anomalyId}/history`
        );
        return response.data.items;
    }

    // ========================================
    // Export
    // ========================================

    async exportJSON(runId: string, reviewedOnly = false): Promise<unknown> {
        const response = await this.client.get(`/runs/${runId}/export/json`, {
            params: { include_reviewed_only: reviewedOnly },
        });
        return response.data;
    }

    async exportGeoJSON(runId: string, reviewedOnly = false): Promise<GeoJSONFeatureCollection> {
        const response = await this.client.get<GeoJSONFeatureCollection>(`/runs/${runId}/export/geojson`, {
            params: { include_reviewed_only: reviewedOnly },
        });
        return response.data;
    }

    getHeatmapUrl(runId: string): string {
        return `${API_BASE_URL}/runs/${runId}/export/heatmap`;
    }

    // ========================================
    // Quality Metrics
    // ========================================

    async getQualityMetrics(runId: string): Promise<unknown> {
        const response = await this.client.get(`/quality/metrics/${runId}`);
        return response.data;
    }

    async getSoundingSelection(runId: string, scale = 50000): Promise<unknown> {
        const response = await this.client.get(`/quality/sounding-selection/${runId}`, {
            params: { scale },
        });
        return response.data;
    }

    async exportS102(runId: string): Promise<Blob> {
        const response = await this.client.get(`/runs/${runId}/export/s102`, {
            responseType: 'blob',
        });
        return response.data;
    }

    // ========================================
    // Production (Upstream Processing)
    // ========================================

    async generateSoundings(
        datasetId: string,
        targetScale = 50000,
        selectionMode: 'shoal' | 'deep' | 'representative' = 'shoal'
    ): Promise<GeoJSONFeatureCollection> {
        const response = await this.client.post<GeoJSONFeatureCollection>('/production/sounding-selection', {
            dataset_id: datasetId,
            target_scale: targetScale,
            selection_mode: selectionMode,
        });
        return response.data;
    }

    async generateContours(
        datasetId: string,
        contourInterval = 5.0,
        smoothingIterations = 3
    ): Promise<GeoJSONFeatureCollection> {
        const response = await this.client.post<GeoJSONFeatureCollection>('/production/contours', {
            dataset_id: datasetId,
            contour_interval: contourInterval,
            smoothing_iterations: smoothingIterations,
        });
        return response.data;
    }

    async applyNoiseCleaning(
        datasetId: string,
        method: 'median' | 'gaussian' | 'opening' = 'median',
        kernelSize = 3,
        threshold = 0.5
    ): Promise<GeoJSONFeatureCollection> {
        const response = await this.client.post<GeoJSONFeatureCollection>('/production/clean', {
            dataset_id: datasetId,
            method,
            kernel_size: kernelSize,
            threshold,
        });
        return response.data;
    }

    async getProductionCapabilities(): Promise<unknown> {
        const response = await this.client.get('/production/capabilities');
        return response.data;
    }
}

export const api = new ApiClient();
export default api;
