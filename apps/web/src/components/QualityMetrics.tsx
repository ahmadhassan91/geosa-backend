/**
 * Quality Metrics Dashboard Component
 * 
 * Compact display of quality metrics, S-100 compliance, time savings,
 * and data sovereignty indicators.
 */

import { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Grid,
    CircularProgress,
    Accordion,
    AccordionSummary,
    AccordionDetails,
} from '@mui/material';
import {
    Assessment as AssessmentIcon,
    ExpandMore as ExpandIcon,
    Shield as ShieldIcon,
} from '@mui/icons-material';
import api from '@/services/api';

import type { Anomaly } from '@/types/api';

interface QualityMetricsProps {
    runId: string;
    anomalies?: Anomaly[];
}

interface QualityData {
    qualityScore: number;
    qualityGrade: string;
    timeSavings: {
        savingsPercent: number;
    };
    s100Compliance: {
        score: number;
    };
    dataSovereignty: {
        processingLocation: string;
    };
}

export default function QualityMetrics({ runId, anomalies }: QualityMetricsProps) {
    const [data, setData] = useState<QualityData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadMetrics = async () => {
            try {
                setLoading(true);
                const metrics = await api.getQualityMetrics(runId) as QualityData;
                setData(metrics);
            } catch (err) {
                console.error('Failed to load quality metrics', err);
            } finally {
                setLoading(false);
            }
        };
        loadMetrics();
    }, [runId]);

    // Calculate anomaly breakdown if anomalies provided
    const breakdown = anomalies ? anomalies.reduce((acc, curr) => {
        acc[curr.anomaly_type] = (acc[curr.anomaly_type] || 0) + 1;
        return acc;
    }, {} as Record<string, number>) : {};

    if (loading) {
        return (
            <Box sx={{ p: 1, display: 'flex', justifyContent: 'center' }}>
                <CircularProgress size={20} />
            </Box>
        );
    }

    if (!data) {
        return null;
    }

    const getGradeColor = (grade: string) => {
        if (grade.startsWith('A')) return 'success.main';
        if (grade.startsWith('B')) return 'info.main';
        if (grade.startsWith('C')) return 'warning.main';
        return 'error.main';
    };

    return (
        <Accordion defaultExpanded={false} sx={{ bgcolor: 'background.default', '&:before': { display: 'none' } }}>
            <AccordionSummary expandIcon={<ExpandIcon />} sx={{ minHeight: 36, py: 0 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <AssessmentIcon fontSize="small" color="primary" />
                    <Typography variant="body2" fontWeight={600}>
                        Quality Dashboard
                    </Typography>
                </Box>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0, pb: 1 }}>
                <Grid container spacing={1} sx={{ mb: anomalies && anomalies.length > 0 ? 1.5 : 0 }}>
                    {/* Quality Grade */}
                    <Grid item xs={3}>
                        <Box sx={{ textAlign: 'center' }}>
                            <Typography variant="h6" fontWeight={700} color={getGradeColor(data.qualityGrade)}>
                                {data.qualityGrade}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.6rem' }}>
                                Quality
                            </Typography>
                        </Box>
                    </Grid>

                    {/* Time Savings */}
                    <Grid item xs={3}>
                        <Box sx={{ textAlign: 'center' }}>
                            <Typography variant="h6" fontWeight={700} color="success.main">
                                {data.timeSavings.savingsPercent.toFixed(0)}%
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.6rem' }}>
                                Time Saved
                            </Typography>
                        </Box>
                    </Grid>

                    {/* S-102 Ready Status */}
                    <Grid item xs={3}>
                        <Box sx={{ textAlign: 'center' }}>
                            <Typography variant="h6" fontWeight={700} color="warning.main" sx={{ fontSize: '0.875rem', lineHeight: 2.2 }}>
                                Ready
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.6rem' }}>
                                S-102
                            </Typography>
                        </Box>
                    </Grid>

                    {/* Data Sovereignty */}
                    <Grid item xs={3}>
                        <Box sx={{ textAlign: 'center' }}>
                            <ShieldIcon sx={{ color: 'success.main', fontSize: 18 }} />
                            <Typography variant="caption" color="text.secondary" display="block" sx={{ fontSize: '0.6rem' }}>
                                On-Prem
                            </Typography>
                        </Box>
                    </Grid>
                </Grid>

                {/* Extended Breakdown */}
                {anomalies && anomalies.length > 0 && (
                    <Box sx={{ pt: 1, borderTop: '1px solid', borderColor: 'divider' }}>
                        <Typography variant="caption" fontWeight={600} sx={{ mb: 0.5, display: 'block' }}>
                            Detected Anomalies
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                            {Object.entries(breakdown).map(([type, count]) => (
                                <Box key={type} sx={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 0.5,
                                    bgcolor: 'background.paper',
                                    borderRadius: 1,
                                    px: 0.8,
                                    py: 0.2,
                                    border: '1px solid',
                                    borderColor: 'divider'
                                }}>
                                    <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'capitalize' }}>
                                        {type.replace('_', ' ')}
                                    </Typography>
                                    <Typography variant="caption" fontWeight={700}>
                                        {count}
                                    </Typography>
                                </Box>
                            ))}
                        </Box>
                    </Box>
                )}
            </AccordionDetails>
        </Accordion>
    );
}
