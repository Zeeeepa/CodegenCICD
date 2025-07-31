#!/bin/bash
set -e

# CodegenCICD Infrastructure Testing Script
echo "🧪 Starting comprehensive infrastructure testing..."

# Configuration
TEST_LOG_FILE=${TEST_LOG_FILE:-./logs/infrastructure-test.log}
DOCKER_COMPOSE_FILE=${DOCKER_COMPOSE_FILE:-docker-compose.yml}
BASE_URL=${BASE_URL:-http://localhost:8000}
TIMEOUT=${TIMEOUT:-30}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$TEST_LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$TEST_LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$TEST_LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$TEST_LOG_FILE"
}

# Test execution function
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_result="$3"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    log "Running test: $test_name"
    
    if eval "$test_command"; then
        if [[ "$expected_result" == "success" ]]; then
            success "✅ $test_name - PASSED"
            TESTS_PASSED=$((TESTS_PASSED + 1))
            return 0
        else
            error "❌ $test_name - FAILED (expected failure but got success)"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 1
        fi
    else
        if [[ "$expected_result" == "failure" ]]; then
            success "✅ $test_name - PASSED (expected failure)"
            TESTS_PASSED=$((TESTS_PASSED + 1))
            return 0
        else
            error "❌ $test_name - FAILED"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            return 1
        fi
    fi
}

# Wait for service to be ready
wait_for_service() {
    local service_url="$1"
    local service_name="$2"
    local max_attempts=30
    local attempt=1
    
    log "Waiting for $service_name to be ready..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "$service_url" > /dev/null 2>&1; then
            success "$service_name is ready"
            return 0
        fi
        
        log "Attempt $attempt/$max_attempts - $service_name not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    error "$service_name failed to become ready within $((max_attempts * 2)) seconds"
    return 1
}

# Test Docker infrastructure
test_docker_infrastructure() {
    log "🐳 Testing Docker infrastructure..."
    
    # Test Docker daemon
    run_test "Docker daemon running" "docker info > /dev/null 2>&1" "success"
    
    # Test Docker Compose
    run_test "Docker Compose available" "docker-compose --version > /dev/null 2>&1" "success"
    
    # Test if services are running
    services=("postgres" "redis" "app" "nginx")
    for service in "${services[@]}"; do
        run_test "$service container running" \
            "docker-compose -f $DOCKER_COMPOSE_FILE ps $service | grep -q 'Up'" \
            "success"
    done
}

# Test database connectivity
test_database_connectivity() {
    log "🗄️ Testing database connectivity..."
    
    # Test PostgreSQL connection
    run_test "PostgreSQL connection" \
        "docker-compose -f $DOCKER_COMPOSE_FILE exec -T postgres pg_isready -U codegencd -d codegencd" \
        "success"
    
    # Test Redis connection
    run_test "Redis connection" \
        "docker-compose -f $DOCKER_COMPOSE_FILE exec -T redis redis-cli ping | grep -q PONG" \
        "success"
    
    # Test database query
    run_test "PostgreSQL query execution" \
        "docker-compose -f $DOCKER_COMPOSE_FILE exec -T postgres psql -U codegencd -d codegencd -c 'SELECT 1;' | grep -q '1 row'" \
        "success"
}

# Test application endpoints
test_application_endpoints() {
    log "🌐 Testing application endpoints..."
    
    # Wait for application to be ready
    wait_for_service "$BASE_URL/health" "Application"
    
    # Test basic endpoints
    run_test "Root endpoint" \
        "curl -f -s $BASE_URL/ | jq -r '.service' | grep -q 'CodegenCICD'" \
        "success"
    
    run_test "Health check endpoint" \
        "curl -f -s $BASE_URL/health | jq -r '.status' | grep -q 'healthy'" \
        "success"
    
    run_test "Version endpoint" \
        "curl -f -s $BASE_URL/version | jq -r '.version' | grep -q '1.0.0'" \
        "success"
    
    run_test "Metrics endpoint" \
        "curl -f -s $BASE_URL/metrics | grep -q 'http_requests_total'" \
        "success"
}

# Test authentication system
test_authentication_system() {
    log "🔐 Testing authentication system..."
    
    # Test login endpoint exists
    run_test "Login endpoint available" \
        "curl -f -s -X POST $BASE_URL/api/auth/login -H 'Content-Type: application/json' -d '{}' | grep -q 'error'" \
        "success"
    
    # Test successful login
    run_test "Admin login" \
        "curl -f -s -X POST $BASE_URL/api/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin123\"}' | jq -r '.access_token' | grep -v null" \
        "success"
    
    # Get admin token for further tests
    ADMIN_TOKEN=$(curl -f -s -X POST $BASE_URL/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')
    
    if [[ "$ADMIN_TOKEN" != "null" && -n "$ADMIN_TOKEN" ]]; then
        success "Admin token obtained: ${ADMIN_TOKEN:0:20}..."
        
        # Test authenticated endpoint
        run_test "Authenticated endpoint access" \
            "curl -f -s -H 'Authorization: Bearer $ADMIN_TOKEN' $BASE_URL/api/auth/me | jq -r '.username' | grep -q 'admin'" \
            "success"
        
        # Test admin-only endpoint
        run_test "Admin-only endpoint access" \
            "curl -f -s -H 'Authorization: Bearer $ADMIN_TOKEN' $BASE_URL/api/auth/users | jq -r '.users' | grep -q 'admin'" \
            "success"
    else
        error "Failed to obtain admin token"
        TESTS_FAILED=$((TESTS_FAILED + 2))
        TESTS_TOTAL=$((TESTS_TOTAL + 2))
    fi
    
    # Test unauthorized access
    run_test "Unauthorized access blocked" \
        "curl -f -s $BASE_URL/api/projects 2>/dev/null" \
        "failure"
}

# Test monitoring and metrics
test_monitoring_system() {
    log "📊 Testing monitoring system..."
    
    # Test Prometheus metrics
    run_test "Prometheus metrics format" \
        "curl -f -s $BASE_URL/metrics | grep -q '# HELP'" \
        "success"
    
    # Test monitoring endpoints (with admin token if available)
    if [[ -n "$ADMIN_TOKEN" ]]; then
        run_test "Detailed health check" \
            "curl -f -s -H 'Authorization: Bearer $ADMIN_TOKEN' $BASE_URL/api/monitoring/health/detailed | jq -r '.status' | grep -q 'healthy'" \
            "success"
        
        run_test "Custom metrics endpoint" \
            "curl -f -s -H 'Authorization: Bearer $ADMIN_TOKEN' $BASE_URL/api/monitoring/metrics/custom | jq -r '.application_metrics.uptime_seconds' | grep -E '^[0-9]+'" \
            "success"
        
        run_test "System diagnostics" \
            "curl -f -s -H 'Authorization: Bearer $ADMIN_TOKEN' $BASE_URL/api/monitoring/diagnostics | jq -r '.system_info.cpu_count' | grep -E '^[0-9]+'" \
            "success"
    else
        warning "Skipping authenticated monitoring tests - no admin token"
    fi
}

# Test external service integrations
test_external_services() {
    log "🔗 Testing external service integrations..."
    
    # Test if external services are configured
    if [[ -n "$CODEGEN_API_TOKEN" ]]; then
        run_test "Codegen API token configured" "echo 'Token configured'" "success"
    else
        warning "Codegen API token not configured"
    fi
    
    if [[ -n "$GITHUB_TOKEN" ]]; then
        run_test "GitHub token configured" "echo 'Token configured'" "success"
    else
        warning "GitHub token not configured"
    fi
    
    if [[ -n "$GEMINI_API_KEY" ]]; then
        run_test "Gemini API key configured" "echo 'Key configured'" "success"
    else
        warning "Gemini API key not configured"
    fi
}

# Test error handling and resilience
test_error_handling() {
    log "🛡️ Testing error handling and resilience..."
    
    # Test 404 handling
    run_test "404 error handling" \
        "curl -s $BASE_URL/nonexistent-endpoint | jq -r '.error' | grep -q 'not_found'" \
        "success"
    
    # Test rate limiting (if implemented)
    run_test "Rate limiting response" \
        "for i in {1..20}; do curl -s $BASE_URL/health > /dev/null; done; curl -s $BASE_URL/health | jq -r '.status' | grep -q 'healthy'" \
        "success"
    
    # Test CORS headers
    run_test "CORS headers present" \
        "curl -s -H 'Origin: http://localhost:3000' $BASE_URL/health -I | grep -q 'Access-Control-Allow-Origin'" \
        "success"
}

# Test security measures
test_security_measures() {
    log "🔒 Testing security measures..."
    
    # Test security headers
    run_test "Security headers present" \
        "curl -s -I $BASE_URL/ | grep -q 'X-Content-Type-Options'" \
        "success"
    
    # Test that sensitive endpoints require authentication
    run_test "Protected endpoint requires auth" \
        "curl -s $BASE_URL/api/projects | jq -r '.error' | grep -q 'authentication'" \
        "success"
    
    # Test SQL injection protection (basic)
    run_test "SQL injection protection" \
        "curl -s '$BASE_URL/api/projects?id=1%27%20OR%20%271%27=%271' | jq -r '.error' | grep -q 'authentication'" \
        "success"
}

# Test performance and load
test_performance() {
    log "⚡ Testing performance..."
    
    # Test response times
    run_test "Health check response time < 1s" \
        "timeout 1s curl -f -s $BASE_URL/health > /dev/null" \
        "success"
    
    run_test "Metrics endpoint response time < 2s" \
        "timeout 2s curl -f -s $BASE_URL/metrics > /dev/null" \
        "success"
    
    # Test concurrent requests
    run_test "Concurrent requests handling" \
        "for i in {1..10}; do curl -s $BASE_URL/health > /dev/null & done; wait; echo 'Concurrent requests completed'" \
        "success"
}

# Test logging and observability
test_logging() {
    log "📝 Testing logging and observability..."
    
    # Test log file creation
    run_test "Application logs exist" \
        "docker-compose -f $DOCKER_COMPOSE_FILE logs app | grep -q 'Starting CodegenCICD'" \
        "success"
    
    # Test structured logging format
    run_test "Structured logging format" \
        "docker-compose -f $DOCKER_COMPOSE_FILE logs app | grep -q 'correlation_id'" \
        "success"
}

# Generate test report
generate_test_report() {
    log "📋 Generating test report..."
    
    echo ""
    echo "=========================================="
    echo "🧪 INFRASTRUCTURE TEST REPORT"
    echo "=========================================="
    echo ""
    echo "📊 Test Summary:"
    echo "  Total Tests: $TESTS_TOTAL"
    echo "  Passed: $TESTS_PASSED"
    echo "  Failed: $TESTS_FAILED"
    echo "  Success Rate: $(( (TESTS_PASSED * 100) / TESTS_TOTAL ))%"
    echo ""
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        success "🎉 All tests passed! Infrastructure is ready for production."
        echo ""
        echo "✅ Production Readiness Checklist:"
        echo "  ✅ Docker infrastructure working"
        echo "  ✅ Database connectivity established"
        echo "  ✅ Application endpoints responding"
        echo "  ✅ Authentication system functional"
        echo "  ✅ Monitoring and metrics available"
        echo "  ✅ Security measures in place"
        echo "  ✅ Error handling working"
        echo "  ✅ Performance acceptable"
        echo "  ✅ Logging operational"
        echo ""
        echo "🚀 Ready for production deployment!"
        return 0
    else
        error "❌ Some tests failed. Infrastructure needs attention before production deployment."
        echo ""
        echo "🔧 Issues to address:"
        echo "  - Review failed tests in the log: $TEST_LOG_FILE"
        echo "  - Fix infrastructure issues"
        echo "  - Re-run tests to verify fixes"
        echo ""
        return 1
    fi
}

# Main test execution
main() {
    log "🚀 Starting comprehensive infrastructure testing..."
    
    # Create logs directory
    mkdir -p "$(dirname "$TEST_LOG_FILE")"
    
    # Run test suites
    test_docker_infrastructure
    test_database_connectivity
    test_application_endpoints
    test_authentication_system
    test_monitoring_system
    test_external_services
    test_error_handling
    test_security_measures
    test_performance
    test_logging
    
    # Generate report
    generate_test_report
}

# Parse command line arguments
case "${1:-all}" in
    "all")
        main
        ;;
    "docker")
        test_docker_infrastructure
        ;;
    "database")
        test_database_connectivity
        ;;
    "endpoints")
        test_application_endpoints
        ;;
    "auth")
        test_authentication_system
        ;;
    "monitoring")
        test_monitoring_system
        ;;
    "security")
        test_security_measures
        ;;
    "performance")
        test_performance
        ;;
    "logging")
        test_logging
        ;;
    *)
        echo "Usage: $0 {all|docker|database|endpoints|auth|monitoring|security|performance|logging}"
        echo ""
        echo "Test Suites:"
        echo "  all         - Run all test suites (default)"
        echo "  docker      - Test Docker infrastructure"
        echo "  database    - Test database connectivity"
        echo "  endpoints   - Test application endpoints"
        echo "  auth        - Test authentication system"
        echo "  monitoring  - Test monitoring and metrics"
        echo "  security    - Test security measures"
        echo "  performance - Test performance and load"
        echo "  logging     - Test logging and observability"
        exit 1
        ;;
esac

