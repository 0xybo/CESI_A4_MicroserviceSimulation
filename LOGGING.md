# Logging System Documentation

This document describes the comprehensive logging system implemented across the Microservice Simulation framework.

## Overview

The application includes a centralized logging system that captures events at multiple severity levels:

- **DEBUG**: Detailed information for diagnosing problems
- **INFO**: Confirmation that things are working as expected
- **WARNING**: Something unexpected happened, or may happen
- **ERROR**: A serious problem, a function has not performed some function

## Log Storage

All logs are automatically saved to the `.logs/` folder in the project root directory:

```
.logs/
├── simulation_20240422_143022.log   # Main application log with all levels
├── simulation_20240422_143535.log
├── errors_20240422_143022.log       # Error-specific log (WARNING and ERROR only)
├── errors_20240422_143535.log
└── ...
```

### Log File Types

1. **`simulation_YYYYMMDD_HHMMSS.log`** - Main log file
    - Contains all log messages (DEBUG, INFO, WARNING, ERROR)
    - Rotating handler: 10MB per file, keeps 5 backups
    - Detailed format with timestamps, module names, line numbers, function names

2. **`errors_YYYYMMDD_HHMMSS.log`** - Error-focused log file
    - Contains only WARNING and ERROR level messages
    - Useful for quick access to problems
    - Same rotating handler configuration

3. **Console Output**
    - INFO level and above displayed in the terminal
    - Simple format for readability

## Log Format

### Main Log Format (Files and Console)

```
2024-04-22 14:30:22 - src.Common.Microservice.microservice - DEBUG - [microservice.py:42] - execute() - Executing microservice 'service_a' (call #1)
```

Components:

- **Timestamp**: `YYYY-MM-DD HH:MM:SS`
- **Logger Name**: Module path (e.g., `src.Common.Microservice.microservice`)
- **Level**: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- **File**: `[filename:line_number]`
- **Function**: `function_name()`
- **Message**: The actual log message

## Usage Examples

### Running the Application

When you run the application, logs are automatically created:

```bash
# Run simulation
python -m . build python

# Logs are automatically created in .logs/ folder
```

### Console Output Example

```
2024-04-22 14:30:22 - INFO - Starting Microservice Simulation Application
2024-04-22 14:30:22 - INFO - Command received: build
2024-04-22 14:30:22 - INFO - Processing build command for environment: python
2024-04-22 14:30:22 - INFO - Building Python environment...
2024-04-22 14:30:23 - INFO - Configuration valid: containers=2, services=4, microservices=6
✓ Python environment built successfully
```

## Logging Throughout the Codebase

### Entry Points (`__main__.py`)

- Application startup/completion
- Command processing
- Error handling

### Configuration (`Config/`)

- Configuration file loading
- Schema generation
- Validation success/failures

### Platform Execution (`Python/`, `Docker/`)

- Build process initialization
- Environment validation
- Execution start/completion
- Worker thread management
- Results saving

### Microservices (`Common/Microservice/`)

- Microservice initialization
- Execution flow with call counts
- Delay application
- Error simulation
- Dependency invocations
- Execution timing

### Services (`Common/Service/`)

- Service initialization
- Request processing
- Per-request success/failure tracking

### Containers (`Common/Container/`)

- Container initialization
- Service execution coordination
- Result aggregation

### Monitoring (`Common/Monitor/`)

- Metric recording
- Execution recording
- Result export

### Test Output Management (`Common/TestOutput/`)

- Test directory creation
- Configuration saving
- Script generation
- Results persistence

## Log Levels by Component

### DEBUG Messages

- Variable initialization
- Function entry/exit state
- Configuration loading details
- Directory creation
- Metric updates
- Worker thread assignment

### INFO Messages

- Application startup/shutdown
- Command processing
- Build process completion
- Simulation execution start/completion
- Configuration validation
- Test directory creation
- Results saved location

### WARNING Messages

- Simulated microservice failures
- Dependency failures with stop_on_error
- Request failures in services

### ERROR Messages

- Missing files/directories
- Invalid configurations
- Command execution failures
- Docker/platform availability issues
- Simulation execution failures

## Accessing Logs

### View Latest Logs

```bash
# Linux/macOS
tail -f .logs/simulation_*.log

# Windows (PowerShell)
Get-Content .logs\simulation_*.log -Wait
```

### View Errors Only

```bash
# Linux/macOS
tail -f .logs/errors_*.log

# Windows
Get-Content .logs\errors_*.log -Wait
```

### Search Logs

```bash
# Search for failures
grep -i "failure" .logs/*.log

# Search for specific microservice
grep "microservice_name" .logs/*.log

# Count errors
grep -c "ERROR" .logs/errors_*.log
```

## Programmatic Usage

### Getting a Logger in Your Code

```python
from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)

# Log at different levels
logger.debug("Debug information")
logger.info("Informational message")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)  # exc_info=True includes exception traceback
```

### Example in a Module

```python
from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)

class MyService:
    def __init__(self, name):
        self.name = name
        logger.debug(f"MyService '{name}' initialized")

    def execute(self):
        logger.info(f"Starting execution of MyService '{self.name}'")
        try:
            # Do work
            logger.debug("Work completed successfully")
        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            raise
```

## Logger Configuration

The logger is configured in `src/Common/Utils/logger.py`:

### File Handlers

- **Main log file**: All DEBUG and above messages
- **Error log file**: WARNING and above messages
- **Console**: INFO and above messages
- **Rotation**: 10MB per file, keeps 5 backups

### Formatters

- **Detailed (files)**: Full timestamp, module, line number, function name
- **Simple (console)**: Timestamp and level for readability

## Troubleshooting

### Logs Not Being Created

1. Check that `.logs/` directory is writable
2. Verify logger is initialized in your module
3. Check file permissions

### Finding Specific Errors

1. Check `.logs/errors_*.log` for WARNING and ERROR messages
2. Use grep to search for specific keywords
3. Review the module name in the log to identify the source

### Performance Impact

The logging system uses non-blocking file I/O and has minimal performance impact:

- File writing is buffered
- Rotating handlers prevent disk space issues
- Log levels can be adjusted if needed

## Best Practices

1. **Use appropriate log levels**:
    - DEBUG: Detailed flow information
    - INFO: Important state changes
    - WARNING: Unexpected but recoverable issues
    - ERROR: Serious problems

2. **Include context in messages**:

    ```python
    # Good
    logger.info(f"Service '{service_name}' executing with {request_count} requests")

    # Bad
    logger.info("Service executing")
    ```

3. **Log exceptions with context**:

    ```python
    try:
        # code
    except Exception as e:
        logger.error(f"Failed to process: {e}", exc_info=True)
    ```

4. **Don't log sensitive information**:
    - Avoid logging passwords, API keys, tokens
    - Sanitize user data before logging

## Integration with Existing Code

The logging system has been integrated throughout the codebase:

- Entry points track application lifecycle
- Configuration module logs validation and loading
- Microservices log execution flow and errors
- Services log request processing
- Containers log service orchestration
- Platform implementations log build and execution
- Monitor logs metric recording

All existing functionality is preserved while adding comprehensive visibility.
