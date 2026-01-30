# PoC Limitations & Next Steps

## Current Scope

This is a **Proof of Concept (PoC)** demonstrating the feasibility of AI-assisted multibeam bathymetry QC. It is **NOT** intended for production use without further development and validation.

## Known Limitations

### 1. Data Support

| Current | Limitation | Future Work |
|---------|------------|-------------|
| GeoTIFF rasters only | No BAG, XYZ, LAS support | Add format parsers |
| Single-band depth | No uncertainty bands | Multi-band support |
| EPSG:4326 assumed | Limited CRS handling | Full pyproj integration |
| < 500MB files | Memory loading | Chunked processing |
| No tiled processing | Full raster in memory | GDAL windowed reads |

### 2. Anomaly Detection

| Current | Limitation | Future Work |
|---------|------------|-------------|
| Isolation Forest + Z-score | Limited detection methods | Ensemble methods |
| Fixed feature set | May miss domain-specific patterns | Custom feature plugins |
| No temporal analysis | Can't detect time-based drift | Multi-survey comparison |
| Binary anomaly/normal | No graduated risk levels | Probabilistic outputs |
| No density-based for points | Point cloud underutilized | DBSCAN for point data |

### 3. Explainability

| Current | Limitation | Future Work |
|---------|------------|-------------|
| Feature-based explanation | Limited "why" detail | SHAP values |
| No visualization of features | Hard to understand reasons | Feature map overlays |
| Static thresholds in explanation | No context adaptation | Dynamic threshold display |

### 4. User Interface

| Current | Status | Notes |
|---------|--------|-------|
| MapLibre GL JS | ✅ Implemented | GPU-accelerated rendering |
| Density heatmap | ✅ Implemented | WebGL anomaly heatmap layer |
| Layer toggles | ✅ Implemented | Sidebar controls for polygons/heatmap |
| Light/Dark theme | ✅ Implemented | Full theme support |
| Desktop browser | ✅ Implemented | Optimized for desktop |
| Mobile responsive | 🔄 Planned | Responsive design needed |
| Offline basemaps | 🔄 Planned | For air-gapped environments |
| Multi-user collab | 🔄 Planned | Real-time collaboration |

### 5. Security

| Current | Limitation | Future Work |
|---------|------------|-------------|
| JWT only | No SSO/LDAP | SAML/OAuth integration |
| Basic RBAC | No fine-grained permissions | Attribute-based access |
| No password policy | Weak passwords allowed | Password requirements |
| No MFA | Single-factor auth | TOTP/hardware key support |
| No rate limiting | API vulnerable to abuse | Rate limiting middleware |

### 6. Operations

| Current | Limitation | Future Work |
|---------|------------|-------------|
| No monitoring | No system health visibility | Prometheus/Grafana |
| Local logs only | Log aggregation missing | ELK stack (internal) |
| No backup automation | Manual backup required | Scheduled backups |
| Single-node only | No horizontal scaling | Kubernetes deployment |
| No health checks | No liveness probes | k8s health endpoints |

### 7. Testing

| Current | Limitation | Future Work |
|---------|------------|-------------|
| Minimal unit tests | Low coverage | 80%+ coverage target |
| No integration tests | API endpoints untested | pytest + httpx |
| No UI tests | Frontend untested | Playwright e2e tests |
| No performance tests | Unknown scalability | Locust load testing |
| No security tests | Vulnerabilities unknown | SAST/DAST scans |

## Not In Scope (By Design)

These items are **intentionally excluded** from this PoC:

1. **Automatic correction of soundings** - Human authority is non-negotiable
2. **Official chart product generation** - Decision support only
3. **Cloud/SaaS deployment** - On-premises requirement
4. **External API integrations** - Air-gapped operation
5. **Mobile applications** - Web-first for PoC

## Acceptance Criteria for PoC

✅ **Completed**:
- [x] Upload GeoTIFF bathymetry file
- [x] Run anomaly detection pipeline
- [x] View anomalies on interactive map
- [x] See ranked list of anomalies by priority
- [x] View explanation for each anomaly
- [x] Accept/reject anomalies with comments
- [x] Export results as JSON/GeoJSON
- [x] Full audit trail of decisions
- [x] RBAC with Admin/Hydrographer/Viewer roles

⏳ **To Be Validated**:
- [ ] Analysis completes within 5 minutes on sample dataset
- [ ] Detection accuracy validated against known anomalies
- [ ] User acceptance by hydrography team

## Recommended Next Steps

### Phase 1: Validation (2-4 weeks)
1. Test with real survey data
2. Validate detection accuracy
3. Gather user feedback
4. Refine UI based on hydrographer input

### Phase 2: Hardening (4-6 weeks)
1. Add comprehensive test suite
2. Performance optimization
3. Security audit and fixes
4. Documentation improvements

### Phase 3: Extended Features ✅ COMPLETE
1. ✅ S-102 HDF5 export (S-102-Ready structure)
2. 🔄 Full S-102 Compliance / Validation (Next)
3. ✅ Heatmap visualization
4. ✅ Quality dashboard with anomaly breakdown
5. 🔄 Multi-survey comparison (Next)
6. 🔄 BAG and point cloud support (Next)

### Phase 4: Production Readiness (4-6 weeks)
1. Kubernetes deployment option
2. Monitoring and alerting
3. Backup automation
4. SSO integration

## Feedback & Issues

For PoC feedback, contact the development team with:
- Feature requests
- Bug reports
- Accuracy concerns
- Usability issues

All feedback will be tracked for prioritization in future phases.
