# CodegenCICD Test Suite

This directory contains all test files for the CodegenCICD system.

## Test Files

### Web Evaluation Tests

#### `simple_web_eval.py`
Lightweight web evaluation script that tests the system using HTTP requests.

**Features:**
- API endpoint testing
- Frontend availability check
- Integration verification
- JSON response validation
- System health reporting

**Usage:**
```bash
python tests/simple_web_eval.py
```

#### `web_eval_test.py`
Full browser automation testing using Playwright for comprehensive UI testing.

**Features:**
- Real browser automation
- Screenshot capture
- UI interaction testing
- Network request monitoring
- Advanced web evaluation

**Usage:**
```bash
python tests/web_eval_test.py
```

**Requirements:**
```bash
pip install playwright beautifulsoup4
playwright install
```

### API & Integration Tests

#### `test_codegen_api.py`
Tests for the Codegen API integration and functionality.

#### `test_integration.py`
Integration tests for the complete system workflow.

#### `run_comprehensive_tests.py`
Comprehensive test runner that executes multiple test suites.

### JavaScript Tests

#### `full-cicd-cycle-test.js`
Full CI/CD cycle testing using JavaScript/Node.js.

#### `validation-test.js`
Validation tests for the system components.

### Legacy Tests

#### `test_web_eval_agent.py`
Legacy web evaluation agent tests.

#### `test_web_eval_deployment.py`
Legacy deployment testing scripts.

## Running Tests

Make sure the CodegenCICD system is running before executing tests:

```bash
# Start the system
./start.sh

# Run lightweight evaluation
python tests/simple_web_eval.py

# Run full browser testing
python tests/web_eval_test.py
```

## Test Results

Both test scripts provide comprehensive reports including:
- API endpoint status
- Frontend functionality
- Integration health
- System performance metrics
- Detailed error reporting

The tests validate that the entire CodegenCICD system is working correctly.
