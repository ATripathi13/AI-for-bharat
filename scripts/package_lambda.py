#!/usr/bin/env python3
"""
Lambda Function Packaging Script

Packages Python Lambda functions with dependencies for deployment.
"""

import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import List


class LambdaPackager:
    """Package Lambda functions for deployment"""
    
    def __init__(self, source_dir: str = "backend/src", output_dir: str = "dist/lambda"):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def package_function(self, function_name: str, handler_path: str) -> str:
        """Package a single Lambda function"""
        print(f"Packaging {function_name}...")
        
        # Create temporary directory
        temp_dir = self.output_dir / f"temp_{function_name}"
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # Copy source code
            self._copy_source_code(temp_dir)
            
            # Install dependencies
            self._install_dependencies(temp_dir)
            
            # Create ZIP file
            zip_path = self.output_dir / f"{function_name}.zip"
            self._create_zip(temp_dir, zip_path)
            
            print(f"✓ {function_name} packaged: {zip_path}")
            return str(zip_path)
            
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _copy_source_code(self, dest_dir: Path):
        """Copy source code to temporary directory"""
        # Copy all Python files
        for py_file in self.source_dir.rglob("*.py"):
            rel_path = py_file.relative_to(self.source_dir)
            dest_file = dest_dir / rel_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(py_file, dest_file)
    
    def _install_dependencies(self, dest_dir: Path):
        """Install Python dependencies"""
        requirements_file = Path("backend/requirements.txt")
        
        if not requirements_file.exists():
            print("No requirements.txt found, skipping dependencies")
            return
        
        print("Installing dependencies...")
        result = subprocess.run(
            [
                "pip", "install",
                "-r", str(requirements_file),
                "-t", str(dest_dir),
                "--upgrade",
                "--no-cache-dir"
            ],
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"\nPip install failed with error:\n{result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    
    def _create_zip(self, source_dir: Path, zip_path: Path):
        """Create ZIP file from directory"""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
    
    def package_all_functions(self) -> List[str]:
        """Package all Lambda functions"""
        functions = [
            ("market-intelligence-agent", "agents/market_intelligence_agent.py"),
            ("demand-forecast-agent", "agents/demand_forecast_agent.py"),
            ("pricing-optimization-agent", "agents/pricing_optimization_agent.py"),
            ("inventory-planning-agent", "agents/inventory_planning_agent.py"),
            ("risk-compliance-agent", "agents/risk_compliance_agent.py"),
            ("business-copilot-agent", "agents/business_copilot_agent.py"),
            ("workflow-regeneration-agent", "agents/workflow_regeneration_agent.py"),
        ]
        
        packaged_functions = []
        
        for function_name, handler_path in functions:
            try:
                zip_path = self.package_function(function_name, handler_path)
                packaged_functions.append(zip_path)
            except Exception as e:
                print(f"✗ Failed to package {function_name}: {e}")
        
        return packaged_functions


def main():
    packager = LambdaPackager()
    packaged = packager.package_all_functions()
    
    print(f"\n✓ Packaged {len(packaged)} Lambda functions")
    print(f"Output directory: {packager.output_dir}")


if __name__ == "__main__":
    main()
