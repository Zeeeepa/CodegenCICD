# STEP2: Frontend-Backend Integration for Pinned Projects

## QUERY ##########

### ROLE
You are a full-stack developer with 8+ years of experience in React/TypeScript frontend development and FastAPI backend integration, specializing in modern API consumption patterns and real-time data synchronization.

### TASK
Integrate Frontend Dashboard with Simple Pinned Projects API

### YOUR QUEST
Connect the existing React Dashboard component to the implemented Simple Pinned Projects API, enabling users to view, pin, and unpin GitHub repositories through the UI. This integration must provide real-time updates, proper error handling, and seamless user experience.

## TECHNICAL CONTEXT

### EXISTING CODEBASE:

```typescript
// From frontend/src/components/Dashboard.tsx
interface GitHubRepository {
  id: number;
  name: string;
  full_name: string;
  description?: string;
  html_url: string;
  owner: {
    login: string;
  };
  default_branch: string;
  is_pinned?: boolean;
}

// From frontend/src/components/EnhancedProjectCard.tsx
export interface ProjectData {
  id: number;
  name: string;
  description?: string;
  url: string;
  owner: string;
  lastUpdated: string;
  status: 'active' | 'inactive' | 'error';
  isPinned: boolean;
}
```

```python
# From backend/routers/simple_projects.py
class PinnedProjectResponse(BaseModel):
    id: int
    user_id: str
    github_repo_name: str
    github_repo_url: str
    github_owner: str
    display_name: str = None
    description: str = None
    pinned_at: str = None
    last_updated: str = None
    is_active: bool

# API Endpoints Available:
# GET /api/simple-projects/pinned - List pinned projects
# POST /api/simple-projects/pin - Pin a project
# DELETE /api/simple-projects/unpin/{id} - Unpin a project
```

### IMPLEMENTATION REQUIREMENTS:

- Create API service client for simple-projects endpoints
- Update Dashboard component to fetch and display pinned projects
- Implement pin/unpin functionality with optimistic updates
- Add proper error handling with user-friendly messages
- Ensure type safety between frontend and backend models
- Add loading states and skeleton components
- Implement real-time updates when projects are pinned/unpinned
- Performance requirement: <100ms UI response time for all operations
- Support for up to 50 pinned projects with efficient rendering

## INTEGRATION CONTEXT

### UPSTREAM DEPENDENCIES:
- STEP1.md - Simple Pinned Projects API (backend/routers/simple_projects.py)
- Existing Dashboard component (frontend/src/components/Dashboard.tsx)
- EnhancedProjectCard component (frontend/src/components/EnhancedProjectCard.tsx)

### DOWNSTREAM DEPENDENCIES:
- STEP3.md - GitHub Repository Integration (will use this API client pattern)
- STEP4.md - Enhanced Project Cards (will extend the integrated project cards)
- STEP7.md - Agent Run Dialog (will trigger from integrated project cards)

## EXPECTED OUTCOME

### Files to Create:
1. `frontend/src/services/pinnedProjectsApi.ts` - API client for simple-projects endpoints
2. `frontend/src/hooks/usePinnedProjects.ts` - React hook for pinned projects state management
3. `frontend/src/types/pinnedProjects.ts` - TypeScript interfaces matching backend models

### Files to Modify:
1. `frontend/src/components/Dashboard.tsx` - Integrate with pinned projects API
2. `frontend/src/components/EnhancedProjectCard.tsx` - Add pin/unpin functionality
3. `frontend/src/components/GitHubProjectSelector.tsx` - Connect to pin functionality

### API Client Interface:
```typescript
interface PinnedProjectsApi {
  getPinnedProjects(): Promise<PinnedProject[]>;
  pinProject(project: PinProjectRequest): Promise<PinnedProject>;
  unpinProject(projectId: number): Promise<void>;
}

interface PinnedProject {
  id: number;
  userId: string;
  githubRepoName: string;
  githubRepoUrl: string;
  githubOwner: string;
  displayName?: string;
  description?: string;
  pinnedAt: string;
  lastUpdated: string;
  isActive: boolean;
}
```

### React Hook Interface:
```typescript
interface UsePinnedProjectsReturn {
  projects: PinnedProject[];
  loading: boolean;
  error: string | null;
  pinProject: (project: PinProjectRequest) => Promise<void>;
  unpinProject: (projectId: number) => Promise<void>;
  refreshProjects: () => Promise<void>;
}
```

## ACCEPTANCE CRITERIA

1. ✅ Dashboard displays pinned projects from backend API on load
2. ✅ Users can pin repositories through GitHubProjectSelector
3. ✅ Users can unpin projects from project cards
4. ✅ Optimistic updates provide immediate UI feedback
5. ✅ Error states display user-friendly messages
6. ✅ Loading states show appropriate skeleton components
7. ✅ All operations complete within 100ms UI response time
8. ✅ TypeScript interfaces ensure type safety across frontend-backend boundary
9. ✅ Component re-renders are optimized to prevent unnecessary updates
10. ✅ API errors are handled gracefully with retry mechanisms

## IMPLEMENTATION CONSTRAINTS

- This task represents a SINGLE atomic unit of functionality
- Must be independently implementable and testable
- Implementation must include comprehensive error handling
- Code must conform to React/TypeScript best practices
- Must not modify existing backend API endpoints
- All API calls must be async/await compatible with proper error boundaries

## TESTING REQUIREMENTS

### Unit Tests:
- API client methods with mock responses
- React hook state management and error handling
- Component rendering with different data states
- Error boundary behavior

### Integration Tests:
- End-to-end pin/unpin workflow
- API client with real backend endpoints
- Component integration with API hooks
- Error scenarios and recovery

### Web-Eval-Agent Validation:
- Dashboard loads and displays pinned projects
- Pin/unpin functionality works through UI
- Error messages display appropriately
- Loading states render correctly
- Performance meets response time requirements

## PERFORMANCE REQUIREMENTS

- Initial dashboard load: <500ms
- Pin/unpin operations: <100ms UI response
- API calls: <200ms response time
- Memory usage: <50MB for 50 pinned projects
- Bundle size impact: <10KB additional JavaScript

## ERROR HANDLING SPECIFICATIONS

### API Error Scenarios:
- Network connectivity issues
- Backend service unavailable (500 errors)
- Authentication failures (401 errors)
- Rate limiting (429 errors)
- Invalid request data (400 errors)

### UI Error States:
- Toast notifications for temporary errors
- Inline error messages for form validation
- Fallback UI for critical failures
- Retry buttons for recoverable errors
- Graceful degradation when API is unavailable

## SECURITY CONSIDERATIONS

- All API calls must include proper authentication headers
- Input validation on frontend before API calls
- Sanitize user input to prevent XSS attacks
- Implement CSRF protection for state-changing operations
- Secure storage of any temporary authentication tokens
