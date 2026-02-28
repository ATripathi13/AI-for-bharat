/**
 * Core type definitions for RetailMind AI
 */

export interface AgentDecision {
  agentId: string;
  decisionId: string;
  timestamp: Date;
  inputData: any;
  recommendation: {
    action: string;
    confidence: number;
    reasoning: string;
    supportingData: any[];
  };
  escalationRequired: boolean;
}

export interface WorkflowInstance {
  workflowId: string;
  instanceId: string;
  status: 'running' | 'completed' | 'failed' | 'rolled_back';
  steps: WorkflowStep[];
  createdBy: 'system' | 'human';
  generatedBy: string;
  performance: {
    executionTime: number;
    successRate: number;
    businessImpact: number;
  };
}

export interface WorkflowStep {
  stepId: string;
  type: 'lambda' | 'decision' | 'parallel';
  configuration: any;
  conditions: any;
}

export interface BusinessIntelligence {
  entityType: 'pricing' | 'demand' | 'inventory' | 'risk';
  entityId: string;
  insights: {
    trend: string;
    prediction: any;
    confidence: number;
    timeframe: string;
  };
  recommendations: ActionRecommendation[];
  dataSource: string[];
}

export interface ActionRecommendation {
  action: string;
  priority: 'high' | 'medium' | 'low';
  expectedImpact: string;
}
