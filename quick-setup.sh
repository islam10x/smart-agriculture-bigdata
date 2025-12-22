#!/bin/bash
# ===========================================================
# SMART AGRICULTURE BIG DATA - QUICK SETUP SCRIPT
# Copy and paste this entire script to set up the project
# ===========================================================

set -e

PROJECT_DIR="smart-agriculture-bigdata"

echo "🌾 Creating Smart Agriculture Big Data Project..."


# Create all directories
mkdir -p {gateway/{src,config},api/src/{routes,models,database,tests},dashboard/{src/{components,services},public},spark/{batch_jobs,ml_models},hadoop/hadoop-config,mongodb/init-scripts,postgres/init-scripts,grafana/{datasources,dashboards},scripts,data/{raw,processed,staging}}

# ===========================================================
# GATEWAY SERVICE FILES
# ===========================================================

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

cat > gateway/requirements.txt << 'EOF'
pymongo==4.6.0
requests==2.31.0
fastapi==0.109.0
uvicorn==0.27.0
python-dotenv==1.0.0
EOF

cat > gateway/src/main.py << 'EOF'
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Agriculture Gateway Service")

@app.get("/")
async def root():
    return {"service": "gateway", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)
EOF

cat > gateway/config/sensors_config.json << 'EOF'
{
  "fields": ["FIELD_A", "FIELD_B", "FIELD_C"],
  "soil_sensors_per_field": 5,
  "atmospheric_sensors_per_field": 1,
  "sampling_interval_seconds": 60,
  "base_location": {
    "latitude": 36.8065,
    "longitude": 10.1815
  }
}
EOF

touch gateway/src/__init__.py gateway/config/__init__.py

# ===========================================================
# API SERVICE FILES
# ===========================================================

cat > api/Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EOF

cat > api/requirements.txt << 'EOF'
fastapi==0.109.0
uvicorn[standard]==0.27.0
motor==3.3.2
pydantic==2.5.3
pymongo==4.6.0
python-dotenv==1.0.0
EOF

# Use the FastAPI code from the artifact - simplified version here
cat > api/src/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Smart Agriculture API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"name": "Smart Agriculture API", "status": "operational"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
EOF

touch api/src/{__init__,routes/__init__,models/__init__,database/__init__,tests/__init__}.py

# ===========================================================
# DASHBOARD FILES
# ===========================================================

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

cat > dashboard/package.json << 'EOF'
{
  "name": "agriculture-dashboard",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build"
  },
  "browserslist": {
    "production": [">0.2%", "not dead"],
    "development": ["last 1 chrome version"]
  }
}
EOF

cat > dashboard/nginx.conf << 'EOF'
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

cat > dashboard/public/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Smart Agriculture</title>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
EOF

cat > dashboard/src/index.jsx << 'EOF'
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<React.StrictMode><App /></React.StrictMode>);
EOF

cat > dashboard/src/App.jsx << 'EOF'
import React from 'react';
function App() {
  return (
    <div style={{padding:'20px',fontFamily:'Arial'}}>
      <h1>🌾 Smart Agriculture Dashboard</h1>
      <p>System Running!</p>
    </div>
  );
}
export default App;
EOF

# ===========================================================
# HADOOP FILES
# ===========================================================

cat > hadoop/hadoop.env << 'EOF'
CORE_CONF_fs_defaultFS=hdfs://namenode:9000
HDFS_CONF_dfs_replication=2
EOF

# ===========================================================
# MONGODB FILES
# ===========================================================

cat > mongodb/init-scripts/init-db.js << 'EOF'
db = db.getSiblingDB('agriculture');
db.createCollection('sensor_data');
db.createCollection('disease_records');
db.sensor_data.createIndex({"timestamp": -1});
print("MongoDB initialized");
EOF

# ===========================================================
# POSTGRESQL FILES
# ===========================================================

cat > postgres/init-scripts/create-tables.sql << 'EOF'
CREATE TABLE fields (
    field_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100)
);
INSERT INTO fields VALUES 
    ('FIELD_A', 'North Field'),
    ('FIELD_B', 'South Field');
EOF

# ===========================================================
# GRAFANA FILES
# ===========================================================

cat > grafana/datasources/datasources.yml << 'EOF'
apiVersion: 1
datasources:
  - name: MongoDB
    type: grafana-mongodb-datasource
    url: mongodb://admin:admin123@mongodb:27017/agriculture
EOF

# ===========================================================
# DOCKER COMPOSE
# ===========================================================

cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  namenode:
    image: bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8
    ports: ["9870:9870"]
    environment:
      CLUSTER_NAME: agriculture
    env_file: ./hadoop/hadoop.env
    volumes: ["hadoop_namenode:/hadoop/dfs/name"]

  mongodb:
    image: mongo:7.0
    ports: ["27017:27017"]
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: admin123
    volumes:
      - mongodb_data:/data/db
      - ./mongodb/init-scripts:/docker-entrypoint-initdb.d

  postgres:
    image: postgres:16
    ports: ["5432:5432"]
    environment:
      POSTGRES_PASSWORD: postgres123
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres/init-scripts:/docker-entrypoint-initdb.d

  spark-master:
    image: bitnami/spark:3.5
    ports: ["8080:8080", "7077:7077"]
    environment:
      SPARK_MODE: master
    volumes: ["./spark/batch_jobs:/opt/spark-apps"]

  gateway:
    build: ./gateway
    ports: ["5001:5001"]
    depends_on: [mongodb]

  api:
    build: ./api
    ports: ["8000:8000"]
    depends_on: [mongodb]

  dashboard:
    build: ./dashboard
    ports: ["3000:80"]

volumes:
  hadoop_namenode:
  mongodb_data:
  postgres_data:
EOF

# ===========================================================
# SCRIPTS
# ===========================================================

cat > scripts/health-check.sh << 'EOF'
#!/bin/bash
echo "Checking services..."
docker-compose ps
EOF

cat > .env << 'EOF'
WEATHER_API_KEY=your_key_here
MONGODB_URI=mongodb://admin:admin123@mongodb:27017/
EOF

cat > .gitignore << 'EOF'
__pycache__/
node_modules/
.env
data/raw/
*.log
EOF

chmod +x scripts/*.sh

# ===========================================================
# DONE
# ===========================================================

echo ""
echo "✅ Project structure created!"
echo ""
echo "📋 Next steps:"
echo "1. cd $PROJECT_DIR"
echo "2. docker-compose up -d"
echo "3. Open http://localhost:3000"
echo ""
echo "🌐 Services will be at:"
echo "  - Dashboard: http://localhost:3000"
echo "  - API: http://localhost:8000"
echo "  - Spark: http://localhost:8080"
echo "  - Hadoop: http://localhost:9870"
echo ""