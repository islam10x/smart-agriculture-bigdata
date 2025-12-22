#!/bin/bash

# Smart Agriculture Big Data Project - Setup Script
# This script initializes the entire project infrastructure

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="smart-agriculture-bigdata"
COMPOSE_FILE="docker-compose.yml"

# Functions
print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

check_requirements() {
    print_header "Checking Requirements"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_success "Docker is installed ($(docker --version))"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    print_success "Docker Compose is installed ($(docker-compose --version))"
    
    # Check available disk space
    AVAILABLE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt 30 ]; then
        print_error "Insufficient disk space. Need at least 30GB, have ${AVAILABLE_SPACE}GB"
        exit 1
    fi
    print_success "Sufficient disk space available (${AVAILABLE_SPACE}GB)"
    
    # Check available memory
    TOTAL_MEM=$(free -g | awk 'NR==2 {print $2}')
    if [ "$TOTAL_MEM" -lt 8 ]; then
        print_error "Insufficient RAM. Need at least 8GB, have ${TOTAL_MEM}GB"
        exit 1
    fi
    print_success "Sufficient memory available (${TOTAL_MEM}GB)"
}

create_directory_structure() {
    print_header "Creating Directory Structure"
    
    directories=(
        "data/raw/plant-disease"
        "data/processed"
        "data/models"
        "data/staging"
        "data/hdfs"
        "gateway/src"
        "gateway/config"
        "spark/batch_jobs"
        "spark/ml_models"
        "spark/computer_vision"
        "mongodb/init-scripts"
        "mongodb/schemas"
        "hadoop/hadoop-config"
        "hadoop/scripts"
        "postgres/init-scripts"
        "api/src/routes"
        "api/src/models"
        "api/src/database"
        "api/tests"
        "dashboard/src/components"
        "dashboard/src/services"
        "dashboard/public"
        "grafana/dashboards"
        "grafana/datasources"
        "docs"
        "scripts"
        "logs"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        print_success "Created $dir"
    done
}

create_env_file() {
    print_header "Creating Environment File"
    
    if [ -f ".env" ]; then
        print_info ".env file already exists, skipping..."
        return
    fi
    
    cat > .env << 'EOF'
# Smart Agriculture Big Data - Environment Variables

# API Keys
WEATHER_API_KEY=your_openweathermap_api_key_here

# MongoDB
MONGODB_URI=mongodb://admin:admin123@mongodb:27017/
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=admin123
MONGO_INITDB_DATABASE=agriculture

# PostgreSQL
POSTGRES_DB=agriculture_meta
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123

# Hadoop
CORE_CONF_fs_defaultFS=hdfs://namenode:9000
CLUSTER_NAME=agriculture-cluster

# Spark
SPARK_MASTER_URL=spark://spark-master:7077

# API
API_HOST=0.0.0.0
API_PORT=8000

# Dashboard
REACT_APP_API_URL=http://localhost:8000

# Grafana
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=admin123
EOF
    
    print_success "Created .env file"
    print_info "Please update .env with your actual API keys"
}

create_dockerfiles() {
    print_header "Creating Dockerfiles"
    
    # Gateway Dockerfile
    cat > gateway/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/

EXPOSE 5001

CMD ["python", "src/main.py"]
EOF
    print_success "Created gateway/Dockerfile"
    
    # API Dockerfile
    cat > api/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EOF
    print_success "Created api/Dockerfile"
    
    # Dashboard Dockerfile
    cat > dashboard/Dockerfile << 'EOF'
FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF
    print_success "Created dashboard/Dockerfile"
}

create_requirements_files() {
    print_header "Creating Requirements Files"
    
    # Gateway requirements
    cat > gateway/requirements.txt << 'EOF'
pymongo==4.6.0
requests==2.31.0
pandas==2.1.4
numpy==1.26.2
python-dotenv==1.0.0
fastapi==0.109.0
uvicorn==0.27.0
hdfs==2.7.0
EOF
    print_success "Created gateway/requirements.txt"
    
    # Spark requirements (included in container)
    cat > spark/requirements.txt << 'EOF'
pyspark==3.5.0
pymongo==4.6.0
pandas==2.1.4
numpy==1.26.2
scikit-learn==1.3.2
matplotlib==3.8.2
opencv-python==4.8.1.78
Pillow==10.1.0
EOF
    print_success "Created spark/requirements.txt"
    
    # API requirements
    cat > api/requirements.txt << 'EOF'
fastapi==0.109.0
uvicorn[standard]==0.27.0
motor==3.3.2
pydantic==2.5.3
pymongo==4.6.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pytest==7.4.3
httpx==0.26.0
EOF
    print_success "Created api/requirements.txt"
}

create_init_scripts() {
    print_header "Creating Database Init Scripts"
    
    # MongoDB init script
    cat > mongodb/init-scripts/init-db.js << 'EOF'
db = db.getSiblingDB('agriculture');

// Create collections
db.createCollection('sensor_data');
db.createCollection('disease_records');
db.createCollection('weather_data');
db.createCollection('alerts');
db.createCollection('analytics_results');

// Create indexes for sensor_data
db.sensor_data.createIndex({ "timestamp": -1 });
db.sensor_data.createIndex({ "sensor_id": 1, "timestamp": -1 });
db.sensor_data.createIndex({ "location.field_id": 1 });
db.sensor_data.createIndex({ "sensor_type": 1 });

// Create indexes for disease_records
db.disease_records.createIndex({ "detection_date": -1 });
db.disease_records.createIndex({ "field_id": 1 });
db.disease_records.createIndex({ "plant_type": 1 });
db.disease_records.createIndex({ "disease": 1 });
db.disease_records.createIndex({ "severity": 1 });

// Create indexes for alerts
db.alerts.createIndex({ "created_at": -1 });
db.alerts.createIndex({ "status": 1 });
db.alerts.createIndex({ "field_id": 1 });

print("MongoDB initialization completed successfully");
EOF
    print_success "Created mongodb/init-scripts/init-db.js"
    
    # PostgreSQL init script
    cat > postgres/init-scripts/create-tables.sql << 'EOF'
-- Create tables for metadata and analytics

CREATE TABLE IF NOT EXISTS fields (
    field_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location_lat DECIMAL(10, 7),
    location_lon DECIMAL(10, 7),
    area_hectares DECIMAL(10, 2),
    soil_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sensors (
    sensor_id VARCHAR(50) PRIMARY KEY,
    field_id VARCHAR(50) REFERENCES fields(field_id),
    sensor_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    last_maintenance DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS batch_jobs (
    job_id SERIAL PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',
    records_processed INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analytics_summary (
    id SERIAL PRIMARY KEY,
    analysis_date DATE NOT NULL,
    field_id VARCHAR(50),
    total_readings INTEGER,
    avg_temperature DECIMAL(5, 2),
    avg_moisture DECIMAL(5, 2),
    disease_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample fields
INSERT INTO fields (field_id, name, location_lat, location_lon, area_hectares, soil_type)
VALUES 
    ('FIELD_A', 'North Field', 36.8065, 10.1815, 5.5, 'clay_loam'),
    ('FIELD_B', 'South Field', 36.8045, 10.1825, 4.2, 'sandy_loam'),
    ('FIELD_C', 'East Field', 36.8055, 10.1835, 6.8, 'silt_loam')
ON CONFLICT (field_id) DO NOTHING;

-- Create indexes
CREATE INDEX idx_batch_jobs_created ON batch_jobs(created_at);
CREATE INDEX idx_analytics_date ON analytics_summary(analysis_date);
CREATE INDEX idx_sensors_field ON sensors(field_id);
EOF
    print_success "Created postgres/init-scripts/create-tables.sql"
}

create_hadoop_config() {
    print_header "Creating Hadoop Configuration"
    
    cat > hadoop/hadoop.env << 'EOF'
CORE_CONF_fs_defaultFS=hdfs://namenode:9000
CORE_CONF_hadoop_http_staticuser_user=root

HDFS_CONF_dfs_namenode_name_dir=file:///hadoop/dfs/name
HDFS_CONF_dfs_datanode_data_dir=file:///hadoop/dfs/data
HDFS_CONF_dfs_replication=2
HDFS_CONF_dfs_blocksize=134217728
HDFS_CONF_dfs_namenode_datanode_registration_ip___hostname___check=false

YARN_CONF_yarn_resourcemanager_hostname=resourcemanager
YARN_CONF_yarn_nodemanager_aux___services=mapreduce_shuffle
EOF
    print_success "Created hadoop/hadoop.env"
}

start_services() {
    print_header "Starting Docker Services"
    
    print_info "Building custom images..."
    docker-compose build
    
    print_info "Starting infrastructure services..."
    docker-compose up -d namenode datanode1 datanode2 datanode3 mongodb postgres
    
    print_info "Waiting for services to be ready (30 seconds)..."
    sleep 30
    
    print_info "Starting processing services..."
    docker-compose up -d spark-master spark-worker-1 spark-worker-2 spark-worker-3
    
    print_info "Starting application services..."
    docker-compose up -d gateway api dashboard grafana mongo-express
    
    print_success "All services started!"
}

check_services() {
    print_header "Checking Service Health"
    
    services=(
        "namenode:9870"
        "mongodb:27017"
        "spark-master:8080"
        "api:8000"
        "dashboard:3000"
    )
    
    for service in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service"
        if docker-compose ps | grep -q "$name.*Up"; then
            print_success "$name is running on port $port"
        else
            print_error "$name is not running"
        fi
    done
}

print_access_info() {
    print_header "Access Information"
    
    cat << EOF

${GREEN}Services are now running! Access them at:${NC}

📊 ${BLUE}React Dashboard:${NC}       http://localhost:3000
🔧 ${BLUE}FastAPI Docs:${NC}          http://localhost:8000/docs
⚡ ${BLUE}Spark Master UI:${NC}       http://localhost:8080
📂 ${BLUE}Hadoop NameNode:${NC}       http://localhost:9870
🗃️  ${BLUE}MongoDB Express:${NC}      http://localhost:8081
📈 ${BLUE}Grafana:${NC}               http://localhost:3001

${YELLOW}Default Credentials:${NC}
MongoDB:  admin / admin123
Grafana:  admin / admin123
Postgres: postgres / postgres123

${YELLOW}Next Steps:${NC}
1. Download Kaggle dataset:
   ./scripts/load-kaggle-data.sh

2. Start IoT simulator:
   docker-compose exec gateway python src/sensor_simulator.py

3. Run Spark batch jobs:
   ./scripts/run-batch-job.sh disease_analytics

${BLUE}For logs:${NC} docker-compose logs -f
${BLUE}To stop:${NC} docker-compose down

EOF
}

main() {
    print_header "Smart Agriculture Big Data - Setup"
    
    check_requirements
    create_directory_structure
    create_env_file
    create_dockerfiles
    create_requirements_files
    create_init_scripts
    create_hadoop_config
    
    read -p "Do you want to start the services now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_services
        sleep 5
        check_services
        print_access_info
    else
        print_info "Setup completed. Run 'docker-compose up -d' when ready."
    fi
    
    print_success "Setup script completed successfully!"
}

# Run main function
main