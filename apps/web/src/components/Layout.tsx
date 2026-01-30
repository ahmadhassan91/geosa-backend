/**
 * Application Layout Component
 */

import { ReactNode } from 'react';
import {
    AppBar,
    Box,
    Drawer,
    IconButton,
    Toolbar,
    Typography,
    Avatar,
    Menu,
    MenuItem,
    Divider,
    useTheme,
    Chip,
    FormControlLabel,
    Switch,
} from '@mui/material';
import {
    Menu as MenuIcon,
    Layers as LayersIcon,
    AccountCircle as AccountIcon,
    ExitToApp as LogoutIcon,
    WaterDrop as WaterIcon,
    Brightness4 as DarkIcon,
    Brightness7 as LightIcon,
} from '@mui/icons-material';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore, useAppStore, useThemeStore } from '@/stores';
import api from '@/services/api';

const DRAWER_WIDTH = 320;

interface LayoutProps {
    children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
    const theme = useTheme();
    const navigate = useNavigate();
    const { user, logout } = useAuthStore();
    const { sidebarOpen, toggleSidebar } = useAppStore();
    const { mode, toggleMode } = useThemeStore();
    const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

    const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
        setAnchorEl(event.currentTarget);
    };

    const handleMenuClose = () => {
        setAnchorEl(null);
    };

    const handleLogout = () => {
        api.logout();
        logout();
        navigate('/login');
    };

    return (
        <Box sx={{ display: 'flex', minHeight: '100vh' }}>
            {/* App Bar */}
            <AppBar
                position="fixed"
                sx={{
                    zIndex: theme.zIndex.drawer + 1,
                    background: mode === 'dark'
                        ? 'linear-gradient(135deg, #1e2a3b 0%, #0a0f1a 100%)'
                        : 'linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%)',
                    borderBottom: mode === 'dark'
                        ? '1px solid rgba(255,255,255,0.1)'
                        : '1px solid rgba(0,0,0,0.1)',
                    color: mode === 'dark' ? 'white' : 'inherit',
                }}
                elevation={0}
            >
                <Toolbar>
                    <IconButton
                        edge="start"
                        color="inherit"
                        onClick={toggleSidebar}
                        sx={{ mr: 2 }}
                    >
                        <MenuIcon />
                    </IconButton>

                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <WaterIcon sx={{ color: theme.palette.primary.main }} />
                        <Typography
                            variant="h6"
                            noWrap
                            component="div"
                            sx={{
                                fontWeight: 600,
                                color: mode === 'dark' ? 'white' : 'text.primary',
                            }}
                        >
                            HydroQ-QC-Assistant
                        </Typography>
                        <Chip
                            label="PoC v0.1.0"
                            size="small"
                            sx={{
                                ml: 1,
                                bgcolor: 'rgba(59, 130, 246, 0.2)',
                                color: theme.palette.primary.main,
                                fontSize: '0.7rem',
                            }}
                        />
                    </Box>

                    <Box sx={{ flexGrow: 1 }} />

                    {/* Theme Toggle */}
                    <IconButton onClick={toggleMode} color="inherit" title={`Switch to ${mode === 'dark' ? 'light' : 'dark'} mode`}>
                        {mode === 'dark' ? <LightIcon /> : <DarkIcon />}
                    </IconButton>

                    {/* User Menu */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Chip
                            label={user?.role?.toUpperCase()}
                            size="small"
                            color={user?.role === 'admin' ? 'error' : user?.role === 'hydrographer' ? 'primary' : 'default'}
                            sx={{ fontSize: '0.7rem' }}
                        />
                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                            {user?.username}
                        </Typography>
                        <IconButton onClick={handleMenuOpen} color="inherit">
                            <Avatar sx={{ width: 32, height: 32, bgcolor: theme.palette.primary.main }}>
                                {user?.username?.[0]?.toUpperCase() || 'U'}
                            </Avatar>
                        </IconButton>
                    </Box>

                    <Menu
                        anchorEl={anchorEl}
                        open={Boolean(anchorEl)}
                        onClose={handleMenuClose}
                        PaperProps={{
                            sx: {
                                bgcolor: 'background.paper',
                                border: '1px solid',
                                borderColor: 'divider',
                            },
                        }}
                    >
                        <MenuItem disabled>
                            <AccountIcon sx={{ mr: 1 }} />
                            {user?.email}
                        </MenuItem>
                        <Divider />
                        <MenuItem onClick={handleLogout}>
                            <LogoutIcon sx={{ mr: 1 }} />
                            Logout
                        </MenuItem>
                    </Menu>
                </Toolbar>
            </AppBar>

            {/* Sidebar */}
            <Drawer
                variant="persistent"
                anchor="left"
                open={sidebarOpen}
                sx={{
                    width: sidebarOpen ? DRAWER_WIDTH : 0,
                    flexShrink: 0,
                    transition: theme.transitions.create('width', {
                        easing: theme.transitions.easing.sharp,
                        duration: theme.transitions.duration.enteringScreen,
                    }),
                    '& .MuiDrawer-paper': {
                        width: DRAWER_WIDTH,
                        boxSizing: 'border-box',
                        bgcolor: 'background.paper',
                        borderRight: '1px solid',
                        borderColor: 'divider',
                    },
                }}
            >
                <Toolbar />
                <Box sx={{ p: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                        <LayersIcon sx={{ color: 'primary.main' }} />
                        <Typography variant="subtitle1" fontWeight={600}>
                            Map Layers
                        </Typography>
                    </Box>

                    {/* Layer Controls - Only active if we have store access (always true here) */}
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {/* Heatmap Toggle */}
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={useAppStore((state) => state.showHeatmap)}
                                    onChange={() => useAppStore.getState().toggleHeatmap()}
                                    size="small"
                                />
                            }
                            label={<Typography variant="body2">Density Heatmap</Typography>}
                        />

                        {/* Anomalies Toggle */}
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={useAppStore((state) => state.showAnomalyPolygons)}
                                    onChange={() => useAppStore.getState().toggleAnomalyPolygons()}
                                    size="small"
                                />
                            }
                            label={<Typography variant="body2">Anomaly Polygons</Typography>}
                        />
                    </Box>

                    <Divider sx={{ my: 2 }} />

                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                        Legends
                    </Typography>

                    {/* Simple Legend */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                        <Box sx={{ width: 12, height: 12, bgcolor: '#ef4444', borderRadius: '50%' }} />
                        <Typography variant="caption">High Confidence</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                        <Box sx={{ width: 12, height: 12, bgcolor: '#f59e0b', borderRadius: '50%' }} />
                        <Typography variant="caption">Medium Confidence</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Box sx={{ width: 12, height: 12, bgcolor: '#10b981', borderRadius: '50%' }} />
                        <Typography variant="caption">Low Confidence</Typography>
                    </Box>
                </Box>
            </Drawer>

            {/* Main Content */}
            <Box
                component="main"
                sx={{
                    flexGrow: 1,
                    transition: theme.transitions.create('margin', {
                        easing: theme.transitions.easing.sharp,
                        duration: theme.transitions.duration.enteringScreen,
                    }),
                    marginLeft: sidebarOpen ? 0 : `-${DRAWER_WIDTH}px`,
                    display: 'flex',
                    flexDirection: 'column',
                }}
            >
                <Toolbar />
                <Box sx={{ flexGrow: 1, p: 0 }}>
                    {children}
                </Box>
            </Box>
        </Box>
    );
}
