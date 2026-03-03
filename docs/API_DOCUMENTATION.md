# RetailMind AI - API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URLs](#base-urls)
4. [Common Headers](#common-headers)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [API Endpoints](#api-endpoints)
8. [WebSocket API](#websocket-api)
9. [Data Models](#data-models)

## Overview

RetailMind AI provides RESTful APIs and WebSocket connections for interacting with the multi-agent decision intelligence platform. All APIs are secured with Amazon Cognito authentication and follow REST best practices.

### API Features
- RESTful design principles
- JSON request/response format
- JWT-based authentication
- Rate limiting and throttling
- Comprehensive error messages
- Request/response validation

## Authentication

### Cognito Authentication

All API requests require authentication using JWT tokens from Amazon Cognito.

#### Obtaining Access Token

**Endpoint**: `POST /auth/login`

**Request**:
```json
{
  "username": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response**:
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "idToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expiresIn": 3600,
  "tokenType": "Bearer"
}
```

#### Refreshing Access Token

**Endpoint**: `POST /auth/refresh`

**Request**:
```json
{
  "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**:
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expiresIn": 3600,
  "tokenType": "Bearer"
}
```

## Base URLs

### Production
```
https://api.retailmind.ai/v1
```

### Staging
```
https://api-staging.retailmind.ai/v1
```

### Development
```
https://api-dev.retailmind.ai/v1
```

## Common Headers

All API requests should include the following headers:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
X-API-Version: 1.0
X-Request-ID: <unique_request_id>
```

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional error context"
    },
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

### HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid or missing token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Common Error Codes

| Error Code | Description |
|------------|-------------|
| `INVALID_TOKEN` | JWT token is invalid or expired |
| `MISSING_PARAMETER` | Required parameter is missing |
| `INVALID_PARAMETER` | Parameter value is invalid |
| `RESOURCE_NOT_FOUND` | Requested resource doesn't exist |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `AGENT_UNAVAILABLE` | AI agent is temporarily unavailable |
| `WORKFLOW_FAILED` | Workflow execution failed |
| `INSUFFICIENT_CONFIDENCE` | Decision confidence below threshold |

## Rate Limiting

### Limits

| Tier | Requests per Second | Requests per Day |
|------|---------------------|------------------|
| Free | 10 | 10,000 |
| Basic | 50 | 100,000 |
| Professional | 200 | 1,000,000 |
| Enterprise | Custom | Custom |

### Rate Limit Headers

```http
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1709467800
```

## API Endpoints

### 1. Market Intelligence

#### Get Pricing Trends

**Endpoint**: `GET /market-intelligence/pricing-trends`

**Query Parameters**:
- `region` (optional): Filter by region
- `category` (optional): Filter by product category
- `startDate` (optional): Start date (ISO 8601)
- `endDate` (optional): End date (ISO 8601)

**Response**:
```json
{
  "data": {
    "trends": [
      {
        "productId": "SKU123",
        "productName": "Product Name",
        "category": "Electronics",
        "region": "North",
        "currentPrice": 999.99,
        "priceChange": -5.2,
        "priceChangePercent": -0.52,
        "trend": "decreasing",
        "competitorPrices": [
          {
            "competitor": "Competitor A",
            "price": 989.99
          }
        ],
        "timestamp": "2026-03-03T10:30:00Z"
      }
    ],
    "summary": {
      "totalProducts": 150,
      "averagePriceChange": -2.3,
      "trendingUp": 45,
      "trendingDown": 105
    }
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

#### Get Demand Heatmap

**Endpoint**: `GET /market-intelligence/demand-heatmap`

**Query Parameters**:
- `region` (optional): Filter by region
- `category` (optional): Filter by product category

**Response**:
```json
{
  "data": {
    "heatmap": [
      {
        "region": "North",
        "category": "Electronics",
        "demandScore": 8.5,
        "demandLevel": "high",
        "topProducts": [
          {
            "productId": "SKU123",
            "productName": "Product Name",
            "demandScore": 9.2
          }
        ]
      }
    ]
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

### 2. Demand Forecasting

#### Get Demand Forecast

**Endpoint**: `GET /demand-forecast/{sku}`

**Path Parameters**:
- `sku`: Product SKU

**Query Parameters**:
- `region` (optional): Filter by region
- `days` (optional): Forecast period in days (default: 30)

**Response**:
```json
{
  "data": {
    "sku": "SKU123",
    "productName": "Product Name",
    "forecasts": [
      {
        "date": "2026-03-04",
        "predictedDemand": 150,
        "confidence": 0.87,
        "lowerBound": 130,
        "upperBound": 170,
        "region": "North"
      }
    ],
    "accuracy": {
      "last30Days": 0.89,
      "last90Days": 0.85
    },
    "seasonalFactors": {
      "isSeasonal": true,
      "peakSeason": "December",
      "seasonalityStrength": 0.75
    }
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z",
    "modelVersion": "v2.3.1"
  }
}
```

#### Get Regional Forecasts

**Endpoint**: `GET /demand-forecast/regional`

**Query Parameters**:
- `category` (optional): Filter by product category
- `days` (optional): Forecast period in days (default: 30)

**Response**:
```json
{
  "data": {
    "regions": [
      {
        "region": "North",
        "totalPredictedDemand": 15000,
        "confidence": 0.85,
        "topProducts": [
          {
            "sku": "SKU123",
            "predictedDemand": 1500,
            "confidence": 0.87
          }
        ]
      }
    ]
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

### 3. Pricing Optimization

#### Get Price Recommendations

**Endpoint**: `GET /pricing/recommendations`

**Query Parameters**:
- `sku` (optional): Filter by SKU
- `category` (optional): Filter by category
- `minMargin` (optional): Minimum margin percentage

**Response**:
```json
{
  "data": {
    "recommendations": [
      {
        "sku": "SKU123",
        "productName": "Product Name",
        "currentPrice": 999.99,
        "recommendedPrice": 949.99,
        "priceChange": -50.00,
        "priceChangePercent": -5.0,
        "reasoning": "Competitive pressure from 3 competitors",
        "confidence": 0.92,
        "expectedImpact": {
          "demandIncrease": 15.5,
          "revenueChange": 8.2,
          "marginChange": -2.1
        },
        "competitorAnalysis": {
          "lowestCompetitorPrice": 939.99,
          "averageCompetitorPrice": 959.99,
          "pricePosition": "above_average"
        }
      }
    ]
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

#### Simulate Price Change

**Endpoint**: `POST /pricing/simulate`

**Request**:
```json
{
  "sku": "SKU123",
  "proposedPrice": 949.99,
  "duration": 30
}
```

**Response**:
```json
{
  "data": {
    "simulation": {
      "sku": "SKU123",
      "currentPrice": 999.99,
      "proposedPrice": 949.99,
      "priceChange": -50.00,
      "elasticity": 1.8,
      "projections": {
        "demandChange": 18.5,
        "revenueChange": 12.3,
        "marginChange": -3.2,
        "profitChange": 8.7
      },
      "risks": [
        {
          "type": "margin_compression",
          "severity": "medium",
          "description": "Margin will decrease by 3.2%"
        }
      ],
      "confidence": 0.88
    }
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

### 4. Inventory Planning

#### Get Inventory Status

**Endpoint**: `GET /inventory/status`

**Query Parameters**:
- `region` (optional): Filter by region
- `status` (optional): Filter by status (overstock, stockout, optimal)

**Response**:
```json
{
  "data": {
    "inventory": [
      {
        "sku": "SKU123",
        "productName": "Product Name",
        "region": "North",
        "currentStock": 50,
        "optimalStock": 150,
        "status": "stockout_risk",
        "daysOfStock": 5,
        "reorderPoint": 100,
        "recommendation": {
          "action": "reorder",
          "quantity": 200,
          "urgency": "high",
          "reasoning": "Stock will run out in 5 days based on demand forecast"
        }
      }
    ],
    "summary": {
      "totalSKUs": 500,
      "overstockCount": 45,
      "stockoutRiskCount": 78,
      "optimalCount": 377
    }
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

#### Get Reorder Recommendations

**Endpoint**: `GET /inventory/reorder-recommendations`

**Query Parameters**:
- `region` (optional): Filter by region
- `urgency` (optional): Filter by urgency (high, medium, low)

**Response**:
```json
{
  "data": {
    "recommendations": [
      {
        "sku": "SKU123",
        "productName": "Product Name",
        "region": "North",
        "currentStock": 50,
        "recommendedOrderQuantity": 200,
        "urgency": "high",
        "estimatedStockoutDate": "2026-03-08",
        "leadTime": 7,
        "confidence": 0.91
      }
    ]
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

### 5. Risk & Compliance

#### Upload Document

**Endpoint**: `POST /risk-compliance/documents`

**Request** (multipart/form-data):
```
file: <binary_file>
documentType: invoice|gst|contract
metadata: {
  "supplierId": "SUP123",
  "documentDate": "2026-03-01"
}
```

**Response**:
```json
{
  "data": {
    "documentId": "DOC123456",
    "status": "processing",
    "estimatedCompletionTime": "2026-03-03T10:35:00Z"
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

#### Get Document Analysis

**Endpoint**: `GET /risk-compliance/documents/{documentId}`

**Response**:
```json
{
  "data": {
    "documentId": "DOC123456",
    "documentType": "invoice",
    "status": "completed",
    "extractedData": {
      "invoiceNumber": "INV-2026-001",
      "invoiceDate": "2026-03-01",
      "supplierName": "Supplier ABC",
      "totalAmount": 50000.00,
      "gstAmount": 9000.00,
      "items": [
        {
          "description": "Product A",
          "quantity": 100,
          "unitPrice": 500.00,
          "amount": 50000.00
        }
      ]
    },
    "validation": {
      "isValid": true,
      "confidence": 0.96,
      "issues": []
    },
    "riskAssessment": {
      "riskScore": 0.15,
      "riskLevel": "low",
      "factors": [
        {
          "factor": "supplier_history",
          "score": 0.1,
          "description": "Supplier has good payment history"
        }
      ]
    }
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

#### Get Fraud Alerts

**Endpoint**: `GET /risk-compliance/fraud-alerts`

**Query Parameters**:
- `severity` (optional): Filter by severity (high, medium, low)
- `status` (optional): Filter by status (open, investigating, resolved)

**Response**:
```json
{
  "data": {
    "alerts": [
      {
        "alertId": "ALERT123",
        "type": "anomalous_transaction",
        "severity": "high",
        "status": "open",
        "description": "Unusual transaction pattern detected",
        "details": {
          "transactionId": "TXN123456",
          "amount": 100000.00,
          "anomalyScore": 0.92,
          "patterns": [
            "Amount 10x higher than average",
            "Transaction outside business hours"
          ]
        },
        "recommendedActions": [
          "Verify transaction with customer",
          "Review transaction details",
          "Contact fraud prevention team"
        ],
        "timestamp": "2026-03-03T10:25:00Z"
      }
    ]
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

### 6. Business Copilot

#### Submit Query

**Endpoint**: `POST /copilot/query`

**Request**:
```json
{
  "query": "What are the top 5 products with declining sales in the North region?",
  "context": {
    "sessionId": "SESSION123",
    "userId": "USER123"
  }
}
```

**Response**:
```json
{
  "data": {
    "queryId": "QUERY123",
    "response": {
      "answer": "Based on the latest sales data, here are the top 5 products with declining sales in the North region...",
      "insights": [
        {
          "type": "trend",
          "description": "Product A sales declined by 15% in the last 30 days",
          "confidence": 0.92
        }
      ],
      "recommendations": [
        {
          "action": "Consider price reduction for Product A",
          "reasoning": "Competitor prices are 10% lower",
          "expectedImpact": "15% increase in sales"
        }
      ],
      "dataSource": [
        "Sales data (last 90 days)",
        "Market intelligence",
        "Competitor pricing"
      ],
      "explainability": {
        "reasoning": "Analysis based on sales trends, market conditions, and competitor activity",
        "confidence": 0.89,
        "agentsConsulted": [
          "Market Intelligence Agent",
          "Demand Forecast Agent"
        ]
      }
    }
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z",
    "processingTime": 2.3
  }
}
```

#### Get Conversation History

**Endpoint**: `GET /copilot/conversations/{sessionId}`

**Response**:
```json
{
  "data": {
    "sessionId": "SESSION123",
    "userId": "USER123",
    "startTime": "2026-03-03T10:00:00Z",
    "messages": [
      {
        "messageId": "MSG001",
        "role": "user",
        "content": "What are the top 5 products with declining sales?",
        "timestamp": "2026-03-03T10:00:00Z"
      },
      {
        "messageId": "MSG002",
        "role": "assistant",
        "content": "Based on the latest sales data...",
        "timestamp": "2026-03-03T10:00:02Z"
      }
    ]
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

### 7. Workflows

#### List Workflows

**Endpoint**: `GET /workflows`

**Query Parameters**:
- `status` (optional): Filter by status (active, completed, failed)
- `type` (optional): Filter by workflow type

**Response**:
```json
{
  "data": {
    "workflows": [
      {
        "workflowId": "WF123",
        "name": "Price Optimization Workflow",
        "version": "1.2.0",
        "status": "active",
        "createdBy": "system",
        "createdAt": "2026-03-01T10:00:00Z",
        "lastModified": "2026-03-03T09:00:00Z",
        "performance": {
          "executionCount": 150,
          "successRate": 0.98,
          "averageExecutionTime": 45.2
        }
      }
    ]
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

#### Get Workflow Details

**Endpoint**: `GET /workflows/{workflowId}`

**Response**:
```json
{
  "data": {
    "workflowId": "WF123",
    "name": "Price Optimization Workflow",
    "version": "1.2.0",
    "status": "active",
    "definition": {
      "steps": [
        {
          "stepId": "step1",
          "name": "Analyze Market Data",
          "type": "lambda",
          "configuration": {
            "functionName": "market-analysis"
          }
        }
      ]
    },
    "performance": {
      "executionCount": 150,
      "successRate": 0.98,
      "averageExecutionTime": 45.2,
      "lastExecution": "2026-03-03T10:25:00Z"
    }
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

#### Trigger Workflow

**Endpoint**: `POST /workflows/{workflowId}/execute`

**Request**:
```json
{
  "input": {
    "sku": "SKU123",
    "region": "North"
  },
  "priority": "high"
}
```

**Response**:
```json
{
  "data": {
    "executionId": "EXEC123",
    "workflowId": "WF123",
    "status": "running",
    "startTime": "2026-03-03T10:30:00Z",
    "estimatedCompletionTime": "2026-03-03T10:31:00Z"
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

### 8. Audit & Monitoring

#### Get Audit Trail

**Endpoint**: `GET /audit/trail`

**Query Parameters**:
- `startDate` (optional): Start date (ISO 8601)
- `endDate` (optional): End date (ISO 8601)
- `agentId` (optional): Filter by agent
- `eventType` (optional): Filter by event type

**Response**:
```json
{
  "data": {
    "events": [
      {
        "eventId": "EVT123",
        "eventType": "agent_decision",
        "agentId": "pricing-agent",
        "timestamp": "2026-03-03T10:25:00Z",
        "details": {
          "decision": "price_change",
          "sku": "SKU123",
          "oldPrice": 999.99,
          "newPrice": 949.99,
          "confidence": 0.92,
          "reasoning": "Competitive pressure"
        },
        "userId": "SYSTEM",
        "outcome": "success"
      }
    ],
    "pagination": {
      "total": 1000,
      "page": 1,
      "pageSize": 50,
      "hasMore": true
    }
  },
  "metadata": {
    "requestId": "req_123456789",
    "timestamp": "2026-03-03T10:30:00Z"
  }
}
```

## WebSocket API

### Connection

**Endpoint**: `wss://ws.retailmind.ai/v1`

**Connection Parameters**:
```
?token=<access_token>
```

### Message Format

**Client to Server**:
```json
{
  "action": "subscribe|unsubscribe|query",
  "channel": "alerts|copilot|dashboard",
  "payload": {}
}
```

**Server to Client**:
```json
{
  "type": "alert|message|update",
  "channel": "alerts|copilot|dashboard",
  "data": {},
  "timestamp": "2026-03-03T10:30:00Z"
}
```

### Channels

#### Alerts Channel
Receive real-time alerts and notifications.

**Subscribe**:
```json
{
  "action": "subscribe",
  "channel": "alerts",
  "payload": {
    "severity": ["high", "medium"]
  }
}
```

**Alert Message**:
```json
{
  "type": "alert",
  "channel": "alerts",
  "data": {
    "alertId": "ALERT123",
    "severity": "high",
    "message": "Stockout risk detected for SKU123",
    "details": {}
  },
  "timestamp": "2026-03-03T10:30:00Z"
}
```

#### Copilot Channel
Real-time Business Copilot chat.

**Send Query**:
```json
{
  "action": "query",
  "channel": "copilot",
  "payload": {
    "query": "What are today's top selling products?",
    "sessionId": "SESSION123"
  }
}
```

**Response**:
```json
{
  "type": "message",
  "channel": "copilot",
  "data": {
    "queryId": "QUERY123",
    "response": "Based on today's sales data...",
    "insights": [],
    "recommendations": []
  },
  "timestamp": "2026-03-03T10:30:02Z"
}
```

## Data Models

### AgentDecision
```typescript
interface AgentDecision {
  agentId: string;
  decisionId: string;
  timestamp: string; // ISO 8601
  inputData: any;
  recommendation: {
    action: string;
    confidence: number; // 0-1
    reasoning: string;
    supportingData: any[];
  };
  escalationRequired: boolean;
}
```

### WorkflowInstance
```typescript
interface WorkflowInstance {
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
```

### BusinessIntelligence
```typescript
interface BusinessIntelligence {
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
```

## SDK Examples

### Python SDK

```python
from retailmind import RetailMindClient

# Initialize client
client = RetailMindClient(
    api_key="your_api_key",
    region="us-east-1"
)

# Get pricing trends
trends = client.market_intelligence.get_pricing_trends(
    region="North",
    category="Electronics"
)

# Get demand forecast
forecast = client.demand_forecast.get_forecast(
    sku="SKU123",
    days=30
)

# Submit copilot query
response = client.copilot.query(
    "What are the top selling products today?"
)
```

### JavaScript SDK

```javascript
import { RetailMindClient } from '@retailmind/sdk';

// Initialize client
const client = new RetailMindClient({
  apiKey: 'your_api_key',
  region: 'us-east-1'
});

// Get pricing trends
const trends = await client.marketIntelligence.getPricingTrends({
  region: 'North',
  category: 'Electronics'
});

// Get demand forecast
const forecast = await client.demandForecast.getForecast({
  sku: 'SKU123',
  days: 30
});

// Submit copilot query
const response = await client.copilot.query(
  'What are the top selling products today?'
);
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-03  
**API Version**: v1  
**Maintained By**: RetailMind AI API Team
