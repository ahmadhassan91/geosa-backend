/**
 * Global state management using Zustand
 */

import { create } from 'zustand';
import type { User, Dataset, Run, Anomaly } from '@/types/api';

interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
    setUser: (user: User | null) => void;
    logout: () => void;
}

interface AppState {
    // Current selections
    selectedDataset: Dataset | null;
    selectedRun: Run | null;
    selectedAnomaly: Anomaly | null;

    // Map state
    mapCenter: [number, number];
    mapZoom: number;
    showHeatmap: boolean;
    showAnomalyPolygons: boolean;

    // UI state
    sidebarOpen: boolean;
    isLoading: boolean;

    // Actions
    setSelectedDataset: (dataset: Dataset | null) => void;
    setSelectedRun: (run: Run | null) => void;
    setSelectedAnomaly: (anomaly: Anomaly | null) => void;
    setMapCenter: (center: [number, number]) => void;
    setMapZoom: (zoom: number) => void;
    toggleHeatmap: () => void;
    toggleAnomalyPolygons: () => void;
    toggleSidebar: () => void;
    setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
    user: null,
    isAuthenticated: false,
    setUser: (user) => set({ user, isAuthenticated: !!user }),
    logout: () => set({ user: null, isAuthenticated: false }),
}));

export const useAppStore = create<AppState>((set) => ({
    // Initial state
    selectedDataset: null,
    selectedRun: null,
    selectedAnomaly: null,
    mapCenter: [138.6, -34.9], // Default to Adelaide, SA
    mapZoom: 10,
    showHeatmap: true,
    showAnomalyPolygons: true,
    sidebarOpen: true,
    isLoading: false,

    // Actions
    setSelectedDataset: (dataset) => set({ selectedDataset: dataset }),
    setSelectedRun: (run) => set({ selectedRun: run, selectedAnomaly: null }),
    setSelectedAnomaly: (anomaly) => set({ selectedAnomaly: anomaly }),
    setMapCenter: (center) => set({ mapCenter: center }),
    setMapZoom: (zoom) => set({ mapZoom: zoom }),
    toggleHeatmap: () => set((state) => ({ showHeatmap: !state.showHeatmap })),
    toggleAnomalyPolygons: () => set((state) => ({ showAnomalyPolygons: !state.showAnomalyPolygons })),
    toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
    setLoading: (loading) => set({ isLoading: loading }),
}));

// Theme store for light/dark mode
interface ThemeState {
    mode: 'light' | 'dark';
    toggleMode: () => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
    mode: (localStorage.getItem('theme_mode') as 'light' | 'dark') || 'dark',
    toggleMode: () => set((state) => {
        const newMode = state.mode === 'dark' ? 'light' : 'dark';
        localStorage.setItem('theme_mode', newMode);
        return { mode: newMode };
    }),
}));

