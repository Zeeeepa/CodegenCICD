#!/usr/bin/env python3
"""
Health check script for CodegenCICD application
"""
import asyncio
import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, Any

# Add app to Python path
sys.path.append('/app')

try:
    import httpx
    import psycopg2
    import redis
    from urllib.parse import urlparse
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


class HealthChecker:
    """Comprehensive health check for all system components"""
    
    def __init__(self):
        self.checks = {}
        self.start_time = time.time()
    
    async def check_web_server(self) -> Dict[str, Any]:
        """Check if the web server is responding"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:8000/health")
                if response.status_code == 200:
                    return {"status": "healthy", "response_time": response.elapsed.total_seconds()}
                else:
                    return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            db_url = os.environ.get('DATABASE_URL', 'postgresql://codegencd:codegencd@postgres:5432/codegencd')
            parsed = urlparse(db_url)
            
            start_time = time.time()
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path[1:]
            )
            
            # Test query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            
            response_time = time.time() - start_time
            return {"status": "healthy", "response_time": response_time}
            
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
            parsed = urlparse(redis_url)
            
            start_time = time.time()
            r = redis.Redis(
                host=parsed.hostname,
                port=parsed.port or 6379,
                db=int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0
            )
            
            # Test ping
            r.ping()
            
            # Test set/get
            test_key = f"healthcheck:{int(time.time())}"
            r.set(test_key, "test", ex=10)
            value = r.get(test_key)
            r.delete(test_key)
            
            if value != b"test":
                raise Exception("Redis set/get test failed")
            
            response_time = time.time() - start_time
            return {"status": "healthy", "response_time": response_time}
            
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space"""
        try:
            import shutil
            
            paths_to_check = ["/app/logs", "/app/data", "/tmp"]
            disk_info = {}
            
            for path in paths_to_check:
                if os.path.exists(path):
                    total, used, free = shutil.disk_usage(path)
                    free_percent = (free / total) * 100
                    disk_info[path] = {
                        "total_gb": round(total / (1024**3), 2),
                        "used_gb": round(used / (1024**3), 2),
                        "free_gb": round(free / (1024**3), 2),
                        "free_percent": round(free_percent, 2)
                    }
            
            # Check if any path has less than 10% free space
            critical_paths = [path for path, info in disk_info.items() 
                            if info["free_percent"] < 10]
            
            if critical_paths:
                return {
                    "status": "warning", 
                    "disk_info": disk_info,
                    "critical_paths": critical_paths
                }
            else:
                return {"status": "healthy", "disk_info": disk_info}
                
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def check_memory(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            memory_info = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_percent": memory.percent,
                "available_percent": round((memory.available / memory.total) * 100, 2)
            }
            
            if memory.percent > 90:
                return {"status": "critical", "memory_info": memory_info}
            elif memory.percent > 80:
                return {"status": "warning", "memory_info": memory_info}
            else:
                return {"status": "healthy", "memory_info": memory_info}
                
        except ImportError:
            # psutil not available, skip memory check
            return {"status": "skipped", "reason": "psutil not available"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def check_external_services(self) -> Dict[str, Any]:
        """Check external service connectivity"""
        services = {}
        
        # Check Codegen API
        try:
            from backend.services.codegen_api_client import CodegenAPIClient
            async with CodegenAPIClient() as client:
                is_valid = await client.validate_connection()
                services["codegen_api"] = {
                    "status": "healthy" if is_valid else "unhealthy",
                    "validated": is_valid
                }
        except Exception as e:
            services["codegen_api"] = {"status": "unhealthy", "error": str(e)}
        
        # Check GitHub API (basic connectivity)
        try:
            github_token = os.environ.get('GITHUB_TOKEN')
            if github_token:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        "https://api.github.com/user",
                        headers={"Authorization": f"token {github_token}"}
                    )
                    services["github_api"] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "status_code": response.status_code
                    }
            else:
                services["github_api"] = {"status": "skipped", "reason": "No token configured"}
        except Exception as e:
            services["github_api"] = {"status": "unhealthy", "error": str(e)}
        
        return services
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        print("🔍 Running health checks...")
        
        # Core infrastructure checks
        self.checks["web_server"] = await self.check_web_server()
        self.checks["database"] = self.check_database()
        self.checks["redis"] = self.check_redis()
        
        # System resource checks
        self.checks["disk_space"] = self.check_disk_space()
        self.checks["memory"] = self.check_memory()
        
        # External service checks
        self.checks["external_services"] = await self.check_external_services()
        
        # Overall health assessment
        critical_failures = []
        warnings = []
        
        for check_name, result in self.checks.items():
            if isinstance(result, dict):
                if result.get("status") == "critical":
                    critical_failures.append(check_name)
                elif result.get("status") in ["unhealthy", "warning"]:
                    warnings.append(check_name)
                elif isinstance(result, dict) and check_name == "external_services":
                    # Check nested external services
                    for service_name, service_result in result.items():
                        if service_result.get("status") == "unhealthy":
                            warnings.append(f"external_services.{service_name}")
        
        # Determine overall status
        if critical_failures:
            overall_status = "critical"
        elif warnings:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        total_time = time.time() - self.start_time
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "check_duration": round(total_time, 3),
            "critical_failures": critical_failures,
            "warnings": warnings,
            "checks": self.checks
        }


async def main():
    """Main health check function"""
    checker = HealthChecker()
    
    try:
        results = await checker.run_all_checks()
        
        # Print results
        status = results["overall_status"]
        if status == "healthy":
            print("✅ All health checks passed")
            print(json.dumps(results, indent=2))
            sys.exit(0)
        elif status == "warning":
            print("⚠️  Health check warnings detected")
            print(json.dumps(results, indent=2))
            sys.exit(0)  # Warnings don't fail health check
        else:
            print("❌ Critical health check failures")
            print(json.dumps(results, indent=2))
            sys.exit(1)
            
    except Exception as e:
        print(f"💥 Health check failed with exception: {e}")
        print(json.dumps({
            "overall_status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

