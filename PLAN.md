# CodegenCICD Dashboard Implementation Plan

## Single-Unit Atomic Task Implementation Framework v4.0

This document outlines the complete implementation plan for the CodegenCICD Dashboard following the atomic task methodology. Each component represents exactly one unit of functionality with explicit dependencies and integration points.

## Project Overview

The CodegenCICD Dashboard is a comprehensive CI/CD orchestration platform that integrates multiple AI-powered services:

### Core Stack
- **Codegen SDK** - Agent coordination & code generation via API
- **Graph-Sitter** - Static analysis & code quality metrics  
- **Grainchain** - Sandboxing + snapshot creation + PR validation
- **Web-Eval-Agent** - UI testing & browser automation

### Services
- **GitHub Client** - Repository management, webhook setup, PR operations
- **Cloudflare Worker** - Webhook gateway for real-time notifications

## Current Implementation Analysis

### ✅ COMPLETED COMPONENTS

#### 1. Basic Pinned Projects API
- **Location**: `backend/routers/simple_projects.py`, `backend/simple_database.py`
- **Status**: ✅ FULLY IMPLEMENTED AND TESTED
- **Features**: Pin/unpin projects, list pinned projects, separate database
- **API Endpoints**: GET /pinned, POST /pin, DELETE /unpin/{id}

#### 2. Frontend Component Library
- **Location**: `frontend/src/components/`
- **Status**: ✅ COMPONENTS EXIST BUT NOT INTEGRATED
- **Components**: Dashboard, ProjectCard, Settings dialogs, GitHub selector
- **Missing**: Integration with backend APIs, proper data flow

#### 3. Service Client Foundations
- **Location**: `backend/services/`
- **Status**: ✅ CLIENT STUBS EXIST
- **Services**: codegen_client.py, github_service.py, grainchain_client.py, etc.
- **Missing**: Proper API integration, error handling, authentication

#### 4. Web-Eval-Agent Testing Infrastructure
- **Location**: `web-eval-agent/`
- **Status**: ✅ DEPLOYED AND CONFIGURED
- **Capabilities**: UI testing with Gemini API integration

### ❌ MISSING CRITICAL COMPONENTS

## Implementation Checklist

### Phase 1: Core Integration (CRITICAL)
1. [X] **Simple Pinned Projects API** - Basic CRUD operations ✅ COMPLETED
2. [ ] **Frontend-Backend Integration** - Connect React components to APIs
3. [ ] **GitHub Repository Integration** - Fix authentication, list repos, setup webhooks
4. [ ] **Project Card Enhancement** - Add Agent Run button, settings, status indicators
5. [ ] **Environment Variables Management** - Editable service URLs and API keys

### Phase 2: Agent Orchestration (HIGH PRIORITY)
6. [ ] **Codegen API Integration** - Agent runs, plan confirmation, PR tracking
7. [ ] **Agent Run Dialog Implementation** - Target text input, progress tracking
8. [ ] **Project Settings System** - Repository rules, setup commands, secrets
9. [ ] **Webhook Notification System** - Real-time PR updates via Cloudflare
10. [ ] **Auto-merge Configuration** - Checkbox and merge logic

### Phase 3: Validation Pipeline (COMPLEX)
11. [ ] **Grainchain Snapshot Service** - Sandbox creation and management
12. [ ] **Graph-Sitter Integration** - Static analysis and code quality
13. [ ] **Web-Eval-Agent Orchestration** - Automated UI testing pipeline
14. [ ] **Validation Flow Implementation** - End-to-end PR validation
15. [ ] **Error Recovery System** - Context passing and iterative improvement

### Phase 4: Production Features (FINAL)
16. [ ] **Real-time Dashboard Updates** - WebSocket integration for live status
17. [ ] **Comprehensive Error Handling** - User-friendly error states
18. [ ] **Performance Optimization** - Caching, lazy loading, response times
19. [ ] **Security Hardening** - Authentication, input validation, secret management
20. [ ] **Documentation and Testing** - Complete user guides and E2E tests

## Atomic Task Dependencies

### Critical Path Analysis
- **STEP2-5** (Frontend Integration) → **STEP6-10** (Agent Orchestration)
- **STEP6** (Codegen API) → **STEP11-15** (Validation Pipeline)
- **STEP8** (Project Settings) → **STEP11** (Grainchain Snapshots)
- **STEP9** (Webhooks) → **STEP16** (Real-time Updates)

### Parallel Development Opportunities
- **Frontend Integration** (STEP2-5) can proceed independently
- **Service Integrations** (STEP6-7, 11-13) can be developed in parallel
- **Testing Infrastructure** is ready for immediate validation

## Technical Architecture

### Data Flow
1. **User selects GitHub project** → Pin to dashboard as card
2. **Webhook URL set** → Cloudflare worker receives PR notifications  
3. **Agent Run triggered** → Codegen API creates PR
4. **Validation pipeline** → Grainchain + Graph-Sitter + Web-Eval-Agent
5. **Auto-merge decision** → Based on validation results

### Service Integration Points
```
Frontend Dashboard ↔ FastAPI Backend ↔ External Services
                                    ├── GitHub API (repos, webhooks, PRs)
                                    ├── Codegen API (agent runs, plans)
                                    ├── Grainchain (snapshots, sandboxing)
                                    ├── Graph-Sitter (static analysis)
                                    └── Web-Eval-Agent (UI testing)
```

## Environment Variables Required
```bash
# Codegen Agent API
CODEGEN_ORG_ID=323
CODEGEN_API_TOKEN=[REDACTED]

# GitHub Integration  
GITHUB_TOKEN=[REDACTED]

# Cloudflare Worker
CLOUDFLARE_API_KEY=[REDACTED]
CLOUDFLARE_ACCOUNT_ID=[REDACTED]
CLOUDFLARE_WORKER_URL=https://webhook-gateway.pixeliumperfecto.workers.dev

# Web-Eval-Agent
GEMINI_API_KEY=[REDACTED]

# Service URLs (Currently Empty - Need Implementation)
GRAINCHAIN_URL=
GRAPH_SITTER_URL=
WEB_EVAL_AGENT_URL=
```

## Success Criteria

Each atomic task must achieve:
- ✅ **Functional Completeness** - All specified features working
- ✅ **Web-Eval-Agent Validation** - UI components tested and verified
- ✅ **Performance Standards** - <5ms API response, <100ms UI updates
- ✅ **Error Resilience** - Graceful handling of all failure modes
- ✅ **Security Compliance** - Authentication, validation, secret management

## Implementation Strategy

### Immediate Priority (Week 1)
- **STEP2**: Frontend-Backend Integration
- **STEP3**: GitHub Repository Integration  
- **STEP4**: Enhanced Project Cards

### High Priority (Week 2)
- **STEP6**: Codegen API Integration
- **STEP7**: Agent Run Dialog
- **STEP8**: Project Settings System

### Complex Integration (Week 3-4)
- **STEP11-15**: Validation Pipeline Implementation
- **STEP16**: Real-time Updates
- **STEP17-20**: Production Hardening

## Next Steps

1. **Start with STEP2.md** - Frontend-Backend Integration (builds on completed STEP1)
2. **Validate each component** with Web-Eval-Agent before proceeding
3. **Maintain atomic boundaries** - one functionality per step
4. **Test integration points** at each phase boundary

---

*This plan follows the Single-Unit Atomic Task Implementation Framework v4.0 for maximum development velocity and quality assurance.*
