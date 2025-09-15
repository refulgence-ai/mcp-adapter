# Data Persistence in Refulgence Admin System

## Overview

The Refulgence Admin System implements comprehensive file-based persistence for all critical governance data, ensuring continuity across container restarts, deployments, and system maintenance.

## Architecture

### Data Storage Strategy

**Docker Volume Persistence**: All data is stored in a dedicated Docker volume (`gateway-data`) mounted at `/app/data` inside the gateway container.

```yaml
# docker-compose.yml configuration
volumes:
  - ./gateway:/app
  - gateway-data:/app/data

volumes:
  gateway-data:
    driver: local
```

### Persistent Data Components

#### 1. User Data Store (`UserDataStore`)
**File**: `gateway/user_data_store.py`
**Storage**: `/app/data/users.json` and `/app/data/activity_patterns.json`

**Data Persisted**:
- User profiles and roles
- Permission mappings
- Activity patterns and analytics
- User preferences and settings
- Demo/production mode configurations

**Implementation**:
```python
# Automatic persistence on data modifications
async def create_user(self, user_data: Dict[str, Any]) -> str:
    # ... user creation logic ...
    await asyncio.get_event_loop().run_in_executor(None, self._save_persistent_data)
    return user_id
```

#### 2. Activity Tracker (`ActivityTracker`)
**File**: `gateway/activity_tracker.py`
**Storage**: `/app/data/activity_events.json`

**Data Persisted**:
- Complete audit trail of all governance events
- Security incidents and violations
- Agent connection/disconnection events
- Query executions and policy decisions
- Approval workflows and voting records

**Implementation**:
```python
# Periodic saving (every 10 events or on critical events)
if (len(self.events) % 10 == 0 or
    event.severity in [ActivitySeverity.CRITICAL]):
    await asyncio.get_event_loop().run_in_executor(None, self._save_persistent_events)
```

#### 3. Governance Policies (Existing)
**File**: `gateway/policies.json`
**Storage**: File-based configuration (already persistent)

**Data Persisted**:
- Policy rules and configurations
- Approval matrices
- Role-based access controls
- Security settings

## Persistence Behavior

### Demo Mode vs Production Mode

**Environment Variable**: `REFULGENCE_DEMO_MODE`

**Demo Mode (`REFULGENCE_DEMO_MODE=true`)**:
- Starts with pre-populated demo data
- All changes are persisted normally
- Demo data generation creates realistic scenarios
- Useful for presentations and testing

**Production Mode (`REFULGENCE_DEMO_MODE=false`)**:
- Starts with empty data structures
- All user-created data is persisted
- No automatic demo data generation
- Enterprise-ready configuration

### Data Loading Sequence

1. **Container Startup**:
   - Data directory (`/app/data`) is created if not exists
   - Existing JSON files are loaded automatically
   - Missing files result in empty data structures (no errors)

2. **Demo Mode Initialization**:
   - Demo data is generated only if no existing data is found
   - If persistent data exists, it takes precedence over demo data

3. **Event Loop Integration**:
   - User simulation starts after FastAPI application is ready
   - Background tasks begin activity monitoring

### File Format and Structure

#### User Data (`users.json`)
```json
{
  "users": {
    "user_id": {
      "id": "user_id",
      "name": "User Name",
      "role": "admin|user|agent|guest",
      "permissions": ["list"],
      "created_at": "ISO timestamp",
      "last_active": "ISO timestamp"
    }
  },
  "settings": {
    "demo_mode": true,
    "last_updated": "ISO timestamp"
  }
}
```

#### Activity Events (`activity_events.json`)
```json
[
  {
    "id": "event_1234567890",
    "timestamp": "ISO timestamp",
    "type": "query_executed",
    "severity": "info",
    "message": "Event description",
    "details": {},
    "subject_id": "user_id",
    "tool_name": "tool_name"
  }
]
```

## Performance Considerations

### Write Strategy
- **Batched Writes**: Events are saved every 10 occurrences to minimize I/O
- **Critical Event Priority**: Security events trigger immediate saves
- **Async Execution**: File operations run in thread pool to avoid blocking

### Memory Management
- **Bounded Collections**: Activity events limited to 1000 most recent
- **Lazy Loading**: Data loaded only when components are initialized
- **Memory Efficiency**: Large collections use deque for O(1) operations

### Error Handling
- **Graceful Degradation**: Missing files don't prevent startup
- **Error Logging**: Persistence failures are logged but don't crash services
- **Data Validation**: JSON structure validation on load

## Backup and Recovery

### Manual Backup
```bash
# Create backup of persistent data
docker cp mcp-adapter-gateway:/app/data ./backup-$(date +%Y%m%d)

# Restore from backup
docker cp ./backup-20240915 mcp-adapter-gateway:/app/data
docker-compose restart gateway
```

### Automated Backup (Recommended)
```bash
# Add to crontab for daily backups
0 2 * * * docker cp mcp-adapter-gateway:/app/data /backups/refulgence-$(date +\%Y\%m\%d)
```

## Testing Persistence

### Manual Testing
```bash
# 1. Start system and generate some data
docker-compose up -d
curl http://localhost:8080/admin  # Access UI, create some data

# 2. Restart container
docker-compose restart gateway

# 3. Verify data persistence
curl http://localhost:8080/api/admin/stats  # Check if data survived restart
```

### Automated Testing
```bash
# Run persistence tests
cd tests && uv run pytest test_persistence.py -v
```

## Monitoring and Diagnostics

### Data Volume Status
```bash
# Check volume size and usage
docker system df -v | grep gateway-data

# Inspect volume contents
docker exec mcp-adapter-gateway ls -la /app/data/
```

### Persistence Logs
```bash
# Monitor persistence operations
docker-compose logs gateway | grep -E "(Loaded|Saved|persistent)"
```

### Health Checks
- **Startup Validation**: Data loading success logged on startup
- **Write Confirmation**: Successful saves logged at DEBUG level
- **Error Alerts**: Persistence failures logged at ERROR level

## Security Considerations

### Data Protection
- **File Permissions**: Data files created with secure permissions
- **Access Control**: Only gateway container has access to data volume
- **Network Isolation**: Data volume not exposed to network

### Sensitive Data
- **No Credentials**: User credentials not stored (OAuth/SSO integration)
- **Audit Trail**: All data access events are logged
- **Encryption**: Consider file-level encryption for production deployments

## Migration and Upgrades

### Schema Evolution
- **Backward Compatibility**: New fields added with defaults
- **Version Detection**: Data format versions tracked in metadata
- **Migration Scripts**: Automatic schema upgrades when needed

### Data Import/Export
```python
# Export current data
curl http://localhost:8080/api/admin/export > backup.json

# Import data (future feature)
curl -X POST -d @backup.json http://localhost:8080/api/admin/import
```

## Development Guidelines

### Adding New Persistent Data

1. **Update Data Store**:
   ```python
   # Add new data structure
   self.new_data = {}

   # Update save method
   def _save_persistent_data(self):
       data = {
           "existing_data": self.existing_data,
           "new_data": self.new_data,  # Add here
           "metadata": self._get_metadata()
       }
   ```

2. **Update Load Method**:
   ```python
   def _load_persistent_data(self):
       # ... existing loading logic ...
       self.new_data = data.get("new_data", {})
   ```

3. **Call Persistence**:
   ```python
   async def modify_new_data(self, item):
       # ... modification logic ...
       await asyncio.get_event_loop().run_in_executor(None, self._save_persistent_data)
   ```

### Best Practices
- **Atomic Operations**: Group related changes and save together
- **Error Handling**: Always catch and log persistence errors
- **Performance**: Batch writes when possible
- **Testing**: Add persistence tests for new data structures

## Troubleshooting

### Common Issues

**Data Not Persisting**:
- Check Docker volume mount configuration
- Verify file permissions in container
- Check logs for persistence errors

**Performance Issues**:
- Monitor save frequency (should not exceed once per second)
- Check file sizes (activity events grow over time)
- Consider increasing deque maxlen for high-volume systems

**Container Startup Failures**:
- Check for corrupted JSON files
- Verify data directory permissions
- Look for import/module loading errors

### Recovery Procedures

**Corrupted Data Files**:
```bash
# Backup corrupted file
docker exec mcp-adapter-gateway cp /app/data/users.json /app/data/users.json.corrupt

# Remove corrupted file (system will recreate)
docker exec mcp-adapter-gateway rm /app/data/users.json

# Restart container
docker-compose restart gateway
```

**Lost Data Volume**:
```bash
# Recreate volume and restart
docker-compose down
docker volume rm mcp-adapter_gateway-data
docker-compose up -d
```

## Future Enhancements

### Database Integration
- PostgreSQL for enterprise deployments
- Redis for high-performance caching
- Elasticsearch for advanced analytics

### Replication
- Multi-node data replication
- Cross-region backup strategies
- High availability configurations

### Encryption
- File-level encryption at rest
- Key management integration
- Compliance requirements (GDPR, HIPAA)