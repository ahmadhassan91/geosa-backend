/**
 * Login Page
 */

import { useState } from 'react';
import {
    Box,
    Card,
    CardContent,
    TextField,
    Button,
    Typography,
    Alert,
    CircularProgress,
    Tabs,
    Tab,
    useTheme,
} from '@mui/material';
import { WaterDrop as WaterIcon, Lock as LockIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores';
import api from '@/services/api';

interface TabPanelProps {
    children?: React.ReactNode;
    index: number;
    value: number;
}

function TabPanel(props: TabPanelProps) {
    const { children, value, index, ...other } = props;
    return (
        <div hidden={value !== index} {...other}>
            {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
        </div>
    );
}

export default function LoginPage() {
    const theme = useTheme();
    const navigate = useNavigate();
    const { setUser } = useAuthStore();

    const [tab, setTab] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Login form
    const [loginUsername, setLoginUsername] = useState('');
    const [loginPassword, setLoginPassword] = useState('');

    // Register form
    const [regUsername, setRegUsername] = useState('');
    const [regEmail, setRegEmail] = useState('');
    const [regPassword, setRegPassword] = useState('');

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            await api.login(loginUsername, loginPassword);
            const user = await api.getCurrentUser();
            setUser(user);
            navigate('/');
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Login failed. Please check your credentials.';
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            await api.register(regUsername, regEmail, regPassword, 'hydrographer');
            // Auto-login after registration
            await api.login(regUsername, regPassword);
            const user = await api.getCurrentUser();
            setUser(user);
            navigate('/');
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Registration failed.';
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Box
            sx={{
                minHeight: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: `linear-gradient(135deg, ${theme.palette.background.default} 0%, #1a2634 100%)`,
                p: 2,
            }}
        >
            <Card
                sx={{
                    maxWidth: 440,
                    width: '100%',
                    bgcolor: 'background.paper',
                    border: '1px solid',
                    borderColor: 'divider',
                    boxShadow: '0 20px 40px rgba(0,0,0,0.4)',
                }}
            >
                <CardContent sx={{ p: 4 }}>
                    {/* Logo & Title */}
                    <Box sx={{ textAlign: 'center', mb: 4 }}>
                        <Box
                            sx={{
                                width: 64,
                                height: 64,
                                borderRadius: 2,
                                bgcolor: 'primary.main',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                mx: 'auto',
                                mb: 2,
                                boxShadow: '0 8px 16px rgba(59, 130, 246, 0.3)',
                            }}
                        >
                            <WaterIcon sx={{ fontSize: 32, color: 'white' }} />
                        </Box>
                        <Typography variant="h5" fontWeight={600} gutterBottom>
                            HydroQ-QC-Assistant
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            Multibeam Bathymetry QC Decision Support
                        </Typography>
                    </Box>

                    {/* Security Notice */}
                    <Alert
                        severity="info"
                        icon={<LockIcon />}
                        sx={{
                            mb: 3,
                            bgcolor: 'rgba(59, 130, 246, 0.1)',
                            border: '1px solid rgba(59, 130, 246, 0.3)',
                        }}
                    >
                        <Typography variant="body2">
                            <strong>On-Premises Only.</strong> This system runs entirely locally with no external connections.
                        </Typography>
                    </Alert>

                    {error && (
                        <Alert severity="error" sx={{ mb: 3 }}>
                            {error}
                        </Alert>
                    )}

                    {/* Tabs */}
                    <Tabs
                        value={tab}
                        onChange={(_, v) => setTab(v)}
                        variant="fullWidth"
                        sx={{ mb: 2 }}
                    >
                        <Tab label="Login" />
                        <Tab label="Register" />
                    </Tabs>

                    {/* Login Form */}
                    <TabPanel value={tab} index={0}>
                        <form onSubmit={handleLogin}>
                            <TextField
                                fullWidth
                                label="Username"
                                value={loginUsername}
                                onChange={(e) => setLoginUsername(e.target.value)}
                                margin="normal"
                                required
                                autoFocus
                            />
                            <TextField
                                fullWidth
                                label="Password"
                                type="password"
                                value={loginPassword}
                                onChange={(e) => setLoginPassword(e.target.value)}
                                margin="normal"
                                required
                            />
                            <Button
                                type="submit"
                                fullWidth
                                variant="contained"
                                size="large"
                                disabled={loading}
                                sx={{ mt: 3, py: 1.5 }}
                            >
                                {loading ? <CircularProgress size={24} /> : 'Sign In'}
                            </Button>
                        </form>
                    </TabPanel>

                    {/* Register Form */}
                    <TabPanel value={tab} index={1}>
                        <form onSubmit={handleRegister}>
                            <TextField
                                fullWidth
                                label="Username"
                                value={regUsername}
                                onChange={(e) => setRegUsername(e.target.value)}
                                margin="normal"
                                required
                            />
                            <TextField
                                fullWidth
                                label="Email"
                                type="email"
                                value={regEmail}
                                onChange={(e) => setRegEmail(e.target.value)}
                                margin="normal"
                                required
                            />
                            <TextField
                                fullWidth
                                label="Password"
                                type="password"
                                value={regPassword}
                                onChange={(e) => setRegPassword(e.target.value)}
                                margin="normal"
                                required
                                helperText="Minimum 8 characters"
                            />
                            <Button
                                type="submit"
                                fullWidth
                                variant="contained"
                                size="large"
                                disabled={loading}
                                sx={{ mt: 3, py: 1.5 }}
                            >
                                {loading ? <CircularProgress size={24} /> : 'Create Account'}
                            </Button>
                        </form>
                    </TabPanel>
                </CardContent>
            </Card>
        </Box>
    );
}
