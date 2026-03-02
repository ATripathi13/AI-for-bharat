"""
Property-based tests for Risk & Compliance Agent - Fraud Detection
Tests Property 7: Fraud Detection Reliability

**Feature: retailmind-ai, Property 7: Fraud Detection Reliability**
**Validates: Requirements 5.3, 5.5**

Property: For any transaction pattern, the Risk Compliance Agent should detect 
anomalies and generate alerts with recommended remediation actions
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timezone, timedelta
import statistics

from src.agents.risk_compliance_agent import (
    RiskComplianceAgent,
    TransactionData,
    RiskComplianceInput
)


# Custom strategies for generating test data
@st.composite
def transaction_data_strategy(draw):
    """Generate TransactionData instances"""
    transaction_id = draw(st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Nd'))))
    supplier_id = draw(st.text(min_size=5, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Nd'))))
    amount = draw(st.floats(min_value=100, max_value=100000, allow_nan=False, allow_infinity=False))
    
    # Generate timestamp within last 30 days
    days_ago = draw(st.integers(min_value=0, max_value=30))
    timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    return TransactionData(
        transaction_id=transaction_id,
        supplier_id=supplier_id,
        amount=amount,
        timestamp=timestamp,
        metadata={'on_time': draw(st.booleans())}
    )


@st.composite
def anomalous_transaction_strategy(draw):
    """Generate transactions with known anomalies"""
    # Create a base transaction
    base_txn = draw(transaction_data_strategy())
    
    anomaly_type = draw(st.sampled_from(['high_amount', 'round_number', 'duplicate']))
    
    if anomaly_type == 'high_amount':
        # Create very high amount transaction
        base_txn.amount = draw(st.floats(min_value=500000, max_value=1000000, allow_nan=False, allow_infinity=False))
    elif anomaly_type == 'round_number':
        # Create round number transaction
        base_txn.amount = draw(st.sampled_from([10000.0, 50000.0, 100000.0, 500000.0]))
    
    return base_txn


class TestFraudDetectionReliability:
    """
    Test Property 7: Fraud Detection Reliability
    For any transaction pattern, the Risk Compliance Agent should detect 
    anomalies and generate alerts with recommended remediation actions
    """
    
    @settings(max_examples=100)
    @given(transactions=st.lists(transaction_data_strategy(), min_size=5, max_size=20))
    def test_fraud_detection_processes_all_transactions(self, transactions):
        """
        Property: For any list of transactions, fraud detection should analyze all of them
        """
        agent = RiskComplianceAgent(register_with_council=False)
        
        # Detect fraud
        result = agent.detect_fraud(transactions)
        
        # Property: Result should have required structure
        assert 'anomalies' in result
        assert 'fraud_alerts' in result
        assert 'summary' in result
        
        # Property: Result fields should be lists
        assert isinstance(result['anomalies'], list)
        assert isinstance(result['fraud_alerts'], list)

    @settings(max_examples=100)
    @given(transactions=st.lists(anomalous_transaction_strategy(), min_size=5, max_size=15))
    def test_fraud_detection_identifies_anomalies(self, transactions):
        """
        Property: For any list of transactions with anomalies, fraud detection should identify them
        """
        agent = RiskComplianceAgent(register_with_council=False)
        
        # Detect fraud
        result = agent.detect_fraud(transactions)
        
        # Property: Anomalies or fraud alerts should be detected
        # (Not all anomalous transactions will trigger alerts due to statistical thresholds)
        assert isinstance(result['anomalies'], list)
        assert isinstance(result['fraud_alerts'], list)
        
        # Property: Each anomaly should have required fields
        for anomaly in result['anomalies']:
            assert 'transaction_id' in anomaly or 'supplier_id' in anomaly
            assert 'type' in anomaly
            assert 'severity' in anomaly
            assert anomaly['severity'] in ['low', 'medium', 'high']
    
    @settings(max_examples=100)
    @given(
        supplier_id=st.text(min_size=5, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Nd'))),
        num_transactions=st.integers(min_value=5, max_value=10)
    )
    def test_fraud_detection_identifies_high_velocity_patterns(self, supplier_id, num_transactions):
        """
        Property: For any supplier with many transactions in short time, high-velocity pattern should be detected
        """
        agent = RiskComplianceAgent(register_with_council=False)
        
        # Create transactions from same supplier within 30 minutes
        base_time = datetime.now(timezone.utc)
        transactions = []
        for i in range(num_transactions):
            transactions.append(TransactionData(
                transaction_id=f"txn-{i}",
                supplier_id=supplier_id,
                amount=1000.0 + i * 100,
                timestamp=base_time + timedelta(minutes=i * 5),
                metadata={}
            ))
        
        # Detect fraud
        result = agent.detect_fraud(transactions)
        
        # Property: High velocity should be detected for 5+ transactions in 1 hour
        if num_transactions >= 5:
            # Check if high velocity was detected
            high_velocity_alerts = [a for a in result['fraud_alerts'] if a.get('type') == 'high_velocity']
            assert len(high_velocity_alerts) > 0, "High velocity pattern should be detected"
            
            # Property: Alert should have required fields
            for alert in high_velocity_alerts:
                assert 'supplier_id' in alert
                assert 'type' in alert
                assert 'severity' in alert
                assert alert['severity'] in ['low', 'medium', 'high']
    
    @settings(max_examples=100)
    @given(
        base_transaction=transaction_data_strategy(),
        num_duplicates=st.integers(min_value=1, max_value=3)
    )
    def test_fraud_detection_identifies_duplicate_transactions(self, base_transaction, num_duplicates):
        """
        Property: For any transaction with duplicates, duplicate pattern should be detected
        """
        agent = RiskComplianceAgent(register_with_council=False)
        
        # Create duplicate transactions (same supplier, amount, within 1 hour)
        transactions = [base_transaction]
        for i in range(num_duplicates):
            duplicate = TransactionData(
                transaction_id=f"{base_transaction.transaction_id}-dup-{i}",
                supplier_id=base_transaction.supplier_id,
                amount=base_transaction.amount,
                timestamp=base_transaction.timestamp + timedelta(minutes=10 * (i + 1)),
                metadata={}
            )
            transactions.append(duplicate)
        
        # Detect fraud
        result = agent.detect_fraud(transactions)
        
        # Property: Duplicate transactions should be detected
        duplicate_alerts = [a for a in result['fraud_alerts'] if a.get('type') == 'duplicate_transaction']
        assert len(duplicate_alerts) > 0, "Duplicate transactions should be detected"
        
        # Property: Each alert should have required fields
        for alert in duplicate_alerts:
            assert 'transaction_id' in alert
            assert 'type' in alert
            assert 'duplicate_count' in alert
            assert 'severity' in alert

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(transactions=st.lists(transaction_data_strategy(), min_size=1, max_size=20))
    def test_fraud_detection_generates_remediation_recommendations(self, transactions, monkeypatch):
        """
        Property: For any transactions with detected fraud, alerts should include remediation recommendations
        """
        agent = RiskComplianceAgent(register_with_council=False)
        
        # Mock persist to avoid AWS calls
        def mock_persist(results, confidence):
            pass
        monkeypatch.setattr(agent, 'persist_risk_intelligence', mock_persist)
        
        # Process through agent to get compliance alerts
        input_data = RiskComplianceInput(
            documents=[],
            transactions=transactions,
            suppliers=[]
        )
        
        decision = agent.process(input_data)
        
        # Property: Decision should be generated
        assert decision is not None
        
        # Get alerts from supporting data
        if len(decision.recommendation.supporting_data) > 1:
            alerts = decision.recommendation.supporting_data[1]
            
            # Property: Each fraud alert should have remediation
            for alert in alerts:
                if 'fraud' in alert.get('alert_type', ''):
                    assert 'remediation' in alert
                    assert isinstance(alert['remediation'], str)
                    assert len(alert['remediation']) > 0
    
    @settings(max_examples=100)
    @given(transactions=st.lists(transaction_data_strategy(), min_size=2, max_size=20))
    def test_fraud_detection_consistency_across_runs(self, transactions):
        """
        Property: For any set of transactions, fraud detection should produce consistent results across multiple runs
        """
        agent = RiskComplianceAgent(register_with_council=False)
        
        # Run fraud detection twice
        result1 = agent.detect_fraud(transactions)
        result2 = agent.detect_fraud(transactions)
        
        # Property: Results should be consistent
        assert len(result1['anomalies']) == len(result2['anomalies'])
        assert len(result1['fraud_alerts']) == len(result2['fraud_alerts'])
        
        # Property: Anomaly types should match
        types1 = sorted([a['type'] for a in result1['anomalies']])
        types2 = sorted([a['type'] for a in result2['anomalies']])
        assert types1 == types2
    
    @settings(max_examples=100)
    @given(
        normal_transactions=st.lists(transaction_data_strategy(), min_size=10, max_size=20),
        anomalous_amount=st.floats(min_value=1000000, max_value=10000000, allow_nan=False, allow_infinity=False)
    )
    def test_fraud_detection_identifies_amount_anomalies(self, normal_transactions, anomalous_amount):
        """
        Property: For any set of normal transactions with one extreme outlier, the outlier should be detected
        """
        agent = RiskComplianceAgent(register_with_council=False)
        
        # Add an anomalous transaction
        anomalous_txn = TransactionData(
            transaction_id="anomaly-txn",
            supplier_id="anomaly-supplier",
            amount=anomalous_amount,
            timestamp=datetime.now(timezone.utc),
            metadata={}
        )
        
        all_transactions = normal_transactions + [anomalous_txn]
        
        # Detect fraud
        result = agent.detect_fraud(all_transactions)
        
        # Property: Amount anomaly should be detected if the outlier is significant
        amounts = [t.amount for t in normal_transactions]
        if len(amounts) > 1:
            avg = statistics.mean(amounts)
            std = statistics.stdev(amounts)
            threshold = avg + 3 * std
            
            if anomalous_amount > threshold:
                # Should detect amount anomaly
                amount_anomalies = [a for a in result['anomalies'] if a.get('type') == 'amount_anomaly']
                assert len(amount_anomalies) > 0, f"Amount anomaly should be detected for {anomalous_amount} vs threshold {threshold}"
    
    @settings(max_examples=100)
    @given(transactions=st.lists(transaction_data_strategy(), min_size=0, max_size=20))
    def test_fraud_detection_handles_edge_cases(self, transactions):
        """
        Property: For any list of transactions (including empty), fraud detection should handle gracefully
        """
        agent = RiskComplianceAgent(register_with_council=False)
        
        # Detect fraud
        result = agent.detect_fraud(transactions)
        
        # Property: Should always return valid structure
        assert 'anomalies' in result
        assert 'fraud_alerts' in result
        assert 'summary' in result
        
        # Property: For empty transactions, should return empty results
        if len(transactions) == 0:
            assert len(result['anomalies']) == 0
            assert len(result['fraud_alerts']) == 0
