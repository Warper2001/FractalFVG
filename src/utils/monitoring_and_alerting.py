"""
Monitoring and Alerting for API Error Handling

Provides comprehensive monitoring, alerting, and health checks for API integrations
with support for multiple notification channels and dashboard integration.
"""

import time
import logging
import json
import asyncio
import smtplib
import threading
from typing import Dict, Any, Optional, Callable, Union, List, Type
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from email.mime.text import MIMEText as MimeText
from email.mime.multipart import MIMEMultipart as MimeMultipart

from .api_error_handler import APIError, ErrorCategory, ErrorSeverity, ErrorMetrics


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    """Available notification channels"""
    LOG = "log"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    DASHBOARD = "dashboard"


@dataclass
class Alert:
    """Alert information"""
    id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    service: Optional[str] = None
    error_category: Optional[ErrorCategory] = None
    error_severity: Optional[ErrorSeverity] = None
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


@dataclass
class HealthCheck:
    """Health check configuration"""
    name: str
    check_func: Callable[[], bool]
    interval: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    timeout: timedelta = field(default_factory=lambda: timedelta(minutes=1))
    failure_threshold: int = 3
    last_check: Optional[datetime] = None
    last_result: Optional[bool] = None
    consecutive_failures: int = 0
    status: str = "unknown"  # healthy, degraded, unhealthy, unknown


@dataclass
class NotificationConfig:
    """Configuration for notification channels"""
    channel: NotificationChannel
    enabled: bool = True
    min_level: AlertLevel = AlertLevel.WARNING
    rate_limit: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    config: Dict[str, Any] = field(default_factory=dict)
    last_notification: Optional[datetime] = None


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self, 
                 service_name: str = "api_service",
                 alert_log_file: Optional[str] = None):
        """
        Initialize alert manager
        
        Args:
            service_name: Name of the service being monitored
            alert_log_file: Optional file for alert logging
        """
        self.service_name = service_name
        self.alerts: List[Alert] = []
        self.notification_configs: Dict[NotificationChannel, NotificationConfig] = {}
        self.health_checks: Dict[str, HealthCheck] = {}
        self.alert_rules: List[Callable[[APIError], Optional[Alert]]] = []
        
        self.logger = logging.getLogger(f"{__name__}.{service_name}")
        
        # Setup alert logging
        if alert_log_file:
            handler = logging.FileHandler(alert_log_file)
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(handler)
        
        # Start health check monitoring
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        self._start_health_monitoring()
    
    def add_notification_channel(self, 
                                channel: NotificationChannel,
                                config: Dict[str, Any],
                                min_level: AlertLevel = AlertLevel.WARNING,
                                rate_limit: timedelta = timedelta(minutes=5)) -> None:
        """
        Add notification channel
        
        Args:
            channel: Notification channel type
            config: Channel-specific configuration
            min_level: Minimum alert level for this channel
            rate_limit: Rate limit for notifications
        """
        notification_config = NotificationConfig(
            channel=channel,
            config=config,
            min_level=min_level,
            rate_limit=rate_limit
        )
        
        self.notification_configs[channel] = notification_config
        self.logger.info(f"Added notification channel: {channel.value}")
    
    def add_health_check(self, 
                        name: str,
                        check_func: Callable[[], bool],
                        interval: timedelta = timedelta(minutes=5),
                        failure_threshold: int = 3) -> None:
        """
        Add health check
        
        Args:
            name: Health check name
            check_func: Function that returns True if healthy
            interval: Check interval
            failure_threshold: Number of consecutive failures before alert
        """
        health_check = HealthCheck(
            name=name,
            check_func=check_func,
            interval=interval,
            failure_threshold=failure_threshold
        )
        
        self.health_checks[name] = health_check
        self.logger.info(f"Added health check: {name}")
    
    def add_alert_rule(self, rule_func: Callable[[APIError], Optional[Alert]]) -> None:
        """
        Add alert rule for generating alerts from errors
        
        Args:
            rule_func: Function that takes APIError and returns Alert or None
        """
        self.alert_rules.append(rule_func)
    
    def process_error(self, error: APIError, service: Optional[str] = None) -> None:
        """
        Process error and generate alerts based on rules
        
        Args:
            error: API error that occurred
            service: Service name where error occurred
        """
        # Apply alert rules
        for rule_func in self.alert_rules:
            try:
                alert = rule_func(error)
                if alert:
                    alert.service = service or self.service_name
                    self.send_alert(alert)
            except Exception as e:
                self.logger.error(f"Error in alert rule: {e}")
        
        # Default alert rules
        self._default_alert_rules(error, service)
    
    def _default_alert_rules(self, error: APIError, service: Optional[str] = None) -> None:
        """Default alert rules for common error patterns"""
        # Critical alerts for authentication errors
        if error.category == ErrorCategory.AUTHENTICATION:
            alert = Alert(
                id=f"auth_error_{int(time.time())}",
                level=AlertLevel.CRITICAL,
                title="Authentication Failure",
                message=f"Authentication failed for {service or self.service_name}: {error.message}",
                service=service or self.service_name,
                error_category=error.category,
                error_severity=error.severity,
                context={'status_code': error.status_code}
            )
            self.send_alert(alert)
        
        # High severity alerts for server errors
        elif error.category == ErrorCategory.SERVER_ERROR:
            alert = Alert(
                id=f"server_error_{int(time.time())}",
                level=AlertLevel.ERROR,
                title="Server Error",
                message=f"Server error in {service or self.service_name}: {error.message}",
                service=service or self.service_name,
                error_category=error.category,
                error_severity=error.severity,
                context={'status_code': error.status_code}
            )
            self.send_alert(alert)
        
        # Warning for rate limiting
        elif error.category == ErrorCategory.RATE_LIMIT:
            alert = Alert(
                id=f"rate_limit_{int(time.time())}",
                level=AlertLevel.WARNING,
                title="Rate Limit Exceeded",
                message=f"Rate limit exceeded for {service or self.service_name}: {error.message}",
                service=service or self.service_name,
                error_category=error.category,
                error_severity=error.severity
            )
            self.send_alert(alert)
    
    def send_alert(self, alert: Alert) -> None:
        """
        Send alert through configured channels
        
        Args:
            alert: Alert to send
        """
        self.alerts.append(alert)
        
        # Log alert
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }.get(alert.level, logging.INFO)
        
        self.logger.log(log_level, f"ALERT: {alert.title} - {alert.message}")
        
        # Send through notification channels
        for channel, config in self.notification_configs.items():
            if not config.enabled:
                continue
            
            if self._should_send_notification(alert, config):
                try:
                    self._send_notification(alert, channel, config)
                    config.last_notification = datetime.utcnow()
                except Exception as e:
                    self.logger.error(f"Failed to send {channel.value} notification: {e}")
    
    def _should_send_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Check if notification should be sent based on level and rate limiting"""
        # Check minimum level
        level_order = [AlertLevel.INFO, AlertLevel.WARNING, AlertLevel.ERROR, AlertLevel.CRITICAL]
        alert_level_index = level_order.index(alert.level)
        min_level_index = level_order.index(config.min_level)
        
        if alert_level_index < min_level_index:
            return False
        
        # Check rate limiting
        if config.last_notification:
            time_since_last = datetime.utcnow() - config.last_notification
            if time_since_last < config.rate_limit:
                return False
        
        return True
    
    def _send_notification(self, alert: Alert, channel: NotificationChannel, config: NotificationConfig) -> None:
        """Send notification through specific channel"""
        if channel == NotificationChannel.LOG:
            # Already logged in send_alert
            pass
        
        elif channel == NotificationChannel.EMAIL:
            self._send_email_notification(alert, config.config)
        
        elif channel == NotificationChannel.SLACK:
            self._send_slack_notification(alert, config.config)
        
        elif channel == NotificationChannel.WEBHOOK:
            self._send_webhook_notification(alert, config.config)
        
        elif channel == NotificationChannel.DASHBOARD:
            self._send_dashboard_notification(alert, config.config)
    
    def _send_email_notification(self, alert: Alert, config: Dict[str, Any]) -> None:
        """Send email notification"""
        try:
            smtp_server = config.get('smtp_server')
            smtp_port = config.get('smtp_port', 587)
            username = config.get('username')
            password = config.get('password')
            from_email = config.get('from_email')
            to_emails = config.get('to_emails', [])
            
            if not all([smtp_server, username, password, from_email, to_emails]):
                self.logger.warning("Incomplete email configuration")
                return
            
            msg = MimeMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = f"[{alert.level.value.upper()}] {alert.title}"
            
            body = f"""
Alert Level: {alert.level.value.upper()}
Service: {alert.service}
Time: {alert.timestamp.isoformat()}
Title: {alert.title}
Message: {alert.message}

Context:
{json.dumps(alert.context, indent=2)}
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Email notification sent for alert: {alert.id}")
        
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
    
    def _send_slack_notification(self, alert: Alert, config: Dict[str, Any]) -> None:
        """Send Slack notification"""
        try:
            webhook_url = config.get('webhook_url')
            channel = config.get('channel', '#alerts')
            
            if not webhook_url:
                self.logger.warning("Slack webhook URL not configured")
                return
            
            color = {
                AlertLevel.INFO: "good",
                AlertLevel.WARNING: "warning",
                AlertLevel.ERROR: "danger",
                AlertLevel.CRITICAL: "danger"
            }.get(alert.level, "warning")
            
            payload = {
                "channel": channel,
                "username": "API Alert Bot",
                "icon_emoji": ":warning:",
                "attachments": [{
                    "color": color,
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {"title": "Service", "value": alert.service, "short": True},
                        {"title": "Level", "value": alert.level.value.upper(), "short": True},
                        {"title": "Time", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"), "short": True}
                    ],
                    "footer": "API Monitoring",
                    "ts": int(alert.timestamp.timestamp())
                }]
            }
            
            import requests
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            self.logger.info(f"Slack notification sent for alert: {alert.id}")
        
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")
    
    def _send_webhook_notification(self, alert: Alert, config: Dict[str, Any]) -> None:
        """Send webhook notification"""
        try:
            webhook_url = config.get('url')
            headers = config.get('headers', {})
            
            if not webhook_url:
                self.logger.warning("Webhook URL not configured")
                return
            
            payload = {
                "alert_id": alert.id,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "service": alert.service,
                "timestamp": alert.timestamp.isoformat(),
                "context": alert.context
            }
            
            import requests
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            self.logger.info(f"Webhook notification sent for alert: {alert.id}")
        
        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")
    
    def _send_dashboard_notification(self, alert: Alert, config: Dict[str, Any]) -> None:
        """Send notification to monitoring dashboard"""
        # This would integrate with monitoring dashboards like Grafana, DataDog, etc.
        dashboard_url = config.get('dashboard_url')
        
        if dashboard_url:
            self.logger.info(f"Dashboard notification for alert {alert.id}: {dashboard_url}")
        else:
            self.logger.info(f"Dashboard notification for alert {alert.id}")
    
    def _start_health_monitoring(self) -> None:
        """Start background health monitoring"""
        def monitor():
            while not self._stop_monitoring.is_set():
                try:
                    self._run_health_checks()
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    self.logger.error(f"Health monitoring error: {e}")
        
        self._monitoring_thread = threading.Thread(target=monitor, daemon=True)
        self._monitoring_thread.start()
    
    def _run_health_checks(self) -> None:
        """Run all health checks"""
        for name, health_check in self.health_checks.items():
            try:
                # Check if it's time to run this health check
                if health_check.last_check:
                    time_since_last = datetime.utcnow() - health_check.last_check
                    if time_since_last < health_check.interval:
                        continue
                
                # Run health check with timeout
                result = self._run_with_timeout(health_check.check_func, health_check.timeout)
                
                health_check.last_check = datetime.utcnow()
                health_check.last_result = result
                
                if result:
                    health_check.consecutive_failures = 0
                    health_check.status = "healthy"
                else:
                    health_check.consecutive_failures += 1
                    
                    if health_check.consecutive_failures >= health_check.failure_threshold:
                        health_check.status = "unhealthy"
                        
                        # Send alert
                        alert = Alert(
                            id=f"health_check_{name}_{int(time.time())}",
                            level=AlertLevel.ERROR,
                            title=f"Health Check Failed: {name}",
                            message=f"Health check '{name}' has failed {health_check.consecutive_failures} times consecutively",
                            service=self.service_name,
                            context={
                                'health_check': name,
                                'consecutive_failures': health_check.consecutive_failures,
                                'failure_threshold': health_check.failure_threshold
                            }
                        )
                        self.send_alert(alert)
                    else:
                        health_check.status = "degraded"
            
            except Exception as e:
                health_check.consecutive_failures += 1
                health_check.last_check = datetime.utcnow()
                health_check.last_result = False
                
                self.logger.error(f"Health check '{name}' error: {e}")
    
    def _run_with_timeout(self, func: Callable, timeout: timedelta) -> bool:
        """Run function with timeout"""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Health check timeout")
        
        # Set timeout signal
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout.total_seconds()))
        
        try:
            result = func()
            signal.alarm(0)  # Cancel timeout
            return result
        except TimeoutError:
            return False
        finally:
            signal.alarm(0)  # Ensure timeout is cancelled
    
    def get_alerts(self, 
                  level: Optional[AlertLevel] = None,
                  service: Optional[str] = None,
                  resolved: Optional[bool] = None,
                  limit: int = 100) -> List[Alert]:
        """
        Get alerts with optional filtering
        
        Args:
            level: Filter by alert level
            service: Filter by service name
            resolved: Filter by resolved status
            limit: Maximum number of alerts to return
            
        Returns:
            List of alerts
        """
        filtered_alerts = self.alerts
        
        if level:
            filtered_alerts = [a for a in filtered_alerts if a.level == level]
        
        if service:
            filtered_alerts = [a for a in filtered_alerts if a.service == service]
        
        if resolved is not None:
            filtered_alerts = [a for a in filtered_alerts if a.resolved == resolved]
        
        # Sort by timestamp (newest first) and limit
        filtered_alerts.sort(key=lambda a: a.timestamp, reverse=True)
        return filtered_alerts[:limit]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """
        Acknowledge an alert
        
        Args:
            alert_id: Alert ID to acknowledge
            acknowledged_by: User who acknowledged the alert
            
        Returns:
            True if alert was found and acknowledged
        """
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.utcnow()
                alert.acknowledged_by = acknowledged_by
                
                self.logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                return True
        
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert
        
        Args:
            alert_id: Alert ID to resolve
            
        Returns:
            True if alert was found and resolved
        """
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                
                self.logger.info(f"Alert {alert_id} resolved")
                return True
        
        return False
    
    def get_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all services"""
        status = {}
        
        for name, health_check in self.health_checks.items():
            status[name] = {
                'status': health_check.status,
                'last_check': health_check.last_check.isoformat() if health_check.last_check else None,
                'last_result': health_check.last_result,
                'consecutive_failures': health_check.consecutive_failures,
                'failure_threshold': health_check.failure_threshold
            }
        
        return status
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of monitoring metrics"""
        total_alerts = len(self.alerts)
        active_alerts = len([a for a in self.alerts if not a.resolved])
        
        alerts_by_level = {}
        for level in AlertLevel:
            alerts_by_level[level.value] = len([a for a in self.alerts if a.level == level])
        
        recent_alerts = len([a for a in self.alerts 
                           if a.timestamp > datetime.utcnow() - timedelta(hours=24)])
        
        return {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'alerts_by_level': alerts_by_level,
            'recent_alerts_24h': recent_alerts,
            'health_checks': len(self.health_checks),
            'notification_channels': len([c for c in self.notification_configs.values() if c.enabled])
        }
    
    def cleanup_old_alerts(self, days: int = 30) -> int:
        """
        Clean up old resolved alerts
        
        Args:
            days: Number of days to keep alerts
            
        Returns:
            Number of alerts cleaned up
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        old_alerts = [a for a in self.alerts 
                     if a.resolved and a.resolved_at and a.resolved_at < cutoff_date]
        
        for alert in old_alerts:
            self.alerts.remove(alert)
        
        self.logger.info(f"Cleaned up {len(old_alerts)} old alerts")
        return len(old_alerts)
    
    def stop(self) -> None:
        """Stop monitoring"""
        if self._monitoring_thread:
            self._stop_monitoring.set()
            self._monitoring_thread.join(timeout=5)


# Decorator for monitoring function calls
def monitor_calls(service_name: str, alert_manager: Optional[AlertManager] = None):
    """
    Decorator for monitoring function calls and generating alerts on errors
    
    Args:
        service_name: Name of the service being monitored
        alert_manager: Alert manager instance (optional)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful call
                execution_time = time.time() - start_time
                logger = logging.getLogger(f"{__name__}.{service_name}")
                logger.debug(f"Function {func.__name__} completed in {execution_time:.2f}s")
                
                return result
            
            except Exception as e:
                # Create API error from exception
                from .api_error_handler import ErrorClassifier
                api_error = ErrorClassifier.classify_error(exception=e)
                
                # Send to alert manager
                if alert_manager:
                    alert_manager.process_error(api_error, service_name)
                else:
                    # Fallback logging
                    logger = logging.getLogger(f"{__name__}.{service_name}")
                    logger.error(f"Function {func.__name__} failed: {api_error.message}")
                
                raise e
        
        return wrapper
    return decorator


# Example usage
def example_monitoring_setup():
    """Example of setting up monitoring and alerting"""
    
    # Initialize alert manager
    alert_manager = AlertManager(
        service_name="quantconnect_api",
        alert_log_file="/root/FractalFVG/logs/alerts.log"
    )
    
    # Add email notifications
    alert_manager.add_notification_channel(
        NotificationChannel.EMAIL,
        config={
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': 'alerts@company.com',
            'password': 'app_password',
            'from_email': 'alerts@company.com',
            'to_emails': ['admin@company.com', 'dev@company.com']
        },
        min_level=AlertLevel.ERROR
    )
    
    # Add Slack notifications
    alert_manager.add_notification_channel(
        NotificationChannel.SLACK,
        config={
            'webhook_url': 'https://hooks.slack.com/services/...',
            'channel': '#api-alerts'
        },
        min_level=AlertLevel.WARNING
    )
    
    # Add health checks
    def check_quantconnect_api():
        """Check if QuantConnect API is accessible"""
        try:
            import requests
            response = requests.get("https://www.quantconnect.com/api/v2/projects", timeout=10)
            return response.status_code == 200
        except:
            return False
    
    alert_manager.add_health_check(
        name="quantconnect_api",
        check_func=check_quantconnect_api,
        interval=timedelta(minutes=5),
        failure_threshold=3
    )
    
    # Add custom alert rule
    def high_error_rate_rule(error: APIError) -> Optional[Alert]:
        """Generate alert for high error rates"""
        # This would check error rates and generate alerts
        return None
    
    alert_manager.add_alert_rule(high_error_rate_rule)
    
    # Example monitored function
    @monitor_calls("quantconnect_api", alert_manager)
    def create_project(name: str):
        """Monitored function for creating projects"""
        # This would normally make an API call
        if "fail" in name.lower():
            raise Exception("Simulated failure")
        return {"project_id": 123, "name": name}
    
    # Test the monitoring
    try:
        result = create_project("Test Project")
        print(f"Success: {result}")
    except Exception as e:
        print(f"Failed: {e}")
    
    try:
        result = create_project("Fail Project")
        print(f"Success: {result}")
    except Exception as e:
        print(f"Failed: {e}")
    
    # Get metrics
    metrics = alert_manager.get_metrics_summary()
    print(f"Metrics: {metrics}")
    
    # Get health status
    health = alert_manager.get_health_status()
    print(f"Health: {health}")
    
    # Cleanup
    alert_manager.stop()


if __name__ == "__main__":
    example_monitoring_setup()