# HydroQ-QC-Assistant Architecture

## C4 Model Diagrams

### Level 1: System Context

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HydroQ-QC-Assistant                                │
│                  Multibeam Bathymetry QC Decision Support                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Uses
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Hydrographer                                    │
│                          [Human Decision Maker]                              │
│                                                                              │
│  • Reviews anomaly detections                                                │
│  • Accepts/rejects findings with comments                                    │
│  • Makes final quality control decisions                                     │
│  • Exports review reports                                                    │
└─────────────────────────────────────────────────────────────────────────────┘

External Systems (None - Fully On-Premises):
• No cloud APIs
• No external databases
• No telemetry services
• All processing local
```

### Level 2: Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        HydroQ-QC-Assistant System                            │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     Web Application                                  │    │
│  │                    [React + Vite + TypeScript]                       │    │
│  │                                                                      │    │
│  │  • Interactive map with anomaly polygons (MapLibre GL)              │    │
│  │  • Ranked anomaly list with filtering                               │    │
│  │  • Review workflow (Accept/Reject/Comment)                          │    │
│  │  • Export capabilities                                               │    │
│  │                                                                      │    │
│  │  Port: 5173                                                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    │ HTTP/REST                               │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     API Server                                       │    │
│  │                    [Python FastAPI]                                  │    │
│  │                                                                      │    │
│  │  Endpoints:                                                          │    │
│  │  • POST /datasets - Upload bathymetry files                         │    │
│  │  • POST /runs - Start analysis                                      │    │
│  │  • GET  /runs/{id}/anomalies - List detected anomalies              │    │
│  │  • POST /anomalies/{id}/review - Submit review decision             │    │
│  │  • GET  /runs/{id}/export - Export results                          │    │
│  │                                                                      │    │
│  │  Port: 8000                                                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│          │                   │                    │                          │
│          │ SQL               │ File I/O          │ ML Inference             │
│          ▼                   ▼                    ▼                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────────┐    │
│  │  PostgreSQL  │   │ File Store   │   │     ML Pipeline              │    │
│  │  Database    │   │              │   │   [scikit-learn]             │    │
│  │              │   │ • Uploads    │   │                               │    │
│  │ • Users      │   │ • Heatmaps   │   │ • Feature Extraction         │    │
│  │ • Datasets   │   │ • GeoJSON    │   │ • Isolation Forest           │    │
│  │ • Runs       │   │ • Reports    │   │ • Z-Score Detection          │    │
│  │ • Anomalies  │   │              │   │ • Polygon Generation         │    │
│  │ • Reviews    │   │              │   │                               │    │
│  │ • Audit Logs │   │              │   │                               │    │
│  └──────────────┘   └──────────────┘   └──────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Level 3: Component Diagram (API Server)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API Server Components                             │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                          API Layer                                      │ │
│  │                                                                         │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │ │
│  │  │ Auth Router  │ │Dataset Router│ │  Run Router  │ │Anomaly Router│   │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │ │
│  │           │               │               │                │            │ │
│  │           └───────────────┴───────────────┴────────────────┘            │ │
│  │                                   │                                      │ │
│  │                            Dependencies                                  │ │
│  │                     (Auth, DB Session, Config)                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      Application Layer (Use Cases)                      │ │
│  │                                                                         │ │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐        │ │
│  │  │ CreateDataset    │ │ StartAnalysisRun │ │  SubmitReview    │        │ │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘        │ │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐        │ │
│  │  │ GetRunAnomalies  │ │  ExportReport    │ │   GetRunStatus   │        │ │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘        │ │
│  │                                                                         │ │
│  │  DTOs: DatasetResponse, RunResponse, AnomalyResponse, ReviewSubmit      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                          Domain Layer                                   │ │
│  │                                                                         │ │
│  │  Entities:                                                              │ │
│  │  ┌────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌───────────┐         │ │
│  │  │  User  │ │ Dataset │ │ ModelRun │ │ Anomaly │ │ ReviewLog │         │ │
│  │  └────────┘ └─────────┘ └──────────┘ └─────────┘ └───────────┘         │ │
│  │                                                                         │ │
│  │  Value Objects:                                                         │ │
│  │  ┌──────────────┐ ┌───────────────┐ ┌──────────────┐                   │ │
│  │  │ BoundingBox  │ │ FeatureVector │ │ AnomalyScore │                   │ │
│  │  └──────────────┘ └───────────────┘ └──────────────┘                   │ │
│  │                                                                         │ │
│  │  Enums: UserRole, RunStatus, ConfidenceLevel, ReviewDecision           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      Infrastructure Layer                               │ │
│  │                                                                         │ │
│  │  Repositories:                           ML Pipeline:                   │ │
│  │  ┌──────────────────────────────┐       ┌──────────────────────────┐   │ │
│  │  │ SQLAlchemyDatasetRepository  │       │ RasterProcessor          │   │ │
│  │  │ SQLAlchemyRunRepository      │       │ FeatureExtractor         │   │ │
│  │  │ SQLAlchemyAnomalyRepository  │       │ AnomalyDetector          │   │ │
│  │  │ SQLAlchemyReviewLogRepository│       │ AnomalyPolygonizer       │   │ │
│  │  └──────────────────────────────┘       │ HeatmapGenerator         │   │ │
│  │                                          └──────────────────────────┘   │ │
│  │  Database:                      File Store:                              │ │
│  │  ┌─────────────────┐           ┌─────────────────┐                      │ │
│  │  │ SQLAlchemy ORM  │           │ Local Filesystem│                      │ │
│  │  │ Alembic Migr.   │           │                 │                      │ │
│  │  └─────────────────┘           └─────────────────┘                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy 2.0 + Alembic
- **ML**: scikit-learn, scipy, numpy
- **Geospatial**: rasterio, shapely, geopandas, pyproj
- **Auth**: JWT with passlib/bcrypt

### Frontend
- **Framework**: React 18 + Vite + TypeScript
- **UI Library**: Material-UI (MUI) v5
- **Mapping**: MapLibre GL JS
- **State**: Zustand
- **HTTP**: Axios

### Infrastructure
- **Database**: PostgreSQL 15+
- **OS**: Linux/macOS (on-premises)
- **Optional**: Docker Compose for containerized deployment

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Security Boundaries                                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     Internal Network Only                            │    │
│  │                                                                      │    │
│  │  • No internet egress                                                │    │
│  │  • No external API calls                                             │    │
│  │  • No telemetry or analytics                                         │    │
│  │  • All secrets stored locally                                        │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  RBAC Roles:                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                          │
│  │   Admin     │  │Hydrographer │  │   Viewer    │                          │
│  │             │  │             │  │             │                          │
│  │ • Manage    │  │ • Upload    │  │ • View      │                          │
│  │   users     │  │   datasets  │  │   results   │                          │
│  │ • All       │  │ • Run       │  │ • Export    │                          │
│  │   actions   │  │   analysis  │  │   reports   │                          │
│  │             │  │ • Review    │  │             │                          │
│  │             │  │   anomalies │  │             │                          │
│  └─────────────┘  └─────────────┘  └─────────────┘                          │
│                                                                              │
│  Audit Trail:                                                                │
│  • Append-only review_logs table                                            │
│  • Append-only audit_logs table                                             │
│  • Captures: who, what, when, why                                           │
│  • Model version recorded with each decision                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

1. **Clean Architecture**: Strict separation of concerns enables testing and maintainability
2. **Explainability First**: Every anomaly includes detailed "why" information
3. **Human Authority**: System suggests but never auto-approves
4. **Audit Everything**: Complete decision history for compliance
5. **On-Premises**: Zero external dependencies for security
6. **Config-Driven**: All thresholds in YAML, no magic numbers
