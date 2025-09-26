#!/bin/bash

# Weather Intelligence Platform Deployment Script
# Deploys the complete real-time weather analytics platform

set -e  # Exit on any error

# Configuration
PROJECT_NAME="weather-intelligence"
ENVIRONMENT="${ENVIRONMENT:-dev}"
AZURE_REGION="${AZURE_REGION:-eastus2}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Azure CLI is installed
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install it first."
        exit 1
    fi
    
    # Check Azure login
    if ! az account show &> /dev/null; then
        log_error "Not logged into Azure. Please run 'az login' first."
        exit 1
    fi
    
    log_success "All prerequisites satisfied"
}

# Setup Python environment
setup_python_environment() {
    log_info "Setting up Python environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
        log_info "Created Python virtual environment"
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_success "Installed Python dependencies"
    else
        log_warning "requirements.txt not found"
    fi
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    log_info "Deploying Azure infrastructure with Terraform..."
    
    cd infrastructure/terraform
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    terraform plan \
        -var="project_name=${PROJECT_NAME}" \
        -var="environment=${ENVIRONMENT}" \
        -var="location=${AZURE_REGION}" \
        -out=tfplan
    
    # Apply deployment
    terraform apply tfplan
    
    # Get outputs
    EVENTHUB_CONNECTION_STRING=$(terraform output -raw eventhub_connection_string)
    KUSTO_CLUSTER_URI=$(terraform output -raw kusto_cluster_uri)
    KUSTO_DATABASE_NAME=$(terraform output -raw kusto_database_name)
    APPLICATION_INSIGHTS_KEY=$(terraform output -raw application_insights_key)
    STORAGE_ACCOUNT_NAME=$(terraform output -raw storage_account_name)
    RESOURCE_GROUP_NAME=$(terraform output -raw resource_group_name)
    
    cd ../..
    
    log_success "Infrastructure deployed successfully"
}

# Create environment configuration
create_environment_config() {
    log_info "Creating environment configuration..."
    
    # Create .env file from template
    if [ -f ".env.template" ]; then
        cp .env.template .env
        
        # Replace placeholders with actual values
        sed -i "s|your_subscription_id_here|$(az account show --query id -o tsv)|g" .env
        sed -i "s|weather-intelligence-rg|${RESOURCE_GROUP_NAME}|g" .env
        sed -i "s|Endpoint=sb://your-namespace.servicebus.windows.net/.*|${EVENTHUB_CONNECTION_STRING}|g" .env
        sed -i "s|https://your-cluster.westus2.kusto.windows.net|${KUSTO_CLUSTER_URI}|g" .env
        sed -i "s|WeatherIntelligence|${KUSTO_DATABASE_NAME}|g" .env
        sed -i "s|your_application_insights_key_here|${APPLICATION_INSIGHTS_KEY}|g" .env
        
        log_success "Environment configuration created"
    else
        log_error ".env.template not found"
        exit 1
    fi
}

# Setup Kusto database schema
setup_kusto_schema() {
    log_info "Setting up Kusto database schema..."
    
    # Activate Python environment
    source .venv/bin/activate
    
    # Run schema setup script
    python3 -c "
from src.kusto.kusto_client import WeatherKustoClient
from config.config import Config

config = Config()
client = WeatherKustoClient(config)

if client.initialize_clients():
    success = client.create_database_schema()
    if success:
        print('Kusto schema created successfully')
        client.optimize_for_dashboards()
        print('Dashboard optimizations applied')
    else:
        print('Failed to create Kusto schema')
    client.close_connections()
else:
    print('Failed to initialize Kusto clients')
"
    
    log_success "Kusto database schema configured"
}

# Test the deployment
test_deployment() {
    log_info "Testing deployment..."
    
    # Activate Python environment
    source .venv/bin/activate
    
    # Run basic connectivity tests
    python3 -c "
import asyncio
from src.data_ingestion.weather_api_client import WeatherAPIClient
from config.config import Config

async def test_weather_api():
    config = Config()
    async with WeatherAPIClient(config) as client:
        weather_data = await client.fetch_all_regions()
        print(f'Weather API test: Retrieved {len(weather_data)} weather readings')
        return len(weather_data) > 0

result = asyncio.run(test_weather_api())
if result:
    print('✓ Weather API connectivity test passed')
else:
    print('✗ Weather API connectivity test failed')
"
    
    log_success "Deployment testing completed"
}

# Deploy Power BI dashboard
deploy_dashboard() {
    log_info "Deploying Power BI dashboard..."
    
    # Check if PowerShell is available
    if command -v pwsh &> /dev/null; then
        # Run PowerShell deployment script
        cd dashboards
        
        # Generate dashboard configuration
        python3 -c "
from powerbi_config import PowerBIDashboardConfig, DashboardDeployment

config = PowerBIDashboardConfig()
deployment = DashboardDeployment(config)

# Save configuration files
with open('dashboard_config.json', 'w') as f:
    f.write(config.get_dashboard_json())

with open('deploy_dashboard.ps1', 'w') as f:
    f.write(deployment.create_deployment_script())

print('Dashboard configuration files generated')
"
        
        cd ..
        log_success "Dashboard configuration prepared"
        log_warning "Run 'pwsh dashboards/deploy_dashboard.ps1' to deploy Power BI dashboard"
    else
        log_warning "PowerShell not available. Dashboard deployment skipped."
    fi
}

# Create systemd service (for Linux deployment)
create_service() {
    log_info "Creating systemd service..."
    
    SERVICE_FILE="/etc/systemd/system/weather-intelligence.service"
    CURRENT_DIR=$(pwd)
    
    sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=Weather Intelligence Platform
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/.venv/bin
ExecStart=$CURRENT_DIR/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Enable and start service
    sudo systemctl daemon-reload
    sudo systemctl enable weather-intelligence
    
    log_success "Systemd service created and enabled"
}

# Main deployment function
deploy() {
    log_info "Starting Weather Intelligence Platform deployment..."
    
    check_prerequisites
    setup_python_environment
    deploy_infrastructure
    create_environment_config
    setup_kusto_schema
    test_deployment
    deploy_dashboard
    
    # Ask if user wants to create service
    read -p "Create systemd service for automatic startup? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        create_service
    fi
    
    log_success "Weather Intelligence Platform deployed successfully!"
    
    # Display next steps
    echo
    echo "=== NEXT STEPS ==="
    echo "1. Configure your weather API key in .env file"
    echo "2. Test the platform: source .venv/bin/activate && python main.py"
    echo "3. Access monitoring: Check Application Insights in Azure Portal"
    echo "4. Deploy Power BI dashboard: Run PowerShell script in dashboards/"
    echo "5. Configure alerting: Update regional contacts in config/config.py"
    echo
    echo "=== RESOURCES CREATED ==="
    echo "Resource Group: ${RESOURCE_GROUP_NAME}"
    echo "Kusto Cluster: ${KUSTO_CLUSTER_URI}"
    echo "Event Hub Namespace: Check Azure Portal"
    echo
}

# Cleanup function
cleanup() {
    log_info "Cleaning up resources..."
    
    cd infrastructure/terraform
    terraform destroy \
        -var="project_name=${PROJECT_NAME}" \
        -var="environment=${ENVIRONMENT}" \
        -var="location=${AZURE_REGION}" \
        -auto-approve
    
    cd ../..
    
    log_success "Resources cleaned up successfully"
}

# Show usage
show_usage() {
    echo "Usage: $0 [deploy|cleanup|test]"
    echo
    echo "Commands:"
    echo "  deploy   - Deploy the complete platform"
    echo "  cleanup  - Remove all deployed resources"
    echo "  test     - Test the deployed platform"
    echo
    echo "Environment Variables:"
    echo "  ENVIRONMENT  - Deployment environment (dev|staging|prod) [default: dev]"
    echo "  AZURE_REGION - Azure region [default: eastus2]"
}

# Main script logic
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "cleanup")
        cleanup
        ;;
    "test")
        check_prerequisites
        setup_python_environment
        test_deployment
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        log_error "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac