/**
 * AWS Amplify Configuration
 */

export const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_USER_POOL_ID || '',
      userPoolClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID || '',
      region: import.meta.env.VITE_AWS_REGION || 'us-east-1',
    }
  },
  API: {
    REST: {
      RetailMindAPI: {
        endpoint: import.meta.env.VITE_API_GATEWAY_URL || '',
        region: import.meta.env.VITE_AWS_REGION || 'us-east-1',
      }
    }
  }
};
