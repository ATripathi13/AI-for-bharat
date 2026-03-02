"""
Unit tests for Risk & Compliance Agent
Tests specific functionality: document extraction, risk scoring, fraud detection
"""
import pytest
from datetime import datetime, timezone, timedelta

from src.agents.risk_compliance_agent import (
    RiskComplianceAgent,
    DocumentData,
    TransactionData,
    SupplierData,
    RiskComplianceInput
)
from src.services.compliance_alert import (
    ComplianceAlertSystem,
    AlertSeverity,
    AlertStatus,
    RemediationEngine
)


class TestDocumentExtraction:
    """Test document extraction accuracy"""
    
    def test_invoice_extraction_with_valid_data(self):
        """Test extraction from a valid invoice document"""
        agent = RiskComplianceAgent(register_with_council=False)
        
        document = DocumentData(
            document_id="inv-001",
            document_type="invoice",
            content="""
            INVOICE
            Invoice Number: INV-2024-001
            Date: 15/01/2024
            Vendor: ABC Suppliers Ltd
            Total Amount: Rs. 50,000.00
            """,
            metadata={},
            timestamp=datetime.now(timezone.utc)
        )
        
        result = agent.extract_and_validate_document(document)
        
        # Verify extraction
        assert result['document_id'] == "inv-001"
        assert result['document_type'] == "invoice"
        assert result['extracted_data']['invoice_number'] == "INV-2024-001"
        assert result['extracted_data']['amount'] == 50000.0
        assert result['extracted_data']['vendor'] == "ABC Suppliers Ltd"
        assert result['validation']['is_valid'] is True
    
    def test_gst_extraction_with_valid_data(self):
        """Test extraction from a valid GST document"""
        agent = RiskComplianceAgent(register_with_council=False)
        
        document = DocumentData(
            document_id="gst-001",
            document_type="gst",
            content="""
            GST DOCUMENT
            GSTIN: 29ABCDE1234F1Z5
            Tax Amount: Rs. 9,000.00
            """,
            metadata={},
            timestamp=datetime.now(timezone.utc)
        )
        
        result = agent.extract_and_validate_document(document)
        
        # Verify extraction
        assert result['document_id'] == "gst-001"
        assert result['document_type'] == "gst"
        assert result['extracted_data']['gstin'] == "29ABCDE1234F1Z5"
        assert result['extracted_data']['tax_amount'] == 9000.0
        assert result['validation']['is_valid'] is True
    
    def test_invoice_extraction_with_missing_fields(self):
        """Test extraction from invoice with missing required fields"""
        agent = RiskComplianceAgent(register_with_council=False)
        
        document = DocumentData(
            document_id="inv-002",
            document_type="invoice",
            content="""
            INVOICE
            Some random text without proper fields
            """,
            metadata={},
            timestamp=datetime.now(timezone.utc)
        )
        
        result = agent.extract_and_validate_document(document)
        
        # Verify validation catches missing fields
        assert result['validation']['is_valid'] is False
        assert len(result['validation']['errors']) > 0


class TestSupplierRiskScoring:
    """Test supplier risk scoring calculation"""
    
    def test_supplier_with_good_history(self):
        """Test risk scoring for supplier with good history"""
        agent = RiskComplianceAgent(register_with_council=False)
        
        # Create supplier with good history
        transactions = [
            TransactionData(
                transaction_id=f"txn-{i}",
                supplier_id="supplier-001",
                amount=10000.0 + i * 100,
                timestamp=datetime.now(timezone.utc) - timedelta(days=i),
                metadata={'on_time': True}
            )
            for i in range(10)
        ]
        
        supplier = SupplierData(
            supplier_id="supplier-001",
            name="Good Supplier Ltd",
            transaction_history=transactions,
            compliance_records=[
                {'date': '2024-01-01', 'violation': False},
                {'date': '2024-02-01', 'violation': False}
            ],
            performance_metrics={
                'quality_score': 0.95,
                'delivery_score': 0.90
            }
        )
        
        result = agent.score_supplier_risk(supplier)
        
        # Verify low risk score
        assert result['supplier_id'] == "supplier-001"
        assert result['risk_level'] == 'low'
        assert result['risk_score'] >= 0.8
    
    def test_supplier_with_poor_history(self):
        """Test risk scoring for supplier with poor history"""
        agent = RiskComplianceAgent(register_with_council=False)
        
        # Create supplier with poor history
        transactions = [
            TransactionData(
                transaction_id=f"txn-{i}",
                supplier_id="supplier-002",
                amount=10000.0 + i * 100,
                timestamp=datetime.now(timezone.utc) - timedelta(days=i),
                metadata={'on_time': False}  # Late payments
            )
            for i in range(10)
        ]
        
        supplier = SupplierData(
            supplier_id="supplier-002",
            name="Risky Supplier Ltd",
            transaction_history=transactions,
            compliance_records=[
                {'date': '2024-01-01', 'violation': True},
                {'date': '2024-02-01', 'violation': True},
                {'date': '2024-03-01', 'violation': False}
            ],
            performance_metrics={
                'quality_score': 0.50,
                'delivery_score': 0.45
            }
        )
        
        result = agent.score_supplier_risk(supplier)
        
        # Verify high risk score
        assert result['supplier_id'] == "supplier-002"
        assert result['risk_level'] in ['medium', 'high']
        assert result['risk_score'] < 0.8
    
    def test_supplier_with_no_history(self):
        """Test risk scoring for new supplier with no history"""
        agent = RiskComplianceAgent(register_with_council=False)
        
        supplier = SupplierData(
            supplier_id="supplier-003",
            name="New Supplier Ltd",
            transaction_history=[],
            compliance_records=[],
            performance_metrics={}
        )
        
        result = agent.score_supplier_risk(supplier)
        
        # Verify neutral risk score (all factors are 0.5, so overall is 0.5 which is < 0.6, making it high risk)
        assert result['supplier_id'] == "supplier-003"
        # With all neutral scores (0.5), the overall score is 0.5 which falls into high risk category
        assert result['risk_level'] in ['medium', 'high']
        assert 0.4 <= result['risk_score'] <= 0.6


class TestFraudDetection:
    """Test fraud pattern detection"""
    
    def test_duplicate_transaction_detection(self):
        """Test detection of duplicate transactions"""
        agent = RiskComplianceAgent(register_with_council=False)
        
        base_time = datetime.now(timezone.utc)
        transactions = [
            TransactionData(
                transaction_id="txn-001",
                supplier_id="supplier-001",
                amount=10000.0,
                timestamp=base_time,
                metadata={}
            ),
            TransactionData(
                transaction_id="txn-002",
                supplier_id="supplier-001",
                amount=10000.0,  # Same amount
                timestamp=base_time + timedelta(minutes=10),  # Within 1 hour
                metadata={}
            )
        ]
        
        result = agent.detect_fraud(transactions)
        
        # Verify duplicate detection
        assert len(result['fraud_alerts']) > 0
        duplicate_alerts = [a for a in result['fraud_alerts'] if a['type'] == 'duplicate_transaction']
        assert len(duplicate_alerts) > 0
    
    def test_high_velocity_detection(self):
        """Test detection of high-velocity transaction patterns"""
        agent = RiskComplianceAgent(register_with_council=False)
        
        base_time = datetime.now(timezone.utc)
        transactions = [
            TransactionData(
                transaction_id=f"txn-{i}",
                supplier_id="supplier-001",
                amount=1000.0 + i * 100,
                timestamp=base_time + timedelta(minutes=i * 5),
                metadata={}
            )
            for i in range(6)  # 6 transactions in 30 minutes
        ]
        
        result = agent.detect_fraud(transactions)
        
        # Verify high velocity detection
        high_velocity_alerts = [a for a in result['fraud_alerts'] if a['type'] == 'high_velocity']
        assert len(high_velocity_alerts) > 0
    
    def test_amount_anomaly_detection(self):
        """Test detection of amount anomalies"""
        agent = RiskComplianceAgent(register_with_council=False)
        
        # Create normal transactions and one outlier
        transactions = [
            TransactionData(
                transaction_id=f"txn-{i}",
                supplier_id=f"supplier-{i}",
                amount=1000.0 + i * 100,
                timestamp=datetime.now(timezone.utc) - timedelta(days=i),
                metadata={}
            )
            for i in range(10)
        ]
        
        # Add outlier
        transactions.append(
            TransactionData(
                transaction_id="txn-outlier",
                supplier_id="supplier-outlier",
                amount=1000000.0,  # Very large amount
                timestamp=datetime.now(timezone.utc),
                metadata={}
            )
        )
        
        result = agent.detect_fraud(transactions)
        
        # Verify amount anomaly detection
        amount_anomalies = [a for a in result['anomalies'] if a['type'] == 'amount_anomaly']
        assert len(amount_anomalies) > 0


class TestContractSummarization:
    """Test contract summarization"""
    
    def test_contract_key_terms_extraction(self):
        """Test extraction of key terms from contract"""
        agent = RiskComplianceAgent(register_with_council=False)
        
        document = DocumentData(
            document_id="contract-001",
            document_type="contract",
            content="""
            SERVICE AGREEMENT
            
            This agreement is for a term of 2 years.
            Payment terms: Net 30 days from invoice date.
            Either party may terminate this agreement with 60 days notice.
            Liability is limited to the contract value.
            """,
            metadata={},
            timestamp=datetime.now(timezone.utc)
        )
        
        result = agent.summarize_contract(document)
        
        # Verify key terms extraction
        assert 'key_terms' in result
        assert len(result['key_terms']) > 0
        
        # Check for specific terms
        term_types = [term['term'] for term in result['key_terms']]
        assert 'payment_period' in term_types or 'contract_duration' in term_types
    
    def test_contract_risk_identification(self):
        """Test identification of risks in contract"""
        agent = RiskComplianceAgent(register_with_council=False)
        
        document = DocumentData(
            document_id="contract-002",
            document_type="contract",
            content="""
            SERVICE AGREEMENT
            
            Payment terms: Net 120 days from invoice date.
            Penalties apply for late delivery.
            """,
            metadata={},
            timestamp=datetime.now(timezone.utc)
        )
        
        result = agent.summarize_contract(document)
        
        # Verify risk identification
        assert 'risks' in result
        # Should identify extended payment terms
        risk_types = [risk['risk'] for risk in result['risks']]
        assert any('payment' in risk_type or 'termination' in risk_type for risk_type in risk_types)


class TestComplianceAlertSystem:
    """Test compliance alert system"""
    
    def test_alert_generation(self):
        """Test generation of compliance alerts"""
        alert_system = ComplianceAlertSystem()
        
        alert = alert_system.generate_alert(
            alert_type='document_validation_failure',
            severity='high',
            description='Invoice validation failed',
            metadata={'document_id': 'inv-001'}
        )
        
        # Verify alert structure
        assert alert.alert_type == 'document_validation_failure'
        assert alert.severity == AlertSeverity.HIGH
        assert alert.status == AlertStatus.OPEN
        assert len(alert.remediation) > 0
    
    def test_remediation_engine(self):
        """Test remediation recommendation engine"""
        engine = RemediationEngine()
        
        remediation = engine.get_remediation(
            alert_type='high_supplier_risk',
            severity=AlertSeverity.HIGH,
            context={'supplier_id': 'supplier-001'}
        )
        
        # Verify remediation is provided
        assert len(remediation) > 0
        assert 'audit' in remediation.lower() or 'review' in remediation.lower()
    
    def test_alert_filtering(self):
        """Test filtering of alerts"""
        alert_system = ComplianceAlertSystem()
        
        # Generate multiple alerts
        alert_system.generate_alert('type1', 'high', 'Description 1')
        alert_system.generate_alert('type2', 'low', 'Description 2')
        alert_system.generate_alert('type1', 'medium', 'Description 3')
        
        # Filter by severity
        high_alerts = alert_system.get_alerts(severity=AlertSeverity.HIGH)
        assert len(high_alerts) == 1
        
        # Filter by type
        type1_alerts = alert_system.get_alerts(alert_type='type1')
        assert len(type1_alerts) == 2
    
    def test_alert_status_update(self):
        """Test updating alert status"""
        alert_system = ComplianceAlertSystem()
        
        alert = alert_system.generate_alert('test_type', 'medium', 'Test description')
        
        # Update status
        success = alert_system.update_alert_status(alert.alert_id, AlertStatus.RESOLVED)
        assert success is True
        
        # Verify status changed
        resolved_alerts = alert_system.get_alerts(status=AlertStatus.RESOLVED)
        assert len(resolved_alerts) == 1
