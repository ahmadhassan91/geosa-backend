# HydroQ-QC-Assistant

**On-Premises, Human-in-the-Loop Multibeam Bathymetry QC Assistant**

A decision-support system for hydrographic multibeam bathymetry quality control. This system:
- 🔍 **Detects anomalies**: spikes, holes, seams, noise bands, discontinuities
- 📊 **Assigns confidence scores** with full explainability
- 🗺️ **Produces QC priority heatmaps** and ranked review candidates
- ✅ **Enables human review** with full audit trail
- 🔒 **Runs entirely on-premises** - no external APIs, no cloud dependencies

## ⚠️ Non-Negotiable Principles

1. **Decision-Support Only**: Never auto-corrects soundings, never generates "official" chart products
2. **Human Authority**: Every AI suggestion is reviewable, overridable, and auditable
3. **On-Prem Only**: No cloud APIs, no external telemetry
4. **Explainability**: Every anomaly flag includes "why" with transparent features/thresholds

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React + Vite)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │   Map View   │  │ Anomaly List │  │   Review Panel        │  │
│  │  (MapLibre)  │  │  (Ranked)    │  │ Accept/Reject/Comment │  │
│  └──────────────┘  └──────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   API       │  │ Application │  │      Domain             │  │
│  │  Routes     │◄─┤  Use Cases  │◄─┤  Entities               │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│         │                │                    │                  │
│         └────────────────┴────────────────────┘                  │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   Infrastructure                             │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │ │
│  │  │ Postgres │  │  File    │  │  Raster  │  │ ML Pipeline │  │ │
│  │  │   Repo   │  │  Store   │  │  Utils   │  │  (sklearn)  │  │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └─────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- GDAL libraries (for rasterio)

### 1. Setup PostgreSQL

```bash
# Create database
createdb hydroq_qc

# Or use the init script
psql -U postgres -f infra/db/init.sql
```

### 2. Setup Backend

```bash
cd apps/api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start API server
uvicorn src.main:app --reload --port 8000
```

### 3. Setup Frontend

```bash
cd apps/web

# Install dependencies
npm install

# Start dev server
npm run dev
```

### 4. Run Demo

```bash
# Generate sample bathymetry data
python scripts/generate_sample_data.py

# Or ingest real GEBCO data
python scripts/ingest_demo_data.py

# Access the application
open http://localhost:5173
```

### 5. Login

- **Username**: `demo_user`
- **Password**: `DemoUser123!`

### Troubleshooting

**Login fails with 401?**
- Ensure backend is running (`uvicorn src.main:app --reload --port 8000`)
- Clear browser localStorage and retry
- Check for leading/trailing spaces in username

**Analysis stays "pending"?**  
- Ensure `scikit-image` is installed: `pip install scikit-image`
- Check backend terminal for errors

## 📂 Project Structure

```
hydroq-qc-assistant/
├── apps/
│   ├── api/          # FastAPI backend (Clean Architecture)
│   └── web/          # React + Vite frontend
├── packages/
│   └── shared/       # Shared TypeScript types
├── data/             # Sample datasets + outputs
├── scripts/          # Utility scripts
├── docs/             # Documentation
└── infra/            # Infrastructure configs
```

## 🔐 Security & Governance

- **RBAC Roles**: Admin, Hydrographer, Viewer
- **JWT Authentication**: Local token-based auth
- **Audit Trail**: Append-only log of all decisions
- **No External Calls**: All processing is local

## 📊 Supported Formats

- **Raster**: GeoTIFF bathymetry grids
- **Points**: CSV/Parquet soundings (x, y, z + optional flags)
- **Exports**: IHO S-102 v2.2 HDF5 (S-102-Ready)*, GeoJSON

*\*Full compliance features pending. See [S-102 Compliance Roadmap](docs/S102_COMPLIANCE_ROADMAP.md)*

## 🧪 Testing

```bash
# Backend tests
cd apps/api
pytest

# Frontend tests
cd apps/web
npm test
```

## 📖 Documentation

- [Architecture](docs/ARCHITECTURE.md) - C4 diagrams
- [Data Flow](docs/DATA_FLOW.md) - Pipeline documentation
- [Threat Model](docs/THREAT_MODEL.md) - Security considerations
- [Runbooks](docs/RUNBOOKS.md) - Operational procedures
- [PoC Limitations](docs/POC_LIMITATIONS.md) - Known constraints & next steps

## 📄 License

Internal use only - GeoSA Hydrography Division
