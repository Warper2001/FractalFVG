# FractalFVG Deployment Runbook

## Overview

This runbook provides step-by-step procedures for deploying the FractalFVG MNQ FVG Algorithm to QuantConnect using the bulletproof deployment pipeline.

## Prerequisites

### Environment Setup
- Python 3.11+ installed
- QuantConnect API credentials configured
- Project structure validated
- All dependencies installed (`pip install -r requirements.txt`)

### Configuration Files
- `config/deployment_config.json` - Deployment configuration
- `deployment_package/Main.cs` - Algorithm source code
- `deployment_package/project.json` - QuantConnect project configuration

## Deployment Procedures

### 1. Standard Deployment

**Command:**
```bash
cd /root/FractalFVG
python3 deployment_package/bulletproof_deployment_pipeline.py
```

**Expected Output:**
```
✅ Deployment successful! ID: deploy_20231022_143022
📊 Duration: 45.23 seconds
📈 Performance Score: 98.50
```

**What happens:**
1. Pre-deployment validation (source code, unit tests)
2. Backup creation and rollback point setup
3. Build and compilation
4. Deployment to QuantConnect
5. Post-deployment testing
6. Health monitoring (5 minutes)
7. Automated rollback if critical issues detected

### 2. Emergency Rollback

**Manual Rollback:**
```python
from deployment_package.bulletproof_deployment_pipeline import RollbackManager

rollback = RollbackManager()
success = rollback.execute_rollback("rollback_deploy_20231022_143022_1666483422", "./quantconnect_mnq_fvg")
```

**Automatic Rollback Triggers:**
- Health score < 30%
- Critical health check failures
- Algorithm accessibility issues
- Configuration consistency problems

### 3. Monitoring and Alerting

**Real-time Monitoring:**
- Health checks every 30 seconds
- Performance metrics collection
- Alert threshold monitoring
- Automated alert generation

**Alert Thresholds:**
- Error rate > 5%
- Response time > 5 seconds
- Memory usage > 80%
- CPU usage > 85%

**Alert Locations:**
- Logs: `logs/alerts/alert_*.json`
- Deployment logs: `logs/deployments/deployment_*.log`

## Troubleshooting

### Common Issues

#### 1. Backup Creation Failed
**Symptoms:**
```
ERROR - Backup creation failed: Permission denied
```

**Solutions:**
- Check file permissions on backup directory
- Ensure sufficient disk space
- Verify source directory exists

#### 2. Source Validation Failed
**Symptoms:**
```
ERROR - Source validation failed: ['Main.cs not found']
```

**Solutions:**
- Verify Main.cs exists in `deployment_package/`
- Check C# syntax and namespace structure
- Validate project.json configuration

#### 3. Unit Tests Failed
**Symptoms:**
```
ERROR - Unit tests failed: ['TestConfluenceScorer failed']
```

**Solutions:**
- Run tests manually: `python3 -m pytest tests/`
- Check test dependencies
- Review test failure logs

#### 4. Deployment to QuantConnect Failed
**Symptoms:**
```
ERROR - Deployment failed: API authentication error
```

**Solutions:**
- Verify API credentials in `setup_api_credentials.py`
- Check QuantConnect service status
- Validate project ID and permissions

#### 5. Health Check Failures
**Symptoms:**
```
WARNING - Unhealthy deployment detected: ['High memory usage: 85.00%']
```

**Solutions:**
- Monitor system resources
- Check algorithm performance
- Consider scaling resources
- Review algorithm configuration

### Emergency Procedures

#### Critical Failure Response
1. **Stop Deployment:** Ctrl+C or kill process
2. **Assess Damage:** Check logs in `logs/deployments/`
3. **Rollback:** Use latest rollback point
4. **Investigate:** Review error logs and metrics
5. **Fix:** Address root cause
6. **Redeploy:** Run deployment pipeline again

#### Service Outage
1. **Check QuantConnect Status:** https://status.quantconnect.com/
2. **Verify Local Environment:** System resources, network connectivity
3. **Review Recent Changes:** Last deployment, configuration updates
4. **Contact Support:** If issue persists

## Maintenance

### Daily Checks
- Review deployment logs for errors
- Monitor system performance metrics
- Check alert notifications
- Verify backup integrity

### Weekly Tasks
- Test rollback procedures
- Update documentation
- Review and update alert thresholds
- Clean up old logs and backups

### Monthly Maintenance
- Security updates
- Dependency updates
- Performance optimization
- Disaster recovery testing

## Configuration

### Deployment Configuration (`config/deployment_config.json`)
```json
{
  "environment": "production",
  "project_id": "12345",
  "algorithm_name": "MNQ_FVG_ML_Algorithm",
  "source_path": "./deployment_package",
  "backup_path": "./backups",
  "max_retries": 3,
  "timeout_seconds": 300,
  "health_check_interval": 30,
  "monitoring_duration": 300
}
```

### Alert Threshold Customization
Modify in `deployment_package/bulletproof_deployment_pipeline.py`:
```python
self.alert_thresholds = {
    "error_rate": 0.05,      # 5%
    "response_time": 5.0,    # 5 seconds
    "memory_usage": 0.80,    # 80%
    "cpu_usage": 0.85        # 85%
}
```

## Security Considerations

### API Credentials
- Store securely using environment variables
- Rotate credentials regularly
- Use least-privilege access
- Monitor for unauthorized access

### Data Protection
- Encrypt sensitive configuration data
- Secure backup storage
- Audit trail for all deployments
- Regular security scans

## Performance Optimization

### Deployment Speed
- Optimize backup strategies
- Parallelize validation steps
- Cache compilation results
- Use incremental deployments

### Resource Usage
- Monitor memory consumption
- Optimize health check frequency
- Implement resource limits
- Use efficient logging

## Compliance and Audit

### Audit Trail
All deployments create comprehensive audit trails including:
- Deployment ID and timestamp
- Configuration changes
- Validation results
- Performance metrics
- Rollback history

### Reporting
Generate deployment reports:
```bash
python3 deployment_package/generate_deployment_report.py --deployment-id deploy_20231022_143022
```

## Contact Information

### Support Team
- DevOps: devops@fractalfvg.com
- Development: dev@fractalfvg.com
- Operations: ops@fractalfvg.com

### Escalation
1. **Level 1:** Automated monitoring and alerts
2. **Level 2:** On-call engineer (30 min response)
3. **Level 3:** Team lead (15 min response)
4. **Level 4:** Management (5 min response)

---

**Version:** 1.0.0  
**Last Updated:** 2025-10-22  
**Next Review:** 2025-11-22