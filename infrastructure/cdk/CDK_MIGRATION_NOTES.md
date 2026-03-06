# AWS CDK v2 Migration Notes

## What Changed

This project uses **AWS CDK v2** (aws-cdk-lib 2.120.0), which consolidates all AWS service modules into a single package.

## Key Differences from CDK v1

### Dependencies

**CDK v1 (Old - Don't use)**:
```txt
aws-cdk.core==1.204.0
aws-cdk.aws-s3==1.204.0
aws-cdk.aws-lambda==1.204.0
aws-cdk.aws-dynamodb==1.204.0
# ... separate packages for each service
```

**CDK v2 (Current - Use this)**:
```txt
aws-cdk-lib==2.120.0
constructs>=10.0.0,<11.0.0
```

### Import Statements

**CDK v1 (Old)**:
```python
from aws_cdk import core
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_lambda as lambda_
```

**CDK v2 (Current)**:
```python
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as lambda_,
    Duration,
    RemovalPolicy
)
from constructs import Construct
```

### Stack Definition

**CDK v1 (Old)**:
```python
from aws_cdk import core

class MyStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
```

**CDK v2 (Current)**:
```python
from aws_cdk import Stack
from constructs import Construct

class MyStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
```

## Installation

### Clean Install
```powershell
# Remove old virtual environment
Remove-Item -Recurse -Force venv

# Create new virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Troubleshooting

#### Issue: Dependency Conflicts
If you see errors about conflicting dependencies between `aws-cdk-lib` and `aws-cdk.aws-*` packages:

**Solution**: Remove all CDK v1 packages from requirements.txt. Only keep:
```txt
aws-cdk-lib==2.120.0
constructs>=10.0.0,<11.0.0
```

#### Issue: Import Errors
If you see `ModuleNotFoundError: No module named 'aws_cdk.core'`:

**Solution**: Update imports to use CDK v2 syntax:
```python
# Change this:
from aws_cdk import core

# To this:
from aws_cdk import Stack
from constructs import Construct
```

#### Issue: Construct Type Errors
If you see errors about `Construct` type:

**Solution**: Import `Construct` from `constructs` package, not from `aws_cdk`:
```python
from constructs import Construct  # Correct
# NOT: from aws_cdk import Construct
```

## Benefits of CDK v2

1. **Simpler Dependencies**: Single package instead of 100+ separate packages
2. **Faster Installation**: Fewer packages to download and install
3. **Better Type Hints**: Improved IDE support and autocomplete
4. **Stable API**: Fewer breaking changes between versions
5. **Better Documentation**: Consolidated documentation

## Migration Checklist

- [x] Updated requirements.txt to use aws-cdk-lib
- [x] Removed CDK v1 packages
- [x] Updated all stack files to use CDK v2 imports
- [x] Updated app.py to use CDK v2 syntax
- [x] Verified all imports use `from constructs import Construct`
- [x] Tested CDK synth command
- [x] Tested CDK deploy command

## Useful Commands

```powershell
# Verify CDK version
cdk --version

# Synthesize CloudFormation templates
cdk synth

# Show differences
cdk diff

# Deploy all stacks
cdk deploy --all

# Destroy all stacks
cdk destroy --all

# List all stacks
cdk list
```

## References

- [AWS CDK v2 Migration Guide](https://docs.aws.amazon.com/cdk/v2/guide/migrating-v2.html)
- [AWS CDK v2 API Reference](https://docs.aws.amazon.com/cdk/api/v2/)
- [AWS CDK v2 Examples](https://github.com/aws-samples/aws-cdk-examples)

---

**Last Updated**: 2026-03-06  
**CDK Version**: 2.120.0
