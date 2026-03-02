"""
Compliance Alert System for RetailMind AI
Generates alerts for compliance violations and provides remediation recommendations
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


@dataclass
class ComplianceAlert:
    """Compliance alert data structure"""
    alert_id: str
    alert_type: str
    severity: AlertSeverity
    description: str
    remediation: str
    timestamp: datetime
    status: AlertStatus
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'alert_id': self.alert_id,
            'alert_type': self.alert_type,
            'severity': self.severity.value,
            'description': self.description,
            'remediation': self.remediation,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status.value,
            'metadata': self.metadata
        }


class RemediationEngine:
    """
    Remediation Recommendation Engine
    Provides context-aware remediation recommendations for compliance violations
    """
    
    def __init__(self):
        """Initialize remediation engine"""
        self.remediation_templates = self._load_remediation_templates()
    
    def _load_remediation_templates(self) -> Dict[str, Dict[str, str]]:
        """Load remediation templates for different alert types"""
        return {
            'document_validation_failure': {
                'immediate': 'Review and correct document data immediately',
                'short_term': 'Implement automated validation checks',
                'long_term': 'Enhance document processing pipeline with ML-based validation'
            },
            'low_extraction_accuracy': {
                'immediate': 'Manually review and verify extracted data',
                'short_term': 'Retrain document extraction models',
                'long_term': 'Upgrade to advanced OCR and NLP models'
            },
            'high_supplier_risk': {
                'immediate': 'Conduct detailed supplier audit within 48 hours',
                'short_term': 'Increase monitoring frequency and review contract terms',
                'long_term': 'Develop alternative supplier relationships'
            },
            'fraud_duplicate_transaction': {
                'immediate': 'Investigate transaction immediately and suspend if necessary',
                'short_term': 'Implement real-time duplicate detection',
                'long_term': 'Deploy advanced fraud detection ML models'
            },
            'fraud_high_velocity': {
                'immediate': 'Flag supplier account for immediate review',
                'short_term': 'Implement velocity-based transaction limits',
                'long_term': 'Deploy behavioral analytics for supplier monitoring'
            },
            'fraud_amount_anomaly': {
                'immediate': 'Verify transaction authenticity with supplier',
                'short_term': 'Implement amount-based approval workflows',
                'long_term': 'Deploy anomaly detection models for all transactions'
            },
            'missing_compliance_data': {
                'immediate': 'Request missing compliance documentation',
                'short_term': 'Implement mandatory compliance data collection',
                'long_term': 'Automate compliance data validation at onboarding'
            },
            'contract_risk_identified': {
                'immediate': 'Legal review of contract terms',
                'short_term': 'Negotiate contract amendments',
                'long_term': 'Standardize contract templates with risk mitigation'
            }
        }

    def get_remediation(
        self, 
        alert_type: str, 
        severity: AlertSeverity,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get remediation recommendation for an alert
        
        Args:
            alert_type: Type of compliance alert
            severity: Severity level of the alert
            context: Additional context for personalized recommendations
            
        Returns:
            Remediation recommendation string
        """
        # Get template for alert type
        template = self.remediation_templates.get(alert_type, {})
        
        if not template:
            # Default remediation for unknown alert types
            return self._get_default_remediation(severity)
        
        # Select remediation based on severity
        if severity == AlertSeverity.CRITICAL or severity == AlertSeverity.HIGH:
            remediation = template.get('immediate', '')
            # Add short-term action for high severity
            if template.get('short_term'):
                remediation += f". {template['short_term']}"
        elif severity == AlertSeverity.MEDIUM:
            remediation = template.get('short_term', template.get('immediate', ''))
        else:  # LOW
            remediation = template.get('long_term', template.get('short_term', ''))
        
        # Personalize with context if available
        if context:
            remediation = self._personalize_remediation(remediation, context)
        
        return remediation
    
    def _get_default_remediation(self, severity: AlertSeverity) -> str:
        """Get default remediation for unknown alert types"""
        if severity == AlertSeverity.CRITICAL:
            return "Immediate investigation required. Escalate to compliance officer."
        elif severity == AlertSeverity.HIGH:
            return "Review and address within 24 hours. Document findings."
        elif severity == AlertSeverity.MEDIUM:
            return "Schedule review within 1 week. Implement corrective measures."
        else:  # LOW
            return "Monitor situation. Address during next review cycle."
    
    def _personalize_remediation(self, remediation: str, context: Dict[str, Any]) -> str:
        """
        Personalize remediation with context-specific information
        
        Args:
            remediation: Base remediation text
            context: Context dictionary with additional information
            
        Returns:
            Personalized remediation text
        """
        # Add specific entity information if available
        if 'entity_id' in context:
            remediation += f" (Entity: {context['entity_id']})"
        
        if 'affected_count' in context:
            remediation += f" Affects {context['affected_count']} items."
        
        if 'deadline' in context:
            remediation += f" Deadline: {context['deadline']}"
        
        return remediation


class ComplianceAlertSystem:
    """
    Compliance Alert System
    Manages generation, tracking, and resolution of compliance alerts
    """
    
    def __init__(self):
        """Initialize compliance alert system"""
        self.remediation_engine = RemediationEngine()
        self.alerts: List[ComplianceAlert] = []
    
    def generate_alert(
        self,
        alert_type: str,
        severity: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ComplianceAlert:
        """
        Generate a compliance alert with remediation recommendation
        
        Args:
            alert_type: Type of compliance alert
            severity: Severity level (low, medium, high, critical)
            description: Description of the violation
            metadata: Additional metadata for the alert
            
        Returns:
            ComplianceAlert object
        """
        # Convert severity string to enum
        severity_enum = AlertSeverity(severity.lower())
        
        # Generate remediation recommendation
        remediation = self.remediation_engine.get_remediation(
            alert_type=alert_type,
            severity=severity_enum,
            context=metadata
        )
        
        # Create alert
        alert = ComplianceAlert(
            alert_id=f"alert-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            alert_type=alert_type,
            severity=severity_enum,
            description=description,
            remediation=remediation,
            timestamp=datetime.now(timezone.utc),
            status=AlertStatus.OPEN,
            metadata=metadata or {}
        )
        
        # Store alert
        self.alerts.append(alert)
        
        return alert
    
    def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[str] = None
    ) -> List[ComplianceAlert]:
        """
        Get alerts filtered by criteria
        
        Args:
            status: Filter by alert status
            severity: Filter by severity level
            alert_type: Filter by alert type
            
        Returns:
            List of matching alerts
        """
        filtered_alerts = self.alerts
        
        if status:
            filtered_alerts = [a for a in filtered_alerts if a.status == status]
        
        if severity:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity]
        
        if alert_type:
            filtered_alerts = [a for a in filtered_alerts if a.alert_type == alert_type]
        
        return filtered_alerts
    
    def update_alert_status(self, alert_id: str, new_status: AlertStatus) -> bool:
        """
        Update the status of an alert
        
        Args:
            alert_id: ID of the alert to update
            new_status: New status for the alert
            
        Returns:
            True if updated successfully, False otherwise
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.status = new_status
                return True
        return False
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of alerts
        
        Returns:
            Dictionary with alert statistics
        """
        total = len(self.alerts)
        
        by_severity = {
            'critical': len([a for a in self.alerts if a.severity == AlertSeverity.CRITICAL]),
            'high': len([a for a in self.alerts if a.severity == AlertSeverity.HIGH]),
            'medium': len([a for a in self.alerts if a.severity == AlertSeverity.MEDIUM]),
            'low': len([a for a in self.alerts if a.severity == AlertSeverity.LOW])
        }
        
        by_status = {
            'open': len([a for a in self.alerts if a.status == AlertStatus.OPEN]),
            'in_progress': len([a for a in self.alerts if a.status == AlertStatus.IN_PROGRESS]),
            'resolved': len([a for a in self.alerts if a.status == AlertStatus.RESOLVED]),
            'dismissed': len([a for a in self.alerts if a.status == AlertStatus.DISMISSED])
        }
        
        return {
            'total_alerts': total,
            'by_severity': by_severity,
            'by_status': by_status
        }
