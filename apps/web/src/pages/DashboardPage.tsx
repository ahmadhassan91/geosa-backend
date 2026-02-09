/**
 * Dashboard Page - Dataset and Run Management
 */

import { useState, useEffect } from 'react';
import {
    Box,
    Grid,
    Card,
    CardContent,
    Typography,
    Button,
    IconButton,
    Chip,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    CircularProgress,
    Alert,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Tooltip,
} from '@mui/material';
import {
    CloudUpload as UploadIcon,
    PlayArrow as RunIcon,
    Visibility as ViewIcon,
    Delete as DeleteIcon,
    Refresh as RefreshIcon,
    Storage as DatasetIcon,
    Analytics as AnalyticsIcon,
    Warning as WarningIcon,
    CheckCircle as SuccessIcon,
    Error as ErrorIcon,
    Schedule as PendingIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import api from '@/services/api';
import type { Dataset, Run } from '@/types/api';

export default function DashboardPage() {
    const navigate = useNavigate();

    const [datasets, setDatasets] = useState<Dataset[]>([]);
    const [runs, setRuns] = useState<Run[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    // Upload dialog
    const [uploadOpen, setUploadOpen] = useState(false);
    const [uploadName, setUploadName] = useState('');
    const [uploadDesc, setUploadDesc] = useState('');
    const [uploadFile, setUploadFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);

    const loadData = async () => {
        try {
            setLoading(true);
            const [datasetRes, runRes] = await Promise.all([
                api.listDatasets(),
                api.listRuns(),
            ]);
            setDatasets(datasetRes.items);
            setRuns(runRes.items);
        } catch (err) {
            setError('Failed to load data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleUpload = async () => {
        if (!uploadFile || !uploadName) return;

        setUploading(true);
        try {
            await api.uploadDataset(uploadName, uploadDesc, uploadFile);
            setUploadOpen(false);
            setUploadName('');
            setUploadDesc('');
            setUploadFile(null);
            loadData();
        } catch (err) {
            setError('Failed to upload dataset');
            console.error(err);
        } finally {
            setUploading(false);
        }
    };

    const handleStartRun = async (datasetId: string) => {
        try {
            const run = await api.createRun(datasetId);
            // Navigate to analysis page
            navigate(`/analysis/${run.id}`);
        } catch (err) {
            setError('Failed to start analysis');
            console.error(err);
        }
    };

    const handleDeleteDataset = async (id: string) => {
        if (!confirm('Are you sure you want to delete this dataset?')) return;
        try {
            await api.deleteDataset(id);
            loadData();
        } catch (err) {
            setError('Failed to delete dataset');
            console.error(err);
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed':
                return <SuccessIcon sx={{ color: 'success.main' }} />;
            case 'failed':
                return <ErrorIcon sx={{ color: 'error.main' }} />;
            case 'processing':
                return <CircularProgress size={20} />;
            default:
                return <PendingIcon sx={{ color: 'text.secondary' }} />;
        }
    };

    const getStatusColor = (status: string): 'success' | 'error' | 'warning' | 'default' => {
        switch (status) {
            case 'completed': return 'success';
            case 'failed': return 'error';
            case 'processing': return 'warning';
            default: return 'default';
        }
    };

    const formatBytes = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    if (loading) {
        return (
            <Box sx={{ p: 4, display: 'flex', justifyContent: 'center' }}>
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Box sx={{ p: 3 }}>
            {/* Header */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
                <Box>
                    <Typography variant="h4" fontWeight={600} gutterBottom>
                        Dashboard
                    </Typography>
                    <Typography variant="body1" color="text.secondary">
                        Manage datasets and analysis runs
                    </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button
                        startIcon={<RefreshIcon />}
                        onClick={loadData}
                        variant="outlined"
                    >
                        Refresh
                    </Button>
                    <Button
                        startIcon={<UploadIcon />}
                        onClick={() => setUploadOpen(true)}
                        variant="contained"
                    >
                        Upload Dataset
                    </Button>
                </Box>
            </Box>

            {error && (
                <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
                    {error}
                </Alert>
            )}

            {/* Stats Cards */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider' }}>
                        <CardContent>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: 'primary.main' }}>
                                    <DatasetIcon sx={{ color: 'white' }} />
                                </Box>
                                <Box>
                                    <Typography variant="h4" fontWeight={600}>{datasets.length}</Typography>
                                    <Typography variant="body2" color="text.secondary">Datasets</Typography>
                                </Box>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider' }}>
                        <CardContent>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: 'secondary.main' }}>
                                    <AnalyticsIcon sx={{ color: 'white' }} />
                                </Box>
                                <Box>
                                    <Typography variant="h4" fontWeight={600}>{runs.length}</Typography>
                                    <Typography variant="body2" color="text.secondary">Analysis Runs</Typography>
                                </Box>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider' }}>
                        <CardContent>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: 'warning.main' }}>
                                    <WarningIcon sx={{ color: 'white' }} />
                                </Box>
                                <Box>
                                    <Typography variant="h4" fontWeight={600}>
                                        {runs.reduce((sum, r) => sum + r.total_anomalies, 0)}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">Total Anomalies</Typography>
                                </Box>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider' }}>
                        <CardContent>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: 'error.main' }}>
                                    <WarningIcon sx={{ color: 'white' }} />
                                </Box>
                                <Box>
                                    <Typography variant="h4" fontWeight={600}>
                                        {runs.reduce((sum, r) => sum + r.high_confidence_count, 0)}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">High Priority</Typography>
                                </Box>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            <Grid container spacing={3}>
                {/* Datasets Table */}
                <Grid item xs={12} lg={6}>
                    <Card sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider' }}>
                        <CardContent>
                            <Typography variant="h6" fontWeight={600} gutterBottom>
                                Datasets
                            </Typography>
                            <TableContainer>
                                <Table size="small">
                                    <TableHead>
                                        <TableRow>
                                            <TableCell>Name</TableCell>
                                            <TableCell>Type</TableCell>
                                            <TableCell>Size</TableCell>
                                            <TableCell align="right">Actions</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {datasets.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={4} sx={{ textAlign: 'center', py: 4 }}>
                                                    <Typography color="text.secondary">
                                                        No datasets yet. Upload one to get started.
                                                    </Typography>
                                                </TableCell>
                                            </TableRow>
                                        ) : (
                                            datasets.map((dataset) => (
                                                <TableRow key={dataset.id} hover>
                                                    <TableCell>
                                                        <Typography variant="body2" fontWeight={500}>
                                                            {dataset.name}
                                                        </Typography>
                                                    </TableCell>
                                                    <TableCell>
                                                        <Chip
                                                            label={dataset.file_type}
                                                            size="small"
                                                            sx={{ fontSize: '0.7rem' }}
                                                        />
                                                    </TableCell>
                                                    <TableCell>
                                                        <Typography variant="body2" color="text.secondary">
                                                            {formatBytes(dataset.file_size_bytes)}
                                                        </Typography>
                                                    </TableCell>
                                                    <TableCell align="right">
                                                        <Tooltip title="Start Analysis">
                                                            <IconButton
                                                                size="small"
                                                                onClick={() => handleStartRun(dataset.id)}
                                                                color="primary"
                                                            >
                                                                <RunIcon />
                                                            </IconButton>
                                                        </Tooltip>
                                                        <Tooltip title="Delete">
                                                            <IconButton
                                                                size="small"
                                                                onClick={() => handleDeleteDataset(dataset.id)}
                                                                color="error"
                                                            >
                                                                <DeleteIcon />
                                                            </IconButton>
                                                        </Tooltip>
                                                    </TableCell>
                                                </TableRow>
                                            ))
                                        )}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        </CardContent>
                    </Card>
                </Grid>

                {/* Recent Runs Table */}
                <Grid item xs={12} lg={6}>
                    <Card sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider' }}>
                        <CardContent>
                            <Typography variant="h6" fontWeight={600} gutterBottom>
                                Recent Analysis Runs
                            </Typography>
                            <TableContainer>
                                <Table size="small">
                                    <TableHead>
                                        <TableRow>
                                            <TableCell>Status</TableCell>
                                            <TableCell>Anomalies</TableCell>
                                            <TableCell>Duration</TableCell>
                                            <TableCell align="right">Actions</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {runs.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={4} sx={{ textAlign: 'center', py: 4 }}>
                                                    <Typography color="text.secondary">
                                                        No analysis runs yet.
                                                    </Typography>
                                                </TableCell>
                                            </TableRow>
                                        ) : (
                                            runs.slice(0, 10).map((run) => (
                                                <TableRow key={run.id} hover>
                                                    <TableCell>
                                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                            {getStatusIcon(run.status)}
                                                            <Chip
                                                                label={run.status}
                                                                size="small"
                                                                color={getStatusColor(run.status)}
                                                                sx={{ fontSize: '0.7rem' }}
                                                            />
                                                        </Box>
                                                    </TableCell>
                                                    <TableCell>
                                                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                                                            <Chip
                                                                label={`${run.high_confidence_count}H`}
                                                                size="small"
                                                                sx={{ bgcolor: 'error.main', color: 'white', fontSize: '0.65rem' }}
                                                            />
                                                            <Chip
                                                                label={`${run.medium_confidence_count}M`}
                                                                size="small"
                                                                sx={{ bgcolor: 'warning.main', color: 'white', fontSize: '0.65rem' }}
                                                            />
                                                            <Chip
                                                                label={`${run.low_confidence_count}L`}
                                                                size="small"
                                                                sx={{ bgcolor: 'success.main', color: 'white', fontSize: '0.65rem' }}
                                                            />
                                                        </Box>
                                                    </TableCell>
                                                    <TableCell>
                                                        <Typography variant="body2" color="text.secondary">
                                                            {run.duration_seconds
                                                                ? `${run.duration_seconds.toFixed(1)}s`
                                                                : '-'}
                                                        </Typography>
                                                    </TableCell>
                                                    <TableCell align="right">
                                                        <Tooltip title="View Analysis">
                                                            <span>
                                                                <IconButton
                                                                    size="small"
                                                                    onClick={() => navigate(`/analysis/${run.id}`)}
                                                                    color="primary"
                                                                    disabled={run.status !== 'completed'}
                                                                >
                                                                    <ViewIcon />
                                                                </IconButton>
                                                            </span>
                                                        </Tooltip>
                                                    </TableCell>
                                                </TableRow>
                                            ))
                                        )}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Upload Dialog */}
            <Dialog open={uploadOpen} onClose={() => setUploadOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Upload Dataset</DialogTitle>
                <DialogContent>
                    <TextField
                        fullWidth
                        label="Dataset Name"
                        value={uploadName}
                        onChange={(e) => setUploadName(e.target.value)}
                        margin="normal"
                        required
                    />
                    <TextField
                        fullWidth
                        label="Description"
                        value={uploadDesc}
                        onChange={(e) => setUploadDesc(e.target.value)}
                        margin="normal"
                        multiline
                        rows={2}
                    />
                    <Button
                        variant="outlined"
                        component="label"
                        fullWidth
                        sx={{ mt: 2, py: 2 }}
                    >
                        {uploadFile ? uploadFile.name : 'Select File (.tif, .csv, .parquet)'}
                        <input
                            type="file"
                            hidden
                            accept=".tif,.tiff,.csv,.parquet"
                            onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                        />
                    </Button>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setUploadOpen(false)}>Cancel</Button>
                    <Button
                        onClick={handleUpload}
                        variant="contained"
                        disabled={!uploadFile || !uploadName || uploading}
                    >
                        {uploading ? <CircularProgress size={24} /> : 'Upload'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
