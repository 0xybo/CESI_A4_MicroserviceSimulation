"""Web service runner for ServiceA.

Auto-generated service that:
- Runs as a web server for inter-service communication
- Executes microservices as tasks
- Handles dependencies and failures
"""

import json
import logging
import random
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

logger = logging.getLogger(__name__)


class ServiceConfig:
    """Configuration for ServiceA service."""
    
    SERVICE_NAME = "ServiceA"
    PORT = 8000
    HOST = "0.0.0.0"
    
    DEPENDENCIES = {}
    
    MICROSERVICES = {
      "A": {
            "error_rate": 0.0,
            "latency": 0,
            "work_difficulty": 1.0,
            "dependencies": {
                  "B": {
                        "call_rate": 1.0,
                        "stop_on_error": true
                  },
                  "E": {
                        "call_rate": 1.0,
                        "stop_on_error": false
                  },
                  "F": {
                        "call_rate": 1.0,
                        "stop_on_error": false
                  },
                  "G": {
                        "call_rate": 1.0,
                        "stop_on_error": false
                  },
                  "H": {
                        "call_rate": 1.0,
                        "stop_on_error": false
                  },
                  "I": {
                        "call_rate": 1.0,
                        "stop_on_error": false
                  },
                  "J": {
                        "call_rate": 1.0,
                        "stop_on_error": false
                  }
            }
      },
      "B": {
            "error_rate": 0.0,
            "latency": 0,
            "work_difficulty": 1.0,
            "dependencies": {
                  "C": {
                        "call_rate": 1.0,
                        "stop_on_error": true
                  }
            }
      },
      "C": {
            "error_rate": 0.0,
            "latency": 0,
            "work_difficulty": 1.0,
            "dependencies": {}
      },
      "D": {
            "error_rate": 0.0,
            "latency": 0,
            "work_difficulty": 1.0,
            "dependencies": {
                  "E": {
                        "call_rate": 1.0,
                        "stop_on_error": true
                  },
                  "F": {
                        "call_rate": 1.0,
                        "stop_on_error": false
                  },
                  "K": {
                        "call_rate": 1.0,
                        "stop_on_error": false
                  },
                  "L": {
                        "call_rate": 1.0,
                        "stop_on_error": false
                  }
            }
      },
      "E": {
            "error_rate": 0.0,
            "latency": 0,
            "work_difficulty": 1.0,
            "dependencies": {}
      },
      "F": {
            "error_rate": 0.0,
            "latency": 0,
            "work_difficulty": 1.0,
            "dependencies": {}
      },
      "G": {
            "error_rate": 0.0,
            "latency": 0,
            "work_difficulty": 1.0,
            "dependencies": {}
      },
      "H": {
            "error_rate": 0.0,
            "latency": 0,
            "work_difficulty": 1.0,
            "dependencies": {
                  "C": {
                        "call_rate": 1.0,
                        "stop_on_error": true
                  }
            }
      },
      "I": {
            "error_rate": 0.0,
            "latency": 0,
            "work_difficulty": 1.0,
            "dependencies": {}
      },
      "J": {
            "error_rate": 0.0,
            "latency": 0,
            "work_difficulty": 1.0,
            "dependencies": {
                  "C": {
                        "call_rate": 1.0,
                        "stop_on_error": true
                  },
                  "D": {
                        "call_rate": 1.0,
                        "stop_on_error": false
                  }
            }
      },
      "K": {
            "error_rate": 0.0,
            "latency": 0,
            "work_difficulty": 1.0,
            "dependencies": {}
      },
      "L": {
            "error_rate": 0.0,
            "latency": 0,
            "work_difficulty": 1.0,
            "dependencies": {}
      }
}


class MicroserviceExecutor:
    """Executes microservices with simulated latency and errors."""
    
    def __init__(self):
        self.call_count = {}
        self.error_count = {}
    
    def execute_microservice(self, microservice_name: str) -> dict:
        """Execute a microservice task.
        
        Args:
            microservice_name: Name of the microservice to execute.
        
        Returns:
            Result dictionary with execution details.
        """
        if microservice_name not in ServiceConfig.MICROSERVICES:
            return {
                "status": "error",
                "message": f"Microservice {microservice_name} not found"
            }
        
        ms_config = ServiceConfig.MICROSERVICES[microservice_name]
        
        # Track calls
        self.call_count[microservice_name] = self.call_count.get(microservice_name, 0) + 1
        
        # Simulate latency
        latency_ms = ms_config.get("latency", 0)
        if latency_ms > 0:
            time.sleep(latency_ms / 1000.0)
        
        # Simulate errors
        error_rate = ms_config.get("error_rate", 0.0)
        if random.random() < error_rate:
            self.error_count[microservice_name] = self.error_count.get(microservice_name, 0) + 1
            return {
                "status": "error",
                "microservice": microservice_name,
                "message": "Simulated error"
            }
        
        return {
            "status": "success",
            "microservice": microservice_name,
            "latency_ms": latency_ms,
            "call_count": self.call_count[microservice_name]
        }
    
    def get_stats(self) -> dict:
        """Get execution statistics."""
        return {
            "calls": self.call_count,
            "errors": self.error_count
        }


class ServiceRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for service API."""
    
    microservice_executor = MicroserviceExecutor()
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "service": ServiceConfig.SERVICE_NAME,
                "status": "healthy"
            }
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == "/stats":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "service": ServiceConfig.SERVICE_NAME,
                "stats": self.microservice_executor.get_stats()
            }
            self.wfile.write(json.dumps(response).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests to execute microservices."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            request = json.loads(body)
            
            microservice_name = request.get("microservice")
            
            if not microservice_name:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                response = {
                    "error": "Missing microservice name"
                }
                self.wfile.write(json.dumps(response).encode())
                return
            
            # Execute the microservice
            result = self.microservice_executor.execute_microservice(microservice_name)
            
            # Send response
            status_code = 200 if result.get("status") == "success" else 500
            self.send_response(status_code)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "error": str(e)
            }
            self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass


def main():
    """Start the service web server."""
    server = HTTPServer(
        (ServiceConfig.HOST, ServiceConfig.PORT),
        ServiceRequestHandler
    )
    
    logger.info(
        "Service %s starting on port %s...",
        ServiceConfig.SERVICE_NAME,
        ServiceConfig.PORT,
    )
    logger.info("Microservices: %s", list(ServiceConfig.MICROSERVICES.keys()))
    logger.info("Dependencies: %s", ServiceConfig.DEPENDENCIES)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Service %s shutting down...", ServiceConfig.SERVICE_NAME)
        server.shutdown()


if __name__ == "__main__":
    main()
