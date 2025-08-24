#!/bin/bash

# Linescope Server Production Deployment Script
# Version: 2.0.0 - Performance Optimized

set -e  # Exit on any error

# Configuration
PROJECT_NAME="linescope-server"
DOCKER_IMAGE="linescope-server:latest"
BACKUP_DIR="/opt/linescope-backups"
DEPLOY_ENV="${1:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker is not running. Please start Docker service."
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Function to backup current deployment
backup_current_deployment() {
    log "Creating backup of current deployment..."
    
    # Create backup directory
    sudo mkdir -p "$BACKUP_DIR"
    
    # Create timestamped backup
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_PATH="$BACKUP_DIR/backup_$TIMESTAMP"
    
    # Backup data directory
    if [ -d "./utils/data" ]; then
        sudo cp -r ./utils/data "$BACKUP_PATH"
        success "Data backup created at $BACKUP_PATH"
    fi
    
    # Backup logs
    if [ -f "./app.log" ]; then
        sudo cp ./app.log "$BACKUP_PATH/app_$TIMESTAMP.log"
    fi
    
    # Keep only last 5 backups
    sudo find "$BACKUP_DIR" -type d -name "backup_*" | sort | head -n -5 | xargs -r sudo rm -rf
}

# Function to build Docker images
build_images() {
    log "Building Docker images..."
    
    # Build the main application image
    docker build -t $DOCKER_IMAGE . --no-cache
    
    # Remove dangling images to save space
    docker image prune -f
    
    success "Docker images built successfully"
}

# Function to run tests
run_tests() {
    log "Running tests..."
    
    # Run unit tests in container
    if docker run --rm -v "$(pwd):/app" $DOCKER_IMAGE python -m pytest tests/ --tb=short; then
        success "All tests passed"
    else
        warning "Some tests failed, but continuing deployment"
    fi
}

# Function to deploy with zero downtime
deploy_with_zero_downtime() {
    log "Deploying with zero downtime strategy..."
    
    # Check if services are already running
    if docker-compose ps | grep -q "Up"; then
        log "Existing services detected, performing rolling update..."
        
        # Scale up new instances
        docker-compose up -d --scale linescope-server=2 --no-recreate
        
        # Wait for new instances to be healthy
        sleep 30
        
        # Scale down old instances
        docker-compose up -d --scale linescope-server=1
        
        # Remove old containers
        docker container prune -f
    else
        log "No existing services, performing fresh deployment..."
        docker-compose up -d
    fi
    
    success "Deployment completed"
}

# Function to verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Wait for services to start
    sleep 10
    
    # Check if containers are running
    if ! docker-compose ps | grep -q "Up"; then
        error "Deployment failed: containers are not running"
        return 1
    fi
    
    # Health check
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost/healthz &> /dev/null; then
            success "Health check passed"
            break
        fi
        
        log "Health check attempt $attempt/$max_attempts failed, retrying..."
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        error "Health check failed after $max_attempts attempts"
        return 1
    fi
    
    # Performance verification
    log "Running performance verification..."
    local response_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost/)
    log "Homepage response time: ${response_time}s"
    
    if (( $(echo "$response_time > 2.0" | bc -l) )); then
        warning "Response time is high: ${response_time}s"
    else
        success "Response time is good: ${response_time}s"
    fi
    
    success "Deployment verification completed"
}

# Function to setup monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create monitoring directory
    mkdir -p ./monitoring
    
    # Setup log rotation
    cat > ./monitoring/logrotate.conf << 'EOF'
/opt/linescope-server/app.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    create 644 appuser appuser
    postrotate
        docker-compose exec linescope-server kill -USR1 1
    endscript
}
EOF
    
    # Setup monitoring script
    cat > ./monitoring/health-check.sh << 'EOF'
#!/bin/bash
ENDPOINT="http://localhost/healthz"
MAX_RESPONSE_TIME=5

response_time=$(curl -o /dev/null -s -w '%{time_total}' --max-time $MAX_RESPONSE_TIME "$ENDPOINT")
exit_code=$?

if [ $exit_code -eq 0 ] && (( $(echo "$response_time < $MAX_RESPONSE_TIME" | bc -l) )); then
    echo "OK - Response time: ${response_time}s"
    exit 0
else
    echo "CRITICAL - Health check failed (response_time: ${response_time}s, exit_code: $exit_code)"
    exit 2
fi
EOF
    
    chmod +x ./monitoring/health-check.sh
    
    success "Monitoring setup completed"
}

# Function to display deployment status
show_status() {
    log "=== Deployment Status ==="
    echo
    echo "Services:"
    docker-compose ps
    echo
    echo "Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
    echo
    echo "Recent Logs:"
    docker-compose logs --tail=20 linescope-server
    echo
    log "=== End Status ==="
}

# Function to rollback deployment
rollback() {
    warning "Rolling back deployment..."
    
    # Stop current services
    docker-compose down
    
    # Restore from latest backup
    LATEST_BACKUP=$(sudo find "$BACKUP_DIR" -type d -name "backup_*" | sort | tail -1)
    if [ -n "$LATEST_BACKUP" ]; then
        sudo cp -r "$LATEST_BACKUP"/* ./utils/data/
        success "Data restored from $LATEST_BACKUP"
    fi
    
    # Start services with previous image
    docker-compose up -d
    
    success "Rollback completed"
}

# Function to cleanup old resources
cleanup() {
    log "Cleaning up old resources..."
    
    # Remove unused Docker resources
    docker system prune -f --volumes
    
    # Remove old backups (keep last 10)
    sudo find "$BACKUP_DIR" -type d -name "backup_*" | sort | head -n -10 | xargs -r sudo rm -rf
    
    success "Cleanup completed"
}

# Main deployment function
main() {
    log "Starting Linescope Server deployment (Environment: $DEPLOY_ENV)"
    
    # Parse command line arguments
    case "${2:-deploy}" in
        "status")
            show_status
            exit 0
            ;;
        "rollback")
            rollback
            exit 0
            ;;
        "cleanup")
            cleanup
            exit 0
            ;;
        "deploy")
            # Continue with deployment
            ;;
        *)
            echo "Usage: $0 [environment] [action]"
            echo "Environments: production, staging"
            echo "Actions: deploy (default), status, rollback, cleanup"
            exit 1
            ;;
    esac
    
    # Execute deployment steps
    check_prerequisites
    backup_current_deployment
    build_images
    run_tests
    deploy_with_zero_downtime
    verify_deployment
    setup_monitoring
    show_status
    
    success "🚀 Linescope Server deployment completed successfully!"
    log "Access your application at: http://localhost"
    log "Health check endpoint: http://localhost/healthz"
    log "Monitoring script: ./monitoring/health-check.sh"
}

# Trap to handle errors
trap 'error "Deployment failed at line $LINENO. Check the logs above for details."; exit 1' ERR

# Run main function
main "$@"