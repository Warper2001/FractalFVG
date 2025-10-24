# Feature Specification: Unified Deployment Script

**Feature Branch**: `003-unified-deployment-script`  
**Created**: October 23, 2025  
**Status**: Draft  
**Input**: User description: "bring the deployment scripts into one end to end script. use the .env for creds"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single Command Deployment (Priority: P1)

As a developer, I want to run a single command that handles the complete deployment pipeline from project creation to backtest execution, so that I can deploy and test my trading algorithms efficiently without managing multiple scripts.

**Why this priority**: This is the core value proposition - eliminating script fragmentation and providing a streamlined deployment experience.

**Independent Test**: Can be fully tested by running the unified script with a test algorithm and verifying it completes the full pipeline (project creation → file upload → compilation → backtest → results) without errors.

**Acceptance Scenarios**:

1. **Given** a valid algorithm file and configured .env credentials, **When** I run the unified deployment script, **Then** the system completes the entire pipeline and returns backtest results
2. **Given** missing or invalid credentials in .env, **When** I run the script, **Then** the system provides clear error messages and exits gracefully
3. **Given** a non-existent algorithm file, **When** I run the script, **Then** the system validates the file path and reports the error before attempting deployment

---

### User Story 2 - Environment Configuration Management (Priority: P2)

As a developer, I want the deployment script to automatically load and use credentials from the .env file, so that I don't need to manually manage API credentials across different environments.

**Why this priority**: Security and convenience - centralized credential management reduces errors and improves security practices.

**Independent Test**: Can be fully tested by creating different .env configurations and verifying the script correctly loads and uses the credentials for API authentication.

**Acceptance Scenarios**:

1. **Given** a properly formatted .env file with QuantConnect credentials, **When** the script runs, **Then** it successfully authenticates with the QuantConnect API
2. **Given** missing QUANTCONNECT_USER_ID in .env, **When** the script runs, **Then** it reports the specific missing credential and exits
3. **Given** invalid credentials in .env, **When** the script runs, **Then** it handles API authentication errors gracefully

---

### User Story 3 - Progress Monitoring and Logging (Priority: P3)

As a developer, I want to see real-time progress and detailed logs during deployment, so that I can monitor the deployment process and troubleshoot any issues that arise.

**Why this priority**: Operational visibility - essential for debugging and understanding deployment status.

**Independent Test**: Can be fully tested by running the script and verifying that appropriate progress indicators and log messages are displayed at each step.

**Acceptance Scenarios**:

1. **Given** a running deployment, **When** each pipeline step completes, **Then** the system displays progress indicators and step completion messages
2. **Given** a deployment failure, **When** an error occurs, **Then** the system provides detailed error information and context
3. **Given** a successful deployment, **When** the pipeline completes, **Then** the system displays a summary with key results and next steps

**Progress Monitoring Requirements**:
- **Visual Progress Bar**: Display a horizontal progress bar showing overall completion percentage
- **Step Names**: Show current step name (e.g., "Creating Project", "Compiling Algorithm")
- **Timestamps**: Include start/end timestamps for each step and overall duration
- **Real-time Updates**: Update progress indicators as each step advances
- **Clean Interface**: Maintain readable output without excessive verbosity

---

### Edge Cases

- What happens when the QuantConnect API is temporarily unavailable?
- How does the system handle network interruptions during long-running operations?
- What happens when project creation succeeds but file upload fails?
- How does the system handle compilation errors in the algorithm?
- What happens when backtest creation fails due to rate limiting?

### Error Handling and Recovery

- **Full Rollback Strategy**: On any pipeline failure, the system must clean up all created resources (projects, files, backtests) to ensure clean state
- **Debug Output**: All failures must output full debug information including API responses, stack traces, and system state
- **Atomic Operations**: Each pipeline step must be designed to be reversible with proper cleanup procedures
- **State Validation**: Before cleanup, the system must validate what resources exist to avoid cleanup errors

### API Failure Mode Handling

- **Rate Limiting (429)**: Implement conservative rate limiting with 1-2 second delays between API calls and 5-10 second delays for heavy operations, plus exponential backoff with jitter, starting at 1 second, max 30 seconds, up to 5 retry attempts
- **Authentication Errors (401/403)**: Fail immediately with clear credential error message, no retry
- **Server Errors (5xx)**: Retry with exponential backoff, max 3 attempts, then fail with full debug output
- **Network Timeouts**: Retry with increasing timeout values, max 3 attempts
- **Client Errors (4xx except 429)**: Fail immediately with specific error details
- **Retry Visibility**: Show retry attempts in progress bar with "Retrying... (attempt X/Y)" message

### Observability and Logging

- **Structured Logging**: Use JSON-formatted logs with consistent fields (timestamp, level, message, context)
- **Verbosity Levels**: Configurable logging levels (ERROR, WARN, INFO, DEBUG) via command-line flag
- **ERROR Level**: Critical failures with full stack traces and debug information
- **WARN Level**: Retry attempts, API rate limiting, non-critical issues
- **INFO Level**: Step completions, progress updates, summary results
- **DEBUG Level**: Detailed API requests/responses, internal state changes
- **Log Rotation**: Automatic log file management with size limits
- **Performance Metrics**: Track timing for each pipeline step and overall duration
- **Error Correlation**: Unique deployment IDs for tracking end-to-end execution

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST read QuantConnect credentials from .env file (QUANTCONNECT_USER_ID, QUANTCONNECT_API_TOKEN)
- **FR-002**: System MUST validate credential presence and format before attempting API connections
- **FR-003**: System MUST consolidate all existing deployment functionality into a single executable script
- **FR-004**: System MUST execute the complete pipeline: project creation → file upload → compilation → backtest → results retrieval
- **FR-005**: System MUST provide real-time progress feedback for each pipeline step
- **FR-006**: System MUST handle API errors gracefully with informative error messages
- **FR-007**: System MUST validate input algorithm file exists and is readable before deployment
- **FR-008**: System MUST support command-line arguments for algorithm file path and optional parameters
- **FR-009**: System MUST generate unique project names to avoid conflicts during repeated deployments
- **FR-010**: System MUST clean up temporary resources (test projects) after successful deployment

### Technical Constraints

- **Python Version**: Must support Python 3.11+ for QuantConnect LEAN compatibility
- **Dependency Limits**: Only use standard CLI libraries (requests, click, tqdm, python-dotenv) - no heavy frameworks
- **Single File Architecture**: Must be deliverable as a single executable script file
- **Cross-Platform**: Must run on Linux, macOS, and Windows environments
- **No External Services**: Cannot depend on external services beyond QuantConnect API
- **Memory Constraints**: Must run efficiently with <100MB memory usage
- **File System**: Use only standard file system operations, no special permissions required

### Key Entities *(include if feature involves data)*

- **Deployment Configuration**: Contains algorithm file path, backtest parameters, and deployment options
- **Pipeline State**: Tracks current step, progress, and intermediate results (project ID, compile ID, backtest ID)
- **Credentials**: QuantConnect API authentication details loaded from .env file
- **Deployment Results**: Contains backtest performance metrics and completion status

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can complete full algorithm deployment using a single command within 5 minutes
- **SC-002**: Script successfully handles 95% of deployment scenarios without manual intervention
- **SC-003**: Deployment time reduced by 70% compared to running individual scripts sequentially
- **SC-004**: Zero credential exposure - all authentication handled through .env file
- **SC-005**: 100% of deployment failures provide clear, actionable error messages with next steps

## Clarifications

### Session 2025-10-23

- Q: When a pipeline step fails (e.g., project created but compilation fails), how should the script handle partial state and cleanup? → A: Full rollback - Clean up all created resources on any failure
- Q: What specific progress indicators should the script display during deployment? → A: Progress bar with step names and timestamps
- Q: How should the script handle different types of QuantConnect API failures? → A: Categorized handling with exponential backoff
- Q: What are the technical boundaries and constraints for the deployment script? → A: Python 3.11+ with standard CLI libraries only
- Q: What level of logging and monitoring should the script provide? → A: Structured logging with configurable verbosity levels
- Q: How should the script handle API rate limiting when chaining calls quickly or using brute force approaches? → A: Conservative rate limiting with configurable delays (1-2 seconds between calls, 5-10 seconds for heavy operations)