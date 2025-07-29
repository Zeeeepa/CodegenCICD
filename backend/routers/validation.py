from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import os
from datetime import datetime

from ..database import get_db
from ..models.project import Project
from ..models.settings import EnvironmentVariable, ValidationRun, ValidationStep
from ..services.validation_service import ValidationService

router = APIRouter(prefix="/api/validation", tags=["validation"])

def get_environment_variables(db: Session) -> Dict[str, str]:
    """Get all environment variables from database."""
    env_vars = {}
    
    # Get from database
    db_vars = db.query(EnvironmentVariable).all()
    for var in db_vars:
        env_vars[var.key] = var.get_value()
    
    # Fallback to OS environment
    required_vars = [
        "CODEGEN_ORG_ID", "CODEGEN_API_TOKEN", "GITHUB_TOKEN", 
        "GEMINI_API_KEY", "CLOUDFLARE_API_KEY", "CLOUDFLARE_ACCOUNT_ID",
        "GRAINCHAIN_URL", "GRAPH_SITTER_URL", "WEB_EVAL_AGENT_URL"
    ]
    
    for var in required_vars:
        if var not in env_vars:
            env_vars[var] = os.getenv(var, "")
    
    return env_vars

@router.post("/start")
async def start_validation_pipeline(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Start the comprehensive validation pipeline for a PR."""
    try:
        project_id = request.get("project_id")
        pr_number = request.get("pr_number")
        pr_url = request.get("pr_url")
        
        if not all([project_id, pr_number, pr_url]):
            raise HTTPException(
                status_code=400, 
                detail="project_id, pr_number, and pr_url are required"
            )
        
        # Get project details
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get setup commands
        setup_commands = request.get("setup_commands", project.setup_commands or [])
        
        # Get environment variables
        env_vars = get_environment_variables(db)
        
        # Initialize validation service
        validation_service = ValidationService()
        
        # Start validation pipeline
        validation_id = await validation_service.start_validation_pipeline(
            project_id=project_id,
            pr_number=pr_number,
            pr_url=pr_url,
            setup_commands=setup_commands,
            env_vars=env_vars,
            db=db
        )
        
        return {
            "success": True,
            "validation_id": validation_id,
            "message": "Validation pipeline started",
            "project_name": project.name,
            "pr_number": pr_number
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start validation: {str(e)}")

@router.get("/status/{validation_id}")
async def get_validation_status(
    validation_id: str,
    db: Session = Depends(get_db)
):
    """Get the current status of a validation run."""
    try:
        validation_service = ValidationService()
        status = await validation_service.get_validation_status(validation_id, db)
        
        return {
            "success": True,
            "validation": status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get validation status: {str(e)}")

@router.get("/history/{project_id}")
async def get_validation_history(
    project_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get validation history for a project."""
    try:
        validation_runs = db.query(ValidationRun).filter(
            ValidationRun.project_id == project_id
        ).order_by(ValidationRun.started_at.desc()).limit(limit).all()
        
        history = []
        for run in validation_runs:
            # Get steps for this run
            steps = db.query(ValidationStep).filter(
                ValidationStep.validation_id == run.id
            ).all()
            
            history.append({
                "validation_id": run.id,
                "pr_number": run.pr_number,
                "pr_url": run.pr_url,
                "status": run.status,
                "success": run.success,
                "error_context": run.error_context,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "duration": (
                    (run.completed_at - run.started_at).total_seconds()
                    if run.completed_at and run.started_at else None
                ),
                "steps_completed": len([s for s in steps if s.status == "completed"]),
                "total_steps": len(steps)
            })
        
        return {
            "success": True,
            "validation_history": history,
            "total": len(history)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get validation history: {str(e)}")

@router.post("/retry/{validation_id}")
async def retry_validation(
    validation_id: str,
    db: Session = Depends(get_db)
):
    """Retry a failed validation run."""
    try:
        # Get the original validation run
        validation_run = db.query(ValidationRun).filter(
            ValidationRun.id == validation_id
        ).first()
        
        if not validation_run:
            raise HTTPException(status_code=404, detail="Validation run not found")
        
        if validation_run.status not in ["failed", "completed"]:
            raise HTTPException(status_code=400, detail="Can only retry failed or completed validations")
        
        # Get project details
        project = db.query(Project).filter(Project.id == validation_run.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get environment variables
        env_vars = get_environment_variables(db)
        
        # Initialize validation service
        validation_service = ValidationService()
        
        # Start new validation pipeline
        new_validation_id = await validation_service.start_validation_pipeline(
            project_id=validation_run.project_id,
            pr_number=validation_run.pr_number,
            pr_url=validation_run.pr_url,
            setup_commands=project.setup_commands or [],
            env_vars=env_vars,
            db=db
        )
        
        return {
            "success": True,
            "new_validation_id": new_validation_id,
            "original_validation_id": validation_id,
            "message": "Validation retry started"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retry validation: {str(e)}")

@router.delete("/{validation_id}")
async def cancel_validation(
    validation_id: str,
    db: Session = Depends(get_db)
):
    """Cancel a running validation."""
    try:
        validation_run = db.query(ValidationRun).filter(
            ValidationRun.id == validation_id
        ).first()
        
        if not validation_run:
            raise HTTPException(status_code=404, detail="Validation run not found")
        
        if validation_run.status != "running":
            raise HTTPException(status_code=400, detail="Can only cancel running validations")
        
        # Update status to cancelled
        validation_run.status = "cancelled"
        validation_run.completed_at = datetime.utcnow()
        validation_run.error_context = "Validation cancelled by user"
        
        db.commit()
        
        return {
            "success": True,
            "message": "Validation cancelled",
            "validation_id": validation_id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cancel validation: {str(e)}")

@router.get("/logs/{validation_id}")
async def get_validation_logs(
    validation_id: str,
    step_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get logs for a validation run or specific step."""
    try:
        if step_id:
            # Get logs for specific step
            step = db.query(ValidationStep).filter(
                ValidationStep.validation_id == validation_id,
                ValidationStep.step_id == step_id
            ).first()
            
            if not step:
                raise HTTPException(status_code=404, detail="Validation step not found")
            
            return {
                "success": True,
                "step_id": step_id,
                "logs": step.logs or [],
                "error_message": step.error_message,
                "status": step.status
            }
        else:
            # Get logs for all steps
            steps = db.query(ValidationStep).filter(
                ValidationStep.validation_id == validation_id
            ).order_by(ValidationStep.started_at).all()
            
            all_logs = []
            for step in steps:
                step_logs = {
                    "step_id": step.step_id,
                    "status": step.status,
                    "logs": step.logs or [],
                    "error_message": step.error_message,
                    "started_at": step.started_at.isoformat() if step.started_at else None,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None
                }
                all_logs.append(step_logs)
            
            return {
                "success": True,
                "validation_id": validation_id,
                "steps": all_logs
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get validation logs: {str(e)}")

@router.post("/test-services")
async def test_validation_services(db: Session = Depends(get_db)):
    """Test connectivity to all validation services."""
    try:
        env_vars = get_environment_variables(db)
        validation_service = ValidationService()
        
        # Initialize clients
        await validation_service.initialize_clients(env_vars)
        
        test_results = {}
        
        # Test Grainchain
        if validation_service.grainchain_client:
            try:
                await validation_service.grainchain_client.test_connection()
                test_results["grainchain"] = {"status": "success", "message": "Connected"}
            except Exception as e:
                test_results["grainchain"] = {"status": "error", "message": str(e)}
        else:
            test_results["grainchain"] = {"status": "error", "message": "Client not initialized"}
        
        # Test Graph-Sitter
        if validation_service.graph_sitter_client:
            try:
                await validation_service.graph_sitter_client.test_connection()
                test_results["graph_sitter"] = {"status": "success", "message": "Connected"}
            except Exception as e:
                test_results["graph_sitter"] = {"status": "error", "message": str(e)}
        else:
            test_results["graph_sitter"] = {"status": "error", "message": "Client not initialized"}
        
        # Test Web-Eval-Agent
        if validation_service.web_eval_agent_client:
            try:
                await validation_service.web_eval_agent_client.test_connection()
                test_results["web_eval_agent"] = {"status": "success", "message": "Connected"}
            except Exception as e:
                test_results["web_eval_agent"] = {"status": "error", "message": str(e)}
        else:
            test_results["web_eval_agent"] = {"status": "error", "message": "Client not initialized"}
        
        # Test GitHub
        if validation_service.github_client:
            try:
                await validation_service.github_client.test_connection()
                test_results["github"] = {"status": "success", "message": "Connected"}
            except Exception as e:
                test_results["github"] = {"status": "error", "message": str(e)}
        else:
            test_results["github"] = {"status": "error", "message": "Client not initialized"}
        
        # Test Codegen
        if validation_service.codegen_client:
            try:
                await validation_service.codegen_client.test_connection()
                test_results["codegen"] = {"status": "success", "message": "Connected"}
            except Exception as e:
                test_results["codegen"] = {"status": "error", "message": str(e)}
        else:
            test_results["codegen"] = {"status": "error", "message": "Client not initialized"}
        
        # Calculate success rate
        successful_tests = len([r for r in test_results.values() if r["status"] == "success"])
        total_tests = len(test_results)
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        return {
            "success": success_rate > 50,  # Consider successful if more than half pass
            "test_results": test_results,
            "success_rate": success_rate,
            "passed": successful_tests,
            "total": total_tests,
            "timestamp": datetime.now().timestamp()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service testing failed: {str(e)}")

@router.get("/metrics/{project_id}")
async def get_validation_metrics(
    project_id: int,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get validation metrics for a project."""
    try:
        from datetime import timedelta
        
        # Get validation runs from the last N days
        since_date = datetime.utcnow() - timedelta(days=days)
        
        validation_runs = db.query(ValidationRun).filter(
            ValidationRun.project_id == project_id,
            ValidationRun.started_at >= since_date
        ).all()
        
        if not validation_runs:
            return {
                "success": True,
                "metrics": {
                    "total_validations": 0,
                    "success_rate": 0,
                    "average_duration": 0,
                    "failure_reasons": {}
                }
            }
        
        # Calculate metrics
        total_validations = len(validation_runs)
        successful_validations = len([r for r in validation_runs if r.success])
        success_rate = (successful_validations / total_validations * 100) if total_validations > 0 else 0
        
        # Calculate average duration
        completed_runs = [r for r in validation_runs if r.completed_at and r.started_at]
        if completed_runs:
            total_duration = sum(
                (r.completed_at - r.started_at).total_seconds() 
                for r in completed_runs
            )
            average_duration = total_duration / len(completed_runs)
        else:
            average_duration = 0
        
        # Analyze failure reasons
        failed_runs = [r for r in validation_runs if not r.success and r.error_context]
        failure_reasons = {}
        for run in failed_runs:
            # Extract failure type from error context
            error_context = run.error_context.lower()
            if "snapshot" in error_context:
                failure_type = "snapshot_creation"
            elif "clone" in error_context or "git" in error_context:
                failure_type = "codebase_cloning"
            elif "setup" in error_context or "install" in error_context:
                failure_type = "setup_commands"
            elif "deployment" in error_context:
                failure_type = "deployment_validation"
            elif "graph" in error_context or "analysis" in error_context:
                failure_type = "static_analysis"
            elif "web-eval" in error_context or "testing" in error_context:
                failure_type = "ui_testing"
            else:
                failure_type = "unknown"
            
            failure_reasons[failure_type] = failure_reasons.get(failure_type, 0) + 1
        
        return {
            "success": True,
            "metrics": {
                "total_validations": total_validations,
                "successful_validations": successful_validations,
                "failed_validations": total_validations - successful_validations,
                "success_rate": round(success_rate, 2),
                "average_duration": round(average_duration, 2),
                "failure_reasons": failure_reasons,
                "period_days": days
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get validation metrics: {str(e)}")

