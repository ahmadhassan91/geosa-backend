/**
 * ProductionTools Component
 * 
 * UI for upstream production processing:
 * - Sounding Selection
 * - Contour Generation
 */

import { useState } from 'react';
import {
    Box,
    Card,
    CardContent,
    Typography,
    Button,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    TextField,
    CircularProgress,
    Alert,
    Stack,
    Chip,
} from '@mui/material';
import {
    ScatterPlot as SoundingIcon,
    Timeline as ContourIcon,
    Download as DownloadIcon,
} from '@mui/icons-material';
import { api } from '@/services/api';
import type { GeoJSONFeatureCollection } from '@/types/api';

interface ProductionToolsProps {
    datasetId: string;
    datasetName: string;
    onSoundingsGenerated?: (geojson: GeoJSONFeatureCollection) => void;
    onContoursGenerated?: (geojson: GeoJSONFeatureCollection) => void;
}

interface SoundingResult {
    geojson: GeoJSONFeatureCollection;
    count: number;
    scale: number;
}

interface ContourResult {
    geojson: GeoJSONFeatureCollection;
    count: number;
    interval: number;
}

export function ProductionTools({
    datasetId,
    datasetName,
    onSoundingsGenerated,
    onContoursGenerated,
}: ProductionToolsProps) {
    // Sounding selection state
    const [targetScale, setTargetScale] = useState(50000);
    const [selectionMode, setSelectionMode] = useState<'shoal' | 'deep' | 'representative'>('shoal');
    const [soundingLoading, setSoundingLoading] = useState(false);
    const [soundingResult, setSoundingResult] = useState<SoundingResult | null>(null);
    const [soundingError, setSoundingError] = useState<string | null>(null);

    // Contour generation state
    const [contourInterval, setContourInterval] = useState(5);
    const [smoothingIterations, setSmoothingIterations] = useState(3);
    const [contourLoading, setContourLoading] = useState(false);
    const [contourResult, setContourResult] = useState<ContourResult | null>(null);
    const [contourError, setContourError] = useState<string | null>(null);

    const handleGenerateSoundings = async () => {
        setSoundingLoading(true);
        setSoundingError(null);
        try {
            const result = await api.generateSoundings(datasetId, targetScale, selectionMode);
            const count = result.features?.length || 0;
            setSoundingResult({ geojson: result, count, scale: targetScale });
            onSoundingsGenerated?.(result);
        } catch (error: unknown) {
            const err = error as { message?: string };
            setSoundingError(err.message || 'Failed to generate soundings');
        } finally {
            setSoundingLoading(false);
        }
    };

    const handleGenerateContours = async () => {
        setContourLoading(true);
        setContourError(null);
        try {
            const result = await api.generateContours(datasetId, contourInterval, smoothingIterations);
            const count = result.features?.length || 0;
            setContourResult({ geojson: result, count, interval: contourInterval });
            onContoursGenerated?.(result);
        } catch (error: unknown) {
            const err = error as { message?: string };
            setContourError(err.message || 'Failed to generate contours');
        } finally {
            setContourLoading(false);
        }
    };

    const downloadGeoJSON = (data: GeoJSONFeatureCollection, filename: string) => {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                🛠️ Production Tools
            </Typography>
            <Typography variant="body2" color="text.secondary">
                Dataset: <strong>{datasetName}</strong>
            </Typography>

            {/* Sounding Selection */}
            <Card variant="outlined">
                <CardContent>
                    <Typography variant="subtitle1" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                        <SoundingIcon color="primary" />
                        Sounding Selection
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        AI-powered shoal-biased sounding selection for chart compilation.
                    </Typography>

                    <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
                        <FormControl size="small" sx={{ minWidth: 120 }}>
                            <InputLabel>Target Scale</InputLabel>
                            <Select
                                value={targetScale}
                                label="Target Scale"
                                onChange={(e) => setTargetScale(Number(e.target.value))}
                            >
                                <MenuItem value={10000}>1:10,000</MenuItem>
                                <MenuItem value={25000}>1:25,000</MenuItem>
                                <MenuItem value={50000}>1:50,000</MenuItem>
                                <MenuItem value={100000}>1:100,000</MenuItem>
                            </Select>
                        </FormControl>

                        <FormControl size="small" sx={{ minWidth: 140 }}>
                            <InputLabel>Selection Mode</InputLabel>
                            <Select
                                value={selectionMode}
                                label="Selection Mode"
                                onChange={(e) => setSelectionMode(e.target.value as 'shoal' | 'deep' | 'representative')}
                            >
                                <MenuItem value="shoal">Shoal (Min)</MenuItem>
                                <MenuItem value="deep">Deep (Max)</MenuItem>
                                <MenuItem value="representative">Representative</MenuItem>
                            </Select>
                        </FormControl>

                        <Button
                            variant="contained"
                            onClick={handleGenerateSoundings}
                            disabled={soundingLoading}
                            startIcon={soundingLoading ? <CircularProgress size={16} /> : <SoundingIcon />}
                        >
                            Generate
                        </Button>
                    </Stack>

                    {soundingError && <Alert severity="error" sx={{ mb: 2 }}>{soundingError}</Alert>}

                    {soundingResult && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                            <Chip
                                label={`${soundingResult.count} soundings`}
                                color="success"
                                size="small"
                            />
                            <Chip
                                label={`1:${soundingResult.scale.toLocaleString()}`}
                                variant="outlined"
                                size="small"
                            />
                            <Button
                                size="small"
                                startIcon={<DownloadIcon />}
                                onClick={() => downloadGeoJSON(soundingResult.geojson, `soundings_${targetScale}.geojson`)}
                            >
                                Download GeoJSON
                            </Button>
                        </Box>
                    )}
                </CardContent>
            </Card>

            {/* Contour Generation */}
            <Card variant="outlined">
                <CardContent>
                    <Typography variant="subtitle1" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                        <ContourIcon color="primary" />
                        Contour Generation
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Generate smoothed depth contours using Chaikin algorithm.
                    </Typography>

                    <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
                        <TextField
                            size="small"
                            label="Interval (m)"
                            type="number"
                            value={contourInterval}
                            onChange={(e) => setContourInterval(Number(e.target.value))}
                            sx={{ width: 100 }}
                            inputProps={{ min: 1, max: 100 }}
                        />

                        <TextField
                            size="small"
                            label="Smoothing"
                            type="number"
                            value={smoothingIterations}
                            onChange={(e) => setSmoothingIterations(Number(e.target.value))}
                            sx={{ width: 100 }}
                            inputProps={{ min: 0, max: 10 }}
                        />

                        <Button
                            variant="contained"
                            onClick={handleGenerateContours}
                            disabled={contourLoading}
                            startIcon={contourLoading ? <CircularProgress size={16} /> : <ContourIcon />}
                        >
                            Generate
                        </Button>
                    </Stack>

                    {contourError && <Alert severity="error" sx={{ mb: 2 }}>{contourError}</Alert>}

                    {contourResult && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                            <Chip
                                label={`${contourResult.count} contours`}
                                color="success"
                                size="small"
                            />
                            <Chip
                                label={`${contourResult.interval}m interval`}
                                variant="outlined"
                                size="small"
                            />
                            <Button
                                size="small"
                                startIcon={<DownloadIcon />}
                                onClick={() => downloadGeoJSON(contourResult.geojson, `contours_${contourInterval}m.geojson`)}
                            >
                                Download GeoJSON
                            </Button>
                        </Box>
                    )}
                </CardContent>
            </Card>
        </Box>
    );
}

export default ProductionTools;
