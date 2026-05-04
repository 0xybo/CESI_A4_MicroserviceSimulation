# Docker Simulation Platform - Usage Guide

## Commands

### 1. Build Docker Environment

Generates a Docker Compose stack from a configuration file:

```bash
python -m src.Docker build --config config-test.json --output .output
```

**Options:**

- `--config`: Path to simulation config file (default: `config-test.json`)
- `--output`: Output directory where docker-compose.yml will be generated (default: `.`)

### 2. Run Simulation (Build + Test)

Builds and runs a complete simulation with a specified number of requests:

```bash
python -m src.Docker run \
  --config config-test.json \
  --compose /path/to/docker-compose.yml \
  --requests 50 \
  --output results.json
```

**Options:**

- `--config`: Path to simulation config file (default: `config-test.json`)
- `--compose`: Path to docker-compose.yml file (required)
- `--requests`: Number of requests per service (default: 100)
- `--output`: Optional path to write JSON results

### 3. Test Running Architecture

Runs requests against an already-running Docker stack and measures performance:

```bash
python -m src.Docker test \
  --requests 10 \
  --output .output \
  --compose .output/20260428_104141/docker-compose.yml
```

**Options:**

- `--requests`: Number of requests per service (default: uses config value)
- `--output`: Output directory where the generated folder is located (default: `.output`)
- `--compose`: Optional path to specific docker-compose.yml; if omitted, searches `--output` for the most recent

**Measurement Results:**

- Per-request duration (milliseconds)
- Per-container resource consumption (CPU %)
- Mean request duration across all requests
- Mean resource usage across all containers
- Exports to `result.csv` in the output folder

### 4. Stop Docker Stack

Stops and removes all containers:

```bash
python -m src.Docker stop --output .output
```

**Options:**

- `--output`: Output directory to search for docker-compose.yml (default: `.output`)
- `--compose`: Optional specific path to docker-compose.yml

---

## Workflow Example

```bash
# 1. Build the Docker environment
python -m src.Docker build --config config-test.json --output .output

# 2. Run 10 requests and measure performance
python -m src.Docker test --requests 10 --output .output

# 3. Check the results
cat .output/*/result.csv

# 4. Stop the stack when done
python -m src.Docker stop --output .output
```

## Architecture Flow

1. **Configuration:** Each service has an **entrypoint** microservice (e.g., `Auth` for `IdentityService`)
2. **Request Flow:** When you call `/execute` on a service:
    - The entrypoint microservice is called
    - It executes and recursively calls all dependent microservices
    - Results bubble back up to the client
3. **Monitoring:**
    - Each request is timed from start to finish
    - Container CPU usage is sampled every 1 second
    - Aggregated statistics (means) are computed and exported to CSV

## Example Configuration

```json
{
	"requestCount": 10,
	"services": {
		"IdentityService": {
			"entrypoint": "Auth",
			"microservices": {
				"Auth": { "canRestart": true },
				"User": { "canRestart": true }
			}
		}
	},
	"microservices": {
		"Auth": {
			"dependencies": {
				"User": { "callRate": 1, "stopOnError": true }
			},
			"errorRate": 0.002,
			"workDifficulty": 0.2,
			"delay": 4
		},
		"User": {
			"dependencies": {},
			"errorRate": 0.001,
			"workDifficulty": 0.15,
			"delay": 2
		}
	},
	"containers": {
		"ContainerA": {
			"cpuLimit": 0.5,
			"services": {
				"IdentityService": { "canRestart": true }
			}
		}
	}
}
```

In this example, when you run 10 requests:

- Each request calls the `Auth` microservice (entrypoint)
- `Auth` then calls the `User` microservice (dependency with callRate: 1)
- The tester measures time from request start to complete response
- Container resource usage is tracked throughout
