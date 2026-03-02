"""
Risk & Compliance Agent for RetailMind AI
Handles document processing, invoice validation, supplier risk scoring, and fraud detection
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from decimal import Decimal
import re
import statistics

from .base_agent import BaseAgent
from .registry import AgentRegistry
from .communication import AgentCommunicationInterface, ACPMessage, MessageType
from ..models.agent_decision import AgentDecision
from ..models.business_intelligence import (
    BusinessIntelligence, EntityType, Insights, 
    ActionRecommendation, Priority
)
from ..repositories.dynamodb_repository import BusinessIntelligenceRepository
from ..repositories.s3_repository import S3Repository


@dataclass
class DocumentData:
    """Document data for processing"""
    document_id: str
    document_type: str  # 'invoice', 'gst', 'contract'
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class TransactionData:
    """Transaction data for fraud detection"""
    transaction_id: str
    supplier_id: str
    amount: float
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class SupplierData:
    """Supplier data for risk scoring"""
    supplier_id: str
    name: str
    transaction_history: List[TransactionData]
    compliance_records: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]


@dataclass
class RiskComplianceInput:
    """Input data for Risk & Compliance Agent"""
    documents: List[DocumentData]
    transactions: List[TransactionData]
    suppliers: List[SupplierData]


class RiskComplianceAgent(BaseAgent):
    """
    Risk & Compliance Agent
    Processes documents, validates invoices, scores supplier risk, and detects fraud
    """
    
    def __init__(
        self, 
        agent_id: str = "risk-compliance-agent",
        s3_bucket: str = "retailmind-risk-compliance",
        register_with_council: bool = True
    ):
        """
        Initialize Risk & Compliance Agent
        
        Args:
            agent_id: Unique identifier for the agent
            s3_bucket: S3 bucket for storing compliance data
            register_with_council: Whether to register with AI Council on initialization
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="risk_compliance",
            version="1.0.0"
        )
        
        # Initialize communication and registry
        self.communication = AgentCommunicationInterface()
        self.registry = AgentRegistry()
        
        # Initialize data persistence
        self.bi_repository = BusinessIntelligenceRepository()
        self.s3_repository = S3Repository(s3_bucket)
        
        # Register with AI Council if requested
        if register_with_council:
            self.register()
    
    def register(self):
        """Register this agent with the AI Council"""
        try:
            self.registry.register_agent(self.metadata)
            print(f"Risk & Compliance Agent {self.metadata.agent_id} registered successfully")
        except Exception as e:
            print(f"Failed to register Risk & Compliance Agent: {str(e)}")
            raise
    
    def unregister(self):
        """Unregister this agent from the AI Council"""
        try:
            self.registry.unregister_agent(self.metadata.agent_id)
            print(f"Risk & Compliance Agent {self.metadata.agent_id} unregistered successfully")
        except Exception as e:
            print(f"Failed to unregister Risk & Compliance Agent: {str(e)}")
            raise
    
    def get_capabilities(self) -> List[str]:
        """Return agent capabilities"""
        return [
            "document_extraction",
            "invoice_validation",
            "gst_validation",
            "supplier_risk_scoring",
            "fraud_detection",
            "contract_summarization"
        ]

    def process(self, input_data: RiskComplianceInput) -> AgentDecision:
        """
        Process risk and compliance data
        
        Args:
            input_data: RiskComplianceInput with documents, transactions, and suppliers
            
        Returns:
            AgentDecision with risk and compliance recommendations
        """
        # Process documents
        document_results = []
        for doc in input_data.documents:
            if doc.document_type in ['invoice', 'gst']:
                result = self.extract_and_validate_document(doc)
                document_results.append(result)
            elif doc.document_type == 'contract':
                result = self.summarize_contract(doc)
                document_results.append(result)
        
        # Score supplier risk
        supplier_scores = []
        for supplier in input_data.suppliers:
            score = self.score_supplier_risk(supplier)
            supplier_scores.append(score)
        
        # Detect fraud in transactions
        fraud_results = self.detect_fraud(input_data.transactions)
        
        # Aggregate results
        results = {
            'document_processing': document_results,
            'supplier_risk_scores': supplier_scores,
            'fraud_detection': fraud_results
        }
        
        # Calculate confidence
        confidence = self._calculate_confidence(results)
        
        # Generate compliance alerts
        alerts = self._generate_compliance_alerts(results)
        
        # Create decision
        decision = self.create_decision(
            input_data=input_data,
            action="risk_compliance_update",
            confidence=confidence,
            reasoning=f"Processed {len(input_data.documents)} documents, scored {len(input_data.suppliers)} suppliers, analyzed {len(input_data.transactions)} transactions",
            supporting_data=[results, alerts]
        )
        
        # Persist risk intelligence
        self.persist_risk_intelligence(results, confidence)
        
        return decision
    
    def extract_and_validate_document(self, document: DocumentData) -> Dict[str, Any]:
        """
        Extract and validate invoice/GST document information
        Simulates Amazon Textract integration
        
        Args:
            document: DocumentData to process
            
        Returns:
            Dictionary with extraction and validation results
        """
        # Simulate document extraction (in production, use Amazon Textract)
        extracted_data = self._simulate_textract_extraction(document)
        
        # Validate extracted data
        validation_result = self._validate_document_data(extracted_data, document.document_type)
        
        return {
            'document_id': document.document_id,
            'document_type': document.document_type,
            'extracted_data': extracted_data,
            'validation': validation_result,
            'accuracy': validation_result.get('accuracy', 0.0),
            'timestamp': document.timestamp.isoformat()
        }

    def _simulate_textract_extraction(self, document: DocumentData) -> Dict[str, Any]:
        """
        Simulate Amazon Textract document extraction
        In production, this would call Amazon Textract API
        
        Args:
            document: DocumentData to extract from
            
        Returns:
            Extracted data dictionary
        """
        content = document.content
        extracted = {}
        
        if document.document_type == 'invoice':
            # Extract invoice fields using regex patterns
            invoice_number_match = re.search(r'Invoice\s+Number[#:\s]+([A-Z0-9-]+)', content, re.IGNORECASE)
            amount_match = re.search(r'(?:Total|Amount)[:\s]+(?:Rs\.?|INR|₹)?\s*([0-9,]+\.?\d*)', content, re.IGNORECASE)
            date_match = re.search(r'Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', content, re.IGNORECASE)
            vendor_match = re.search(r'(?:Vendor|Supplier)[:\s]+([A-Za-z\s&]+?)(?:\n|$)', content, re.IGNORECASE)
            
            extracted = {
                'invoice_number': invoice_number_match.group(1) if invoice_number_match else None,
                'amount': float(amount_match.group(1).replace(',', '')) if amount_match else None,
                'date': date_match.group(1) if date_match else None,
                'vendor': vendor_match.group(1).strip() if vendor_match else None
            }
        
        elif document.document_type == 'gst':
            # Extract GST fields
            gstin_match = re.search(r'GSTIN[:\s]+([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})', content, re.IGNORECASE)
            tax_amount_match = re.search(r'(?:Tax\s+Amount|GST)[:\s]+(?:Rs\.?|INR|₹)?\s*([0-9,]+\.?\d*)', content, re.IGNORECASE)
            
            extracted = {
                'gstin': gstin_match.group(1) if gstin_match else None,
                'tax_amount': float(tax_amount_match.group(1).replace(',', '')) if tax_amount_match else None
            }
        
        # Add metadata
        extracted['extraction_confidence'] = self._calculate_extraction_confidence(extracted)
        
        return extracted
    
    def _calculate_extraction_confidence(self, extracted_data: Dict[str, Any]) -> float:
        """Calculate confidence in extraction based on fields found"""
        if not extracted_data:
            return 0.0
        
        # Count non-None fields (excluding extraction_confidence itself)
        valid_fields = sum(1 for k, v in extracted_data.items() 
                          if k != 'extraction_confidence' and v is not None)
        total_fields = len([k for k in extracted_data.keys() if k != 'extraction_confidence'])
        
        if total_fields == 0:
            return 0.0
        
        return min(0.95, valid_fields / total_fields)
    
    def _validate_document_data(self, extracted_data: Dict[str, Any], document_type: str) -> Dict[str, Any]:
        """
        Validate extracted document data
        
        Args:
            extracted_data: Extracted data dictionary
            document_type: Type of document
            
        Returns:
            Validation result dictionary
        """
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'accuracy': 0.95  # Default high accuracy
        }
        
        if document_type == 'invoice':
            # Validate invoice fields
            if not extracted_data.get('invoice_number'):
                validation['errors'].append('Missing invoice number')
                validation['is_valid'] = False
            
            if not extracted_data.get('amount') or extracted_data.get('amount', 0) <= 0:
                validation['errors'].append('Invalid or missing amount')
                validation['is_valid'] = False
            
            if not extracted_data.get('date'):
                validation['warnings'].append('Missing date')
            
            if not extracted_data.get('vendor'):
                validation['warnings'].append('Missing vendor information')
        
        elif document_type == 'gst':
            # Validate GST fields
            gstin = extracted_data.get('gstin')
            if not gstin or len(gstin) != 15:
                validation['errors'].append('Invalid GSTIN format')
                validation['is_valid'] = False
            
            if not extracted_data.get('tax_amount') or extracted_data.get('tax_amount', 0) <= 0:
                validation['errors'].append('Invalid or missing tax amount')
                validation['is_valid'] = False
        
        # Adjust accuracy based on errors and warnings
        if validation['errors']:
            validation['accuracy'] = max(0.5, 0.95 - len(validation['errors']) * 0.15)
        elif validation['warnings']:
            validation['accuracy'] = max(0.85, 0.95 - len(validation['warnings']) * 0.05)
        
        return validation

    def score_supplier_risk(self, supplier: SupplierData) -> Dict[str, Any]:
        """
        Generate supplier risk score based on historical performance and compliance
        
        Args:
            supplier: SupplierData to score
            
        Returns:
            Dictionary with risk score and analysis
        """
        risk_factors = {
            'payment_reliability': 0.0,
            'compliance_history': 0.0,
            'transaction_consistency': 0.0,
            'performance_quality': 0.0
        }
        
        # Analyze payment reliability
        if supplier.transaction_history:
            on_time_count = sum(1 for t in supplier.transaction_history 
                               if t.metadata.get('on_time', True))
            risk_factors['payment_reliability'] = on_time_count / len(supplier.transaction_history)
        else:
            risk_factors['payment_reliability'] = 0.5  # Neutral for no history
        
        # Analyze compliance history
        if supplier.compliance_records:
            violations = sum(1 for r in supplier.compliance_records 
                           if r.get('violation', False))
            risk_factors['compliance_history'] = 1.0 - (violations / max(len(supplier.compliance_records), 1))
        else:
            risk_factors['compliance_history'] = 0.5  # Neutral for no history
        
        # Analyze transaction consistency
        if supplier.transaction_history and len(supplier.transaction_history) > 1:
            amounts = [t.amount for t in supplier.transaction_history]
            avg_amount = statistics.mean(amounts)
            std_amount = statistics.stdev(amounts) if len(amounts) > 1 else 0.0
            
            # Lower variance = higher consistency = lower risk
            if avg_amount > 0:
                coefficient_of_variation = std_amount / avg_amount
                risk_factors['transaction_consistency'] = max(0.0, 1.0 - coefficient_of_variation)
            else:
                risk_factors['transaction_consistency'] = 0.5
        else:
            risk_factors['transaction_consistency'] = 0.5
        
        # Analyze performance quality
        if supplier.performance_metrics:
            quality_score = supplier.performance_metrics.get('quality_score', 0.5)
            delivery_score = supplier.performance_metrics.get('delivery_score', 0.5)
            risk_factors['performance_quality'] = (quality_score + delivery_score) / 2
        else:
            risk_factors['performance_quality'] = 0.5
        
        # Calculate overall risk score (0 = high risk, 1 = low risk)
        overall_score = statistics.mean(risk_factors.values())
        
        # Convert to risk level
        if overall_score >= 0.8:
            risk_level = 'low'
        elif overall_score >= 0.6:
            risk_level = 'medium'
        else:
            risk_level = 'high'
        
        return {
            'supplier_id': supplier.supplier_id,
            'supplier_name': supplier.name,
            'risk_score': overall_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'recommendation': self._get_supplier_recommendation(risk_level)
        }
    
    def _get_supplier_recommendation(self, risk_level: str) -> str:
        """Get recommendation based on risk level"""
        recommendations = {
            'low': 'Continue business relationship with standard monitoring',
            'medium': 'Increase monitoring frequency and review contract terms',
            'high': 'Conduct detailed audit and consider alternative suppliers'
        }
        return recommendations.get(risk_level, 'Review supplier relationship')

    def detect_fraud(self, transactions: List[TransactionData]) -> Dict[str, Any]:
        """
        Detect fraud and anomalies using pattern recognition
        
        Args:
            transactions: List of transactions to analyze
            
        Returns:
            Dictionary with fraud detection results
        """
        if not transactions:
            return {
                'anomalies': [],
                'fraud_alerts': [],
                'summary': 'No transactions to analyze'
            }
        
        anomalies = []
        fraud_alerts = []
        
        # Calculate baseline statistics
        amounts = [t.amount for t in transactions]
        if len(amounts) > 1:
            avg_amount = statistics.mean(amounts)
            std_amount = statistics.stdev(amounts)
            
            # Detect amount anomalies (transactions > 3 standard deviations)
            threshold = avg_amount + 3 * std_amount
            
            for transaction in transactions:
                # Check for amount anomalies
                if transaction.amount > threshold:
                    anomalies.append({
                        'transaction_id': transaction.transaction_id,
                        'type': 'amount_anomaly',
                        'amount': transaction.amount,
                        'threshold': threshold,
                        'severity': 'high' if transaction.amount > threshold * 1.5 else 'medium'
                    })
                
                # Check for duplicate transactions (same supplier, amount, within 1 hour)
                duplicates = [t for t in transactions 
                            if t.transaction_id != transaction.transaction_id
                            and t.supplier_id == transaction.supplier_id
                            and abs(t.amount - transaction.amount) < 0.01
                            and abs((t.timestamp - transaction.timestamp).total_seconds()) < 3600]
                
                if duplicates:
                    fraud_alerts.append({
                        'transaction_id': transaction.transaction_id,
                        'type': 'duplicate_transaction',
                        'duplicate_count': len(duplicates),
                        'severity': 'high'
                    })
                
                # Check for round number patterns (potential fraud indicator)
                if transaction.amount % 1000 == 0 and transaction.amount >= 10000:
                    anomalies.append({
                        'transaction_id': transaction.transaction_id,
                        'type': 'round_number_pattern',
                        'amount': transaction.amount,
                        'severity': 'low'
                    })
        
        # Group transactions by supplier to detect velocity anomalies
        supplier_transactions = {}
        for t in transactions:
            if t.supplier_id not in supplier_transactions:
                supplier_transactions[t.supplier_id] = []
            supplier_transactions[t.supplier_id].append(t)
        
        # Detect high-velocity patterns (many transactions in short time)
        for supplier_id, supplier_txns in supplier_transactions.items():
            if len(supplier_txns) >= 5:
                # Sort by timestamp
                sorted_txns = sorted(supplier_txns, key=lambda x: x.timestamp)
                
                # Check for 5+ transactions within 1 hour
                for i in range(len(sorted_txns) - 4):
                    time_window = (sorted_txns[i + 4].timestamp - sorted_txns[i].timestamp).total_seconds()
                    if time_window < 3600:  # 1 hour
                        fraud_alerts.append({
                            'supplier_id': supplier_id,
                            'type': 'high_velocity',
                            'transaction_count': 5,
                            'time_window_seconds': time_window,
                            'severity': 'high'
                        })
                        break
        
        return {
            'anomalies': anomalies,
            'fraud_alerts': fraud_alerts,
            'summary': f'Detected {len(anomalies)} anomalies and {len(fraud_alerts)} fraud alerts from {len(transactions)} transactions'
        }

    def summarize_contract(self, document: DocumentData) -> Dict[str, Any]:
        """
        Summarize contract highlighting key terms and risks
        Simulates Amazon Bedrock integration
        
        Args:
            document: Contract document to summarize
            
        Returns:
            Dictionary with contract summary
        """
        content = document.content
        
        # Simulate contract analysis (in production, use Amazon Bedrock)
        summary = {
            'document_id': document.document_id,
            'key_terms': self._extract_key_terms(content),
            'risks': self._identify_contract_risks(content),
            'summary_text': self._generate_summary_text(content),
            'timestamp': document.timestamp.isoformat()
        }
        
        return summary
    
    def _extract_key_terms(self, content: str) -> List[Dict[str, Any]]:
        """Extract key terms from contract"""
        key_terms = []
        
        # Extract payment terms
        payment_match = re.search(r'payment.*?(\d+)\s*days?', content, re.IGNORECASE)
        if payment_match:
            key_terms.append({
                'term': 'payment_period',
                'value': f"{payment_match.group(1)} days",
                'importance': 'high'
            })
        
        # Extract contract duration
        duration_match = re.search(r'(?:term|duration).*?(\d+)\s*(year|month)', content, re.IGNORECASE)
        if duration_match:
            key_terms.append({
                'term': 'contract_duration',
                'value': f"{duration_match.group(1)} {duration_match.group(2)}s",
                'importance': 'high'
            })
        
        # Extract termination clause
        if re.search(r'terminat', content, re.IGNORECASE):
            key_terms.append({
                'term': 'termination_clause',
                'value': 'Present',
                'importance': 'high'
            })
        
        # Extract liability terms
        if re.search(r'liabilit', content, re.IGNORECASE):
            key_terms.append({
                'term': 'liability',
                'value': 'Specified',
                'importance': 'medium'
            })
        
        return key_terms
    
    def _identify_contract_risks(self, content: str) -> List[Dict[str, Any]]:
        """Identify potential risks in contract"""
        risks = []
        
        # Check for missing key clauses
        if not re.search(r'terminat', content, re.IGNORECASE):
            risks.append({
                'risk': 'missing_termination_clause',
                'severity': 'high',
                'description': 'No termination clause found'
            })
        
        if not re.search(r'liabilit', content, re.IGNORECASE):
            risks.append({
                'risk': 'missing_liability_clause',
                'severity': 'medium',
                'description': 'No liability clause found'
            })
        
        # Check for unfavorable payment terms
        payment_match = re.search(r'payment.*?(\d+)\s*days?', content, re.IGNORECASE)
        if payment_match and int(payment_match.group(1)) > 90:
            risks.append({
                'risk': 'extended_payment_terms',
                'severity': 'medium',
                'description': f'Payment terms exceed 90 days'
            })
        
        # Check for penalty clauses
        if re.search(r'penalt|fine', content, re.IGNORECASE):
            risks.append({
                'risk': 'penalty_clause_present',
                'severity': 'low',
                'description': 'Contract contains penalty clauses'
            })
        
        return risks
    
    def _generate_summary_text(self, content: str) -> str:
        """Generate summary text for contract"""
        # Simple summary generation (in production, use Amazon Bedrock)
        word_count = len(content.split())
        
        summary_parts = []
        
        if re.search(r'supply|deliver', content, re.IGNORECASE):
            summary_parts.append("Supply/delivery agreement")
        
        if re.search(r'service', content, re.IGNORECASE):
            summary_parts.append("Service contract")
        
        payment_match = re.search(r'payment.*?(\d+)\s*days?', content, re.IGNORECASE)
        if payment_match:
            summary_parts.append(f"Payment terms: {payment_match.group(1)} days")
        
        duration_match = re.search(r'(?:term|duration).*?(\d+)\s*(year|month)', content, re.IGNORECASE)
        if duration_match:
            summary_parts.append(f"Duration: {duration_match.group(1)} {duration_match.group(2)}s")
        
        if summary_parts:
            return f"Contract summary: {', '.join(summary_parts)}. Document length: {word_count} words."
        else:
            return f"Contract document with {word_count} words. Detailed analysis required."

    def generate_compliance_alert(
        self, 
        alert_type: str, 
        severity: str, 
        description: str,
        remediation: str
    ) -> Dict[str, Any]:
        """
        Generate compliance alert with remediation recommendation
        
        Args:
            alert_type: Type of compliance alert
            severity: Severity level (low, medium, high, critical)
            description: Description of the violation
            remediation: Recommended remediation action
            
        Returns:
            Alert dictionary
        """
        return {
            'alert_id': f"alert-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            'alert_type': alert_type,
            'severity': severity,
            'description': description,
            'remediation': remediation,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'open'
        }
    
    def _generate_compliance_alerts(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate compliance alerts from analysis results"""
        alerts = []
        
        # Check document processing results
        for doc_result in results.get('document_processing', []):
            validation = doc_result.get('validation', {})
            if not validation.get('is_valid', True):
                alerts.append(self.generate_compliance_alert(
                    alert_type='document_validation_failure',
                    severity='high',
                    description=f"Document {doc_result['document_id']} failed validation: {', '.join(validation.get('errors', []))}",
                    remediation='Review and correct document data, resubmit for validation'
                ))
            
            # Check accuracy threshold
            if doc_result.get('accuracy', 1.0) < 0.95:
                alerts.append(self.generate_compliance_alert(
                    alert_type='low_extraction_accuracy',
                    severity='medium',
                    description=f"Document {doc_result['document_id']} extraction accuracy below threshold: {doc_result.get('accuracy', 0):.2%}",
                    remediation='Manual review recommended to verify extracted data'
                ))
        
        # Check supplier risk scores
        for supplier_score in results.get('supplier_risk_scores', []):
            if supplier_score.get('risk_level') == 'high':
                alerts.append(self.generate_compliance_alert(
                    alert_type='high_supplier_risk',
                    severity='high',
                    description=f"Supplier {supplier_score['supplier_name']} has high risk score: {supplier_score['risk_score']:.2f}",
                    remediation=supplier_score.get('recommendation', 'Conduct detailed supplier audit')
                ))
        
        # Check fraud detection results
        fraud_results = results.get('fraud_detection', {})
        for fraud_alert in fraud_results.get('fraud_alerts', []):
            alerts.append(self.generate_compliance_alert(
                alert_type=f"fraud_{fraud_alert['type']}",
                severity=fraud_alert.get('severity', 'high'),
                description=f"Fraud pattern detected: {fraud_alert['type']}",
                remediation='Investigate transaction immediately and suspend if necessary'
            ))
        
        return alerts
    
    def _calculate_confidence(self, results: Dict[str, Any]) -> float:
        """Calculate overall confidence in risk assessment"""
        confidences = []
        
        # Document processing confidence
        for doc_result in results.get('document_processing', []):
            confidences.append(doc_result.get('accuracy', 0.0))
        
        # Supplier scoring confidence (based on data availability)
        for supplier_score in results.get('supplier_risk_scores', []):
            # Higher confidence with more complete risk factor data
            risk_factors = supplier_score.get('risk_factors', {})
            non_neutral = sum(1 for v in risk_factors.values() if v != 0.5)
            confidence = 0.7 + (non_neutral / len(risk_factors)) * 0.25 if risk_factors else 0.5
            confidences.append(confidence)
        
        # Fraud detection confidence (based on sample size)
        fraud_results = results.get('fraud_detection', {})
        anomaly_count = len(fraud_results.get('anomalies', []))
        if anomaly_count > 0:
            confidences.append(0.85)
        
        return statistics.mean(confidences) if confidences else 0.5

    def persist_risk_intelligence(self, results: Dict[str, Any], confidence: float):
        """
        Persist risk and compliance intelligence to DynamoDB and S3
        
        Args:
            results: Risk analysis results
            confidence: Confidence level of the analysis
        """
        timestamp = datetime.now(timezone.utc)
        
        # Convert floats to Decimals for DynamoDB
        results_for_db = self._convert_floats_to_decimals(results)
        
        # Persist risk intelligence
        risk_entity = BusinessIntelligence(
            entity_type=EntityType.RISK,
            entity_id=f"risk-{timestamp.strftime('%Y%m%d-%H%M%S')}",
            insights=Insights(
                trend='Risk and compliance analysis',
                prediction=results_for_db,
                confidence=Decimal(str(confidence)),
                timeframe='current'
            ),
            recommendations=self._create_risk_recommendations(results),
            data_source=['risk_compliance_agent']
        )
        self.bi_repository.create(risk_entity)
        
        # Store detailed results in S3
        s3_key = f"risk-compliance/{timestamp.strftime('%Y/%m/%d')}/{timestamp.strftime('%H%M%S')}-analysis.json"
        self.s3_repository.upload_json(
            data={
                'timestamp': timestamp.isoformat(),
                'results': results,
                'confidence': confidence
            },
            s3_key=s3_key,
            metadata={
                'agent_id': self.metadata.agent_id,
                'analysis_date': timestamp.strftime('%Y-%m-%d')
            }
        )
    
    def _convert_floats_to_decimals(self, obj: Any) -> Any:
        """
        Recursively convert float values to Decimal for DynamoDB compatibility
        
        Args:
            obj: Object to convert
            
        Returns:
            Object with floats converted to Decimals
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._convert_floats_to_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_floats_to_decimals(item) for item in obj]
        else:
            return obj
    
    def _create_risk_recommendations(self, results: Dict[str, Any]) -> List[ActionRecommendation]:
        """Create action recommendations from risk analysis"""
        recommendations = []
        
        # Document-related recommendations
        doc_issues = sum(1 for doc in results.get('document_processing', [])
                        if not doc.get('validation', {}).get('is_valid', True))
        if doc_issues > 0:
            recommendations.append(ActionRecommendation(
                action=f'Review and correct {doc_issues} document validation failures',
                priority=Priority.HIGH,
                expected_impact='Improved compliance and reduced processing errors'
            ))
        
        # Supplier-related recommendations
        high_risk_suppliers = sum(1 for s in results.get('supplier_risk_scores', [])
                                 if s.get('risk_level') == 'high')
        if high_risk_suppliers > 0:
            recommendations.append(ActionRecommendation(
                action=f'Conduct detailed audit of {high_risk_suppliers} high-risk suppliers',
                priority=Priority.HIGH,
                expected_impact='Reduced supplier-related risks and improved supply chain reliability'
            ))
        
        # Fraud-related recommendations
        fraud_alerts = len(results.get('fraud_detection', {}).get('fraud_alerts', []))
        if fraud_alerts > 0:
            recommendations.append(ActionRecommendation(
                action=f'Investigate {fraud_alerts} fraud alerts immediately',
                priority=Priority.CRITICAL,
                expected_impact='Prevention of financial losses and compliance violations'
            ))
        
        if not recommendations:
            recommendations.append(ActionRecommendation(
                action='Continue standard risk monitoring procedures',
                priority=Priority.LOW,
                expected_impact='Maintained compliance and risk awareness'
            ))
        
        return recommendations
    
    def handle_message(self, message: ACPMessage) -> Optional[Dict[str, Any]]:
        """
        Handle incoming messages from other agents or AI Council
        
        Args:
            message: ACPMessage to handle
            
        Returns:
            Response payload if applicable
        """
        if message.message_type == MessageType.REQUEST:
            return self._handle_risk_request(message)
        elif message.message_type == MessageType.BROADCAST:
            return self._handle_broadcast(message)
        elif message.message_type == MessageType.NOTIFICATION:
            return self._handle_notification(message)
        else:
            print(f"Unknown message type: {message.message_type}")
            return None
    
    def _handle_risk_request(self, message: ACPMessage) -> Dict[str, Any]:
        """Handle request for risk intelligence data"""
        request_type = message.payload.get('request_type')
        
        if request_type == 'supplier_risk':
            entities = self.bi_repository.get_by_type(EntityType.RISK.value, limit=10)
            return {
                'status': 'success',
                'data': [entity.to_dict() for entity in entities]
            }
        else:
            return {
                'status': 'error',
                'message': f'Unknown request type: {request_type}'
            }
    
    def _handle_broadcast(self, message: ACPMessage) -> Dict[str, Any]:
        """Handle broadcast messages from AI Council"""
        print(f"Received broadcast from {message.agent_id}: {message.payload}")
        return {'status': 'acknowledged'}
    
    def _handle_notification(self, message: ACPMessage) -> Dict[str, Any]:
        """Handle notification messages"""
        print(f"Received notification from {message.agent_id}: {message.payload}")
        return {'status': 'acknowledged'}
