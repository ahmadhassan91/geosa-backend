/**
 * Analysis Page - Map View with Anomaly Review Panel
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Map, { Source, Layer, NavigationControl, ScaleControl, Popup } from 'react-map-gl/maplibre';
import {
    Box,
    Paper,
    Typography,
    Chip,
    Button,
    IconButton,
    List,
    ListItemButton,
    ListItemText,
    TextField,
    CircularProgress,
    Alert,
    Divider,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    Tooltip,
} from '@mui/material';
import {
    ArrowBack as BackIcon,
    CheckCircle as AcceptIcon,
    Cancel as RejectIcon,
    ExpandMore as ExpandIcon,
    Download as ExportIcon,
    FilterList as FilterIcon,
    Refresh as RefreshIcon,
} from '@mui/icons-material';
import api from '@/services/api';
import { useAppStore } from '@/stores';
import QualityMetrics from '@/components/QualityMetrics';
import ProductionTools from '@/components/ProductionTools';
import type { Run, Anomaly, GeoJSONFeatureCollection } from '@/types/api';

const MAPLIBRE_STYLE = 'https://demotiles.maplibre.org/style.json';

export default function AnalysisPage() {
    const { showAnomalyPolygons, showHeatmap } = useAppStore((state) => ({
        showAnomalyPolygons: state.showAnomalyPolygons,
        showHeatmap: state.showHeatmap
    }));
    const navigate = useNavigate();
    const { runId } = useParams<{ runId: string }>();
    const mapRef = useRef<any>(null);

    // State
    const [run, setRun] = useState<Run | null>(null);
    const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
    const [geojson, setGeojson] = useState<GeoJSONFeatureCollection | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    // Selection & Review
    const [selectedAnomaly, setSelectedAnomaly] = useState<Anomaly | null>(null);
    const [reviewComment, setReviewComment] = useState('');
    const [submitting, setSubmitting] = useState(false);

    // Filters
    const [showHigh, setShowHigh] = useState(true);
    const [showMedium, setShowMedium] = useState(true);
    const [showLow, setShowLow] = useState(true);
    const [showPending, setShowPending] = useState(true);
    const [showAccepted, setShowAccepted] = useState(false);
    const [showRejected, setShowRejected] = useState(false);

    // Map state
    const [viewState, setViewState] = useState({
        longitude: 138.6,
        latitude: -34.9,
        zoom: 10,
    });
    const [popupInfo, setPopupInfo] = useState<Anomaly | null>(null);

    // Production layer state
    const [soundingsGeojson, setSoundingsGeojson] = useState<GeoJSONFeatureCollection | null>(null);
    const [contoursGeojson, setContoursGeojson] = useState<GeoJSONFeatureCollection | null>(null);

    // Cleaning state
    const [cleaningMethod, setCleaningMethod] = useState<'median' | 'gaussian' | 'opening'>('median');
    const [cleaningKernel, setCleaningKernel] = useState(3);
    const [cleaningLoading, setCleaningLoading] = useState(false);
    const [cleaningGeojson, setCleaningGeojson] = useState<GeoJSONFeatureCollection | null>(null);

    const loadData = useCallback(async () => {
        if (!runId) return;

        try {
            setLoading(true);
            const [runData, anomalyData, geojsonData] = await Promise.all([
                api.getRun(runId),
                api.listAnomalies(runId, { pageSize: 1000 }),
                api.exportGeoJSON(runId),
            ]);

            setRun(runData);
            setAnomalies(anomalyData.items);
            setGeojson(geojsonData);

            // Center map on anomalies if available
            if (anomalyData.items.length > 0) {
                const firstAnomaly = anomalyData.items[0];
                setViewState({
                    longitude: firstAnomaly.centroid_x,
                    latitude: firstAnomaly.centroid_y,
                    zoom: 14,
                });
            }
        } catch (err) {
            setError('Failed to load analysis data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [runId]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleSelectAnomaly = (anomaly: Anomaly) => {
        setSelectedAnomaly(anomaly);
        setReviewComment('');
        setPopupInfo(anomaly);

        // Fly to anomaly
        if (mapRef.current) {
            mapRef.current.flyTo({
                center: [anomaly.centroid_x, anomaly.centroid_y],
                zoom: 16,
                duration: 1000,
            });
        }
    };

    const handleReview = async (decision: 'accepted' | 'rejected') => {
        if (!selectedAnomaly || !runId) return;

        setSubmitting(true);
        try {
            await api.submitReview(runId, selectedAnomaly.id, decision, reviewComment || undefined);

            // Update local state
            setAnomalies((prev) =>
                prev.map((a) =>
                    a.id === selectedAnomaly.id ? { ...a, review_decision: decision } : a
                )
            );

            // Move to next pending anomaly
            const pendingAnomalies = anomalies.filter(
                (a) => a.review_decision === 'pending' && a.id !== selectedAnomaly.id
            );
            if (pendingAnomalies.length > 0) {
                handleSelectAnomaly(pendingAnomalies[0]);
            } else {
                setSelectedAnomaly(null);
                setPopupInfo(null);
            }
        } catch (err) {
            setError('Failed to submit review');
            console.error(err);
        } finally {
            setSubmitting(false);
        }
    };

    const handleExportGeoJSON = async () => {
        if (!runId) return;
        try {
            const data = await api.exportGeoJSON(runId);
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/geo+json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `run_${runId}_anomalies.geojson`;
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            setError('Failed to export GeoJSON');
        }
    };

    const handleExport = async () => {
        if (!runId) return;
        try {
            const data = await api.exportJSON(runId);
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `run_${runId}_report.json`;
            a.click();
        } catch (err) {
            setError('Failed to export report');
        }
    };

    const handleExportS102 = async () => {
        if (!runId) return;
        try {
            const blob = await api.exportS102(runId);
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `run_${runId}_S102_export.h5`;
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            setError('Failed to export S-102 format');
        }
    };

    const handleClean = async () => {
        if (!run?.dataset_id) return;
        setCleaningLoading(true);
        try {
            const result = await api.applyNoiseCleaning(
                run.dataset_id,
                cleaningMethod,
                cleaningKernel
            );
            setCleaningGeojson(result);

            // Auto fly to first diff if exists
            if (result.features && result.features.length > 0) {
                // @ts-ignore - simple centroid calculation or use turf
                const coords = result.features[0].geometry.coordinates[0][0];
                if (coords) {
                    mapRef.current?.flyTo({ center: coords, zoom: 14 });
                }
            }
        } catch (err) {
            const error = err as { message?: string };
            setError('Cleaning failed: ' + (error.message || 'Unknown error'));
        } finally {
            setCleaningLoading(false);
        }
    };

    // Filter anomalies
    const filteredAnomalies = anomalies.filter((a) => {
        const confMatch =
            (showHigh && a.confidence_level === 'high') ||
            (showMedium && a.confidence_level === 'medium') ||
            (showLow && a.confidence_level === 'low');

        const decMatch =
            (showPending && a.review_decision === 'pending') ||
            (showAccepted && a.review_decision === 'accepted') ||
            (showRejected && a.review_decision === 'rejected');

        return confMatch && decMatch;
    });

    // Create filtered GeoJSON
    const filteredGeojson = geojson
        ? {
            ...geojson,
            features: geojson.features.filter((f) =>
                filteredAnomalies.some((a) => a.id === f.id)
            ),
        }
        : null;

    // Create Heatmap GeoJSON (Points from Centroids)
    const heatmapGeojson = useMemo(() => {
        if (filteredAnomalies.length === 0) return null;
        return {
            type: 'FeatureCollection',
            features: filteredAnomalies.map((a) => ({
                type: 'Feature',
                geometry: { type: 'Point', coordinates: [a.centroid_x, a.centroid_y] },
                properties: {
                    id: a.id,
                    mag: a.anomaly_probability,
                }
            }))
        };
    }, [filteredAnomalies]);

    const getConfidenceColor = (level: string) => {
        switch (level) {
            case 'high': return '#ef4444';
            case 'medium': return '#f59e0b';
            case 'low': return '#10b981';
            default: return '#6b7280';
        }
    };

    const getDecisionBadge = (decision: string) => {
        switch (decision) {
            case 'accepted':
                return <Chip label="Accepted" size="small" color="success" sx={{ fontSize: '0.65rem' }} />;
            case 'rejected':
                return <Chip label="Rejected" size="small" color="error" sx={{ fontSize: '0.65rem' }} />;
            default:
                return <Chip label="Pending" size="small" sx={{ fontSize: '0.65rem' }} />;
        }
    };

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Box sx={{ display: 'flex', height: 'calc(100vh - 64px)' }}>
            {/* Map Container */}
            <Box sx={{ flexGrow: 1, position: 'relative' }}>
                <Map
                    ref={mapRef}
                    {...viewState}
                    onMove={(evt) => setViewState(evt.viewState)}
                    mapStyle={MAPLIBRE_STYLE}
                    style={{ width: '100%', height: '100%' }}
                    onClick={(e) => {
                        // Check if clicked on an anomaly feature
                        const features = e.features;
                        if (features && features.length > 0) {
                            const anomalyId = features[0].properties?.anomaly_id;
                            const anomaly = anomalies.find((a) => a.id === anomalyId);
                            if (anomaly) {
                                handleSelectAnomaly(anomaly);
                            }
                        }
                    }}
                    interactiveLayerIds={['anomaly-polygons']}
                >
                    <NavigationControl position="top-right" />
                    <ScaleControl position="bottom-right" />

                    {/* Density Heatmap */}
                    {heatmapGeojson && showHeatmap && (
                        <Source id="heatmap" type="geojson" data={heatmapGeojson}>
                            <Layer
                                id="heatmap-layer"
                                type="heatmap"
                                paint={{
                                    'heatmap-weight': ['interpolate', ['linear'], ['get', 'mag'], 0, 0, 1, 1],
                                    'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 0, 1, 15, 3],
                                    'heatmap-color': [
                                        'interpolate',
                                        ['linear'],
                                        ['heatmap-density'],
                                        0, 'rgba(33,102,172,0)',
                                        0.2, 'rgb(103,169,207)',
                                        0.4, 'rgb(209,229,240)',
                                        0.6, 'rgb(253,219,199)',
                                        0.8, 'rgb(239,138,98)',
                                        1, 'rgb(178,24,43)'
                                    ],
                                    'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 2, 15, 20],
                                    'heatmap-opacity': 0.6
                                }}
                            />
                        </Source>
                    )}

                    {/* Anomaly Polygons */}
                    {filteredGeojson && showAnomalyPolygons && (
                        <Source id="anomalies" type="geojson" data={filteredGeojson}>
                            <Layer
                                id="anomaly-polygons"
                                type="fill"
                                paint={{
                                    'fill-color': [
                                        'match',
                                        ['get', 'confidence_level'],
                                        'high', '#ef4444',
                                        'medium', '#f59e0b',
                                        'low', '#10b981',
                                        '#6b7280',
                                    ],
                                    'fill-opacity': 0.5,
                                }}
                            />
                            <Layer
                                id="anomaly-outlines"
                                type="line"
                                paint={{
                                    'line-color': [
                                        'match',
                                        ['get', 'confidence_level'],
                                        'high', '#dc2626',
                                        'medium', '#d97706',
                                        'low', '#059669',
                                        '#4b5563',
                                    ],
                                    'line-width': 2,
                                }}
                            />
                        </Source>
                    )}

                    {/* Selected Anomaly Highlight */}
                    {selectedAnomaly && (
                        <Source
                            id="selected-anomaly"
                            type="geojson"
                            data={{
                                type: 'Feature',
                                geometry: selectedAnomaly.geometry,
                                properties: {},
                            }}
                        >
                            <Layer
                                id="selected-outline"
                                type="line"
                                paint={{
                                    'line-color': '#fff',
                                    'line-width': 4,
                                }}
                            />
                        </Source>
                    )}

                    {/* Generated Contours */}
                    {contoursGeojson && (
                        <Source id="production-contours" type="geojson" data={contoursGeojson}>
                            <Layer
                                id="contours-layer"
                                type="line"
                                paint={{
                                    'line-color': '#3b82f6',
                                    'line-width': 2,
                                    'line-dasharray': [2, 1],
                                }}
                            />
                        </Source>
                    )}

                    {/* Generated Soundings */}
                    {soundingsGeojson && (
                        <Source id="production-soundings" type="geojson" data={soundingsGeojson}>
                            <Layer
                                id="soundings-layer"
                                type="circle"
                                paint={{
                                    'circle-radius': 5,
                                    'circle-color': '#22c55e',
                                    'circle-stroke-color': '#fff',
                                    'circle-stroke-width': 1,
                                }}
                            />
                        </Source>
                    )}

                    {/* Popup */}
                    {popupInfo && (
                        <Popup
                            longitude={popupInfo.centroid_x}
                            latitude={popupInfo.centroid_y}
                            anchor="bottom"
                            onClose={() => setPopupInfo(null)}
                            closeOnClick={false}
                        >
                            <Box sx={{ p: 1 }}>
                                <Typography variant="subtitle2" fontWeight={600}>
                                    {popupInfo.anomaly_type.replace('_', ' ').toUpperCase()}
                                </Typography>
                                <Typography variant="body2">
                                    Priority: {(popupInfo.qc_priority * 100).toFixed(0)}%
                                </Typography>
                                <Typography variant="body2">
                                    Probability: {(popupInfo.anomaly_probability * 100).toFixed(0)}%
                                </Typography>
                            </Box>
                        </Popup>
                    )}
                </Map>

                {/* Back Button */}
                <Box sx={{ position: 'absolute', top: 16, left: 16, zIndex: 10 }}>
                    <Button
                        startIcon={<BackIcon />}
                        onClick={() => navigate('/')}
                        variant="contained"
                        sx={{ bgcolor: 'background.paper', color: 'text.primary' }}
                    >
                        Back
                    </Button>
                </Box>
            </Box>

            {/* Review Panel */}
            <Paper
                sx={{
                    width: 400,
                    flexShrink: 0,
                    overflow: 'auto',
                    borderLeft: '1px solid',
                    borderColor: 'divider',
                    display: 'flex',
                    flexDirection: 'column',
                }}
            >
                {/* Header */}
                <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="h6" fontWeight={600}>
                            Anomaly Review
                        </Typography>
                        <Box>
                            <Tooltip title="Refresh">
                                <IconButton size="small" onClick={loadData}>
                                    <RefreshIcon />
                                </IconButton>
                            </Tooltip>
                            <Tooltip title="Export Report">
                                <IconButton size="small" onClick={handleExport}>
                                    <ExportIcon />
                                </IconButton>
                            </Tooltip>
                        </Box>
                    </Box>

                    {run && (
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                            <Chip
                                label={`${run.total_anomalies} total`}
                                size="small"
                                sx={{ fontSize: '0.7rem' }}
                            />
                            <Chip
                                label={`${run.high_confidence_count} high`}
                                size="small"
                                sx={{ bgcolor: 'error.main', color: 'white', fontSize: '0.7rem' }}
                            />
                            <Chip
                                label={`${run.medium_confidence_count} medium`}
                                size="small"
                                sx={{ bgcolor: 'warning.main', color: 'white', fontSize: '0.7rem' }}
                            />
                            <Chip
                                label={`${run.low_confidence_count} low`}
                                size="small"
                                sx={{ bgcolor: 'success.main', color: 'white', fontSize: '0.7rem' }}
                            />
                        </Box>
                    )}

                    {/* Export Options */}
                    <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        <Button
                            size="small"
                            variant="outlined"
                            startIcon={<ExportIcon />}
                            onClick={handleExportGeoJSON}
                        >
                            GeoJSON
                        </Button>
                        <Button
                            size="small"
                            variant="outlined"
                            startIcon={<ExportIcon />}
                            onClick={handleExport}
                        >
                            JSON
                        </Button>
                        <Button
                            size="small"
                            variant="contained"
                            color="primary"
                            startIcon={<ExportIcon />}
                            onClick={handleExportS102}
                        >
                            S-102
                        </Button>
                    </Box>
                </Box>

                {error && (
                    <Alert severity="error" sx={{ m: 1 }} onClose={() => setError('')}>
                        {error}
                    </Alert>
                )}

                {/* Filters */}
                <Accordion defaultExpanded={false}>
                    <AccordionSummary expandIcon={<ExpandIcon />}>
                        <FilterIcon sx={{ mr: 1 }} />
                        <Typography>Filters</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                        <Typography variant="subtitle2" gutterBottom>Confidence</Typography>
                        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                            <Chip
                                label="High"
                                size="small"
                                onClick={() => setShowHigh(!showHigh)}
                                color={showHigh ? 'error' : 'default'}
                                variant={showHigh ? 'filled' : 'outlined'}
                            />
                            <Chip
                                label="Medium"
                                size="small"
                                onClick={() => setShowMedium(!showMedium)}
                                color={showMedium ? 'warning' : 'default'}
                                variant={showMedium ? 'filled' : 'outlined'}
                            />
                            <Chip
                                label="Low"
                                size="small"
                                onClick={() => setShowLow(!showLow)}
                                color={showLow ? 'success' : 'default'}
                                variant={showLow ? 'filled' : 'outlined'}
                            />
                        </Box>
                        <Typography variant="subtitle2" gutterBottom>Decision</Typography>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                            <Chip
                                label="Pending"
                                size="small"
                                onClick={() => setShowPending(!showPending)}
                                variant={showPending ? 'filled' : 'outlined'}
                            />
                            <Chip
                                label="Accepted"
                                size="small"
                                onClick={() => setShowAccepted(!showAccepted)}
                                color={showAccepted ? 'success' : 'default'}
                                variant={showAccepted ? 'filled' : 'outlined'}
                            />
                            <Chip
                                label="Rejected"
                                size="small"
                                onClick={() => setShowRejected(!showRejected)}
                                color={showRejected ? 'error' : 'default'}
                                variant={showRejected ? 'filled' : 'outlined'}
                            />
                        </Box>
                    </AccordionDetails>
                </Accordion>

                {/* Quality Dashboard */}
                {runId && <QualityMetrics runId={runId} anomalies={anomalies} />}

                {/* Production Tools */}
                {run && (
                    <Accordion>
                        <AccordionSummary expandIcon={<ExpandIcon />}>
                            <Typography>🛠️ Production Tools</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                            <ProductionTools
                                datasetId={run.dataset_id}
                                datasetName="Current Dataset"
                                onSoundingsGenerated={setSoundingsGeojson}
                                onContoursGenerated={setContoursGeojson}

                                // Cleaning props
                                cleaningMethod={cleaningMethod}
                                cleaningKernel={cleaningKernel}
                                cleaningLoading={cleaningLoading}
                                cleaningResult={cleaningGeojson}
                                onCleaningMethodChange={setCleaningMethod}
                                onCleaningKernelChange={setCleaningKernel}
                                onClean={handleClean}
                            />
                        </AccordionDetails>
                    </Accordion>
                )}

                <Divider />

                {/* Anomaly List */}
                <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
                    <List dense disablePadding>
                        {filteredAnomalies.map((anomaly, index) => (
                            <ListItemButton
                                key={anomaly.id}
                                selected={selectedAnomaly?.id === anomaly.id}
                                onClick={() => handleSelectAnomaly(anomaly)}
                                sx={{
                                    borderLeft: `4px solid ${getConfidenceColor(anomaly.confidence_level)}`,
                                    '&:hover': { bgcolor: 'action.hover' },
                                }}
                            >
                                <ListItemText
                                    primary={
                                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <Typography variant="body2" fontWeight={500}>
                                                #{index + 1} {anomaly.anomaly_type.replace('_', ' ')}
                                            </Typography>
                                            {getDecisionBadge(anomaly.review_decision)}
                                        </Box>
                                    }
                                    secondary={
                                        <Box>
                                            <Typography variant="caption" color="text.secondary">
                                                Priority: {(anomaly.qc_priority * 100).toFixed(0)}% |
                                                Prob: {(anomaly.anomaly_probability * 100).toFixed(0)}%
                                            </Typography>
                                        </Box>
                                    }
                                />
                            </ListItemButton>
                        ))}
                    </List>
                </Box>

                {/* Review Actions */}
                {selectedAnomaly && (
                    <Box sx={{ p: 2, borderTop: '1px solid', borderColor: 'divider', bgcolor: 'background.default' }}>
                        <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                            Review: {selectedAnomaly.anomaly_type.replace('_', ' ').toUpperCase()}
                        </Typography>

                        {/* Explanation */}
                        <Accordion defaultExpanded>
                            <AccordionSummary expandIcon={<ExpandIcon />}>
                                <Typography variant="body2">Why was this flagged?</Typography>
                            </AccordionSummary>
                            <AccordionDetails sx={{ pt: 0 }}>
                                <Typography variant="body2" color="text.secondary" gutterBottom>
                                    {selectedAnomaly.explanation.primary_reason}
                                </Typography>
                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                                    {selectedAnomaly.explanation.detector_flags.map((flag) => (
                                        <Chip key={flag} label={flag} size="small" sx={{ fontSize: '0.65rem' }} />
                                    ))}
                                </Box>
                                {selectedAnomaly.explanation.features && (
                                    <Box sx={{ mt: 1 }}>
                                        {Object.entries(selectedAnomaly.explanation.features).slice(0, 4).map(([key, value]) => (
                                            <Typography key={key} variant="caption" display="block" color="text.secondary">
                                                {key}: {typeof value === 'number' ? value.toFixed(3) : value}
                                            </Typography>
                                        ))}
                                    </Box>
                                )}
                            </AccordionDetails>
                        </Accordion>

                        <TextField
                            fullWidth
                            size="small"
                            label="Comment (optional)"
                            value={reviewComment}
                            onChange={(e) => setReviewComment(e.target.value)}
                            multiline
                            rows={2}
                            sx={{ my: 2 }}
                        />

                        <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button
                                fullWidth
                                variant="contained"
                                color="success"
                                startIcon={<AcceptIcon />}
                                onClick={() => handleReview('accepted')}
                                disabled={submitting || selectedAnomaly.review_decision !== 'pending'}
                            >
                                Accept
                            </Button>
                            <Button
                                fullWidth
                                variant="contained"
                                color="error"
                                startIcon={<RejectIcon />}
                                onClick={() => handleReview('rejected')}
                                disabled={submitting || selectedAnomaly.review_decision !== 'pending'}
                            >
                                Reject
                            </Button>
                        </Box>

                        {selectedAnomaly.review_decision !== 'pending' && (
                            <Alert severity="info" sx={{ mt: 2 }}>
                                Already reviewed as {selectedAnomaly.review_decision}
                            </Alert>
                        )}
                    </Box>
                )}
            </Paper>
        </Box>
    );
}
