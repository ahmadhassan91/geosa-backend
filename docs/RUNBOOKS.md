# Operational Runbooks

## Quick Start

### One-Time Setup

```bash
# 1. Clone repository
cd /path/to/hydroq-qc-assistant

# 2. Create PostgreSQL database
createdb hydroq_qc

# 3. Setup Python environment
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Copy and configure environment
cp ../../.env.example .env
# Edit .env with your settings, especially:
# - DATABASE_URL
# - JWT_SECRET_KEY (generate with: openssl rand -hex 32)

# 5. Run database migrations
alembic upgrade head

# 6. Setup frontend
cd ../web
npm install

# 7. Create admin user (via API after starting)
```

### Starting the System

**Terminal 1 - API Server**:
```bash
cd apps/api
source venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Web Frontend**:
```bash
cd apps/web
npm run dev
```

**Access**:
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

---

## Common Operations

### Creating the First Admin User

After starting the API, register via the API:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@local",
    "password": "SecurePassword123!",
    "role": "admin"
  }'
```

### Uploading a Dataset

```bash
# Login first
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "SecurePassword123!"}' \
  | jq -r '.access_token')

# Upload dataset
curl -X POST http://localhost:8000/api/v1/datasets/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "name=Survey Block A" \
  -F "description=Test survey data" \
  -F "file=@/path/to/bathymetry.tif"
```

### Starting an Analysis Run

```bash
# Get dataset ID
DATASET_ID=$(curl -s http://localhost:8000/api/v1/datasets/ \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.items[0].id')

# Start run
curl -X POST http://localhost:8000/api/v1/runs/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"dataset_id\": \"$DATASET_ID\"}"
```

### Generating Sample Data

```bash
cd apps/api
source venv/bin/activate
python ../../scripts/generate_sample_data.py \
  --output ../../data/samples/sample_bathymetry.tif \
  --width 500 \
  --height 500 \
  --spikes 10 \
  --holes 10 \
  --seams 3
```

---

## Database Operations

### Running Migrations

```bash
cd apps/api
source venv/bin/activate

# Upgrade to latest
alembic upgrade head

# Downgrade one revision
alembic downgrade -1

# Generate new migration
alembic revision --autogenerate -m "description"
```

### Database Backup

```bash
# Backup
pg_dump -U postgres hydroq_qc > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
psql -U postgres -d hydroq_qc < backup_20240120_120000.sql
```

### Checking Database Status

```bash
psql -U postgres -d hydroq_qc

# Count records
SELECT 'datasets' as table_name, COUNT(*) FROM datasets
UNION ALL
SELECT 'model_runs', COUNT(*) FROM model_runs
UNION ALL
SELECT 'anomalies', COUNT(*) FROM anomalies
UNION ALL
SELECT 'review_logs', COUNT(*) FROM review_logs;

# Check recent activity
SELECT action, resource_type, username, created_at 
FROM audit_logs 
ORDER BY created_at DESC 
LIMIT 20;
```

---

## Troubleshooting

### API Won't Start

**Issue**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
```bash
# Ensure you're in the api directory
cd apps/api
# Ensure virtual environment is activated
source venv/bin/activate
# Run from this directory
uvicorn src.main:app --reload
```

### Database Connection Failed

**Issue**: `psycopg2.OperationalError: could not connect to server`

**Solution**:
1. Check PostgreSQL is running: `pg_isready`
2. Verify database exists: `psql -l | grep hydroq_qc`
3. Check DATABASE_URL in `.env`
4. Ensure PostgreSQL accepts local connections

### Frontend Can't Connect to API

**Issue**: CORS errors or network errors

**Solution**:
1. Verify API is running on port 8000
2. Check Vite proxy config in `vite.config.ts`
3. Ensure API CORS allows frontend origin
4. Check browser console for specific errors

### Analysis Run Stuck in "Processing"

**Issue**: Run status never changes to completed

**Solution**:
1. Check API logs for errors
2. Verify rasterio can read the file: `rio info /path/to/file.tif`
3. Check available memory
4. Review background task output

### Out of Memory During Processing

**Issue**: Large raster causes memory errors

**Solution**:
1. Reduce raster size before upload
2. Increase system memory
3. Modify chunk_size in config.yaml (future feature)

---

## Monitoring

### Log Locations

| Component | Log Location |
|-----------|--------------|
| API | stdout (structured JSON) |
| Web | Browser console |
| PostgreSQL | `/var/log/postgresql/` |

### Health Check

```bash
# API health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected",
  "timestamp": "2024-01-20T12:00:00.000000"
}
```

### Quick Stats

```bash
# Get metrics (if implemented)
curl http://localhost:8000/metrics

# Or query database directly
psql -U postgres -d hydroq_qc -c "
  SELECT 
    (SELECT COUNT(*) FROM datasets) as datasets,
    (SELECT COUNT(*) FROM model_runs) as runs,
    (SELECT COUNT(*) FROM anomalies) as anomalies,
    (SELECT COUNT(*) FROM anomalies WHERE review_decision = 'pending') as pending_reviews
"
```

---

## Maintenance

### Weekly Tasks

- [ ] Check disk space for data directories
- [ ] Review error logs
- [ ] Verify backup integrity

### Monthly Tasks

- [ ] Update Python dependencies (security patches)
- [ ] Update npm dependencies
- [ ] Review audit logs for anomalies
- [ ] Clean up old analysis outputs if needed

### Data Cleanup

```bash
# Remove old output files (older than 30 days)
find data/outputs -type f -mtime +30 -delete

# Clean uploaded files for deleted datasets
# (Implement as needed based on data retention policy)
```
