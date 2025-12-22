# 🌾 Smart Agriculture Big Data Platform

A comprehensive big data platform for smart agriculture that integrates IoT sensor data, disease detection using computer vision, and real-time analytics for precision farming.

## 📋 Overview

This platform leverages modern big data technologies to provide farmers and agricultural organizations with actionable insights from IoT sensors, weather data, and plant disease detection. The system is built using a microservices architecture with distributed data processing capabilities.

### Key Features

- **📊 Real-time IoT Data Processing**: Collect and process sensor data from agricultural fields (temperature, humidity, soil moisture, etc.)
- **🔬 Plant Disease Detection**: Computer vision-based disease detection using machine learning models
- **☁️ Weather Integration**: Real-time weather data integration for predictive analytics
- **📈 Advanced Analytics**: Spark-based batch processing for historical data analysis
- **🎯 Intelligent Alerts**: Automated alerting system for critical farming conditions
- **📊 Interactive Dashboards**: React-based web dashboard with real-time visualizations
- **🗄️ Distributed Storage**: HDFS-based distributed file system for large-scale data storage

## 🏗️ Architecture

The platform uses a modern microservices architecture with the following components:

```
┌─────────────────────────────────────────────────────────────┐
│                     React Dashboard (Port 3000)              │
│                   + Grafana Analytics (Port 3001)            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Port 8000)               │
└──────────┬────────────────────────────┬─────────────────────┘
           │                            │
           ▼                            ▼
┌──────────────────────┐    ┌──────────────────────────────┐
│   MongoDB (NoSQL)    │    │   PostgreSQL (Metadata)      │
│   - Sensor Data      │    │   - Fields & Sensors         │
│   - Disease Records  │    │   - Batch Jobs               │
│   - Weather Data     │    │   - Analytics Summary        │
└──────────────────────┘    └──────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Apache Spark Cluster (Batch Processing)         │
│         Master (8080) + 3 Workers (Spark 3.5.0)              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│            Hadoop HDFS Cluster (Distributed Storage)         │
│     NameNode (9870) + 3 DataNodes (Hadoop 3.2.1)             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│          Data Gateway Service (IoT Ingestion) (5001)         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│        Optional: Kafka + Zookeeper (Streaming)               │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Technology Stack

### Backend
- **FastAPI**: High-performance REST API framework
- **Python 3.11**: Core programming language
- **Motor**: Async MongoDB driver

### Big Data Processing
- **Apache Spark 3.5.0**: Distributed data processing
- **Apache Hadoop 3.2.1**: Distributed file system (HDFS)
- **PySpark**: Python interface for Spark

### Databases
- **MongoDB 7.0**: NoSQL database for sensor data and time-series
- **PostgreSQL 16**: Relational database for metadata and analytics

### Frontend
- **React 18.2**: Modern web framework
- **Grafana 10.2**: Data visualization and monitoring

### Machine Learning
- **scikit-learn**: Machine learning models
- **OpenCV**: Computer vision for disease detection
- **Pillow**: Image processing

### Optional Streaming
- **Apache Kafka 7.5**: Real-time data streaming
- **Zookeeper**: Kafka cluster coordination

### DevOps
- **Docker & Docker Compose**: Containerization and orchestration
- **Nginx**: Web server for frontend

## 📦 Project Structure

```
smart-agriculture-bigdata/
├── api/                    # FastAPI backend application
│   ├── src/
│   │   ├── routes/        # API endpoints
│   │   ├── models/        # Pydantic data models
│   │   └── database/      # Database connections
│   ├── tests/             # API tests
│   ├── Dockerfile
│   └── requirements.txt
│
├── dashboard/             # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   └── services/      # API service clients
│   ├── public/
│   ├── Dockerfile
│   └── package.json
│
├── gateway/               # Data ingestion gateway
│   ├── src/              # Gateway service code
│   ├── config/           # Configuration files
│   ├── Dockerfile
│   └── requirements.txt
│
├── spark/                 # Spark processing jobs
│   ├── batch_jobs/       # Batch processing scripts
│   ├── ml_models/        # ML model training
│   ├── computer_vision/  # Disease detection models
│   └── requirements.txt
│
├── data/                  # Data storage
│   ├── raw/              # Raw data files
│   ├── processed/        # Processed datasets
│   ├── models/           # Trained ML models
│   ├── staging/          # Staging area
│   └── hdfs/             # HDFS mount point
│
├── hadoop/                # Hadoop configuration
│   ├── hadoop-config/
│   ├── scripts/
│   └── hadoop.env
│
├── mongodb/               # MongoDB initialization
│   ├── init-scripts/     # Database init scripts
│   └── schemas/          # Collection schemas
│
├── postgres/              # PostgreSQL initialization
│   └── init-scripts/     # SQL init scripts
│
├── grafana/               # Grafana dashboards
│   ├── dashboards/       # Dashboard JSON files
│   └── datasources/      # Datasource configs
│
├── scripts/               # Utility scripts
│   └── health-check.sh   # Service health check
│
├── logs/                  # Application logs
├── docs/                  # Documentation
├── docker-compose.yml     # Docker orchestration
├── setup.sh              # Full setup script
├── quick-setup.sh        # Quick setup script
├── .env                  # Environment variables
└── README.md             # This file
```

## 🚀 Quick Start

### Prerequisites

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Minimum 8GB RAM**
- **Minimum 30GB free disk space**

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/islam10x/smart-agriculture-bigdata.git
   cd smart-agriculture-bigdata
   ```

2. **Run the automated setup script**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

   The setup script will:
   - Check system requirements
   - Create necessary directory structure
   - Generate environment files
   - Create Dockerfiles and init scripts
   - Start all Docker services

3. **Configure environment variables**
   ```bash
   # Edit .env file and add your API keys
   nano .env
   # Add your OpenWeatherMap API key
   WEATHER_API_KEY=your_api_key_here
   ```

### Manual Setup

If you prefer manual setup:

```bash
# 1. Create environment file
cp .env.example .env

# 2. Build and start services
docker-compose build
docker-compose up -d

# 3. Verify services are running
docker-compose ps
```

### Quick Setup (Existing Configuration)

```bash
chmod +x quick-setup.sh
./quick-setup.sh
```

## 🌐 Service Access

Once all services are running, access them at:

| Service | URL | Credentials |
|---------|-----|-------------|
| 📊 **React Dashboard** | http://localhost:3000 | - |
| 🔧 **FastAPI Docs** | http://localhost:8000/docs | - |
| ⚡ **Spark Master UI** | http://localhost:8080 | - |
| 📂 **Hadoop NameNode** | http://localhost:9870 | - |
| 🗃️ **MongoDB Express** | http://localhost:8081 | admin / admin123 |
| 📈 **Grafana** | http://localhost:3001 | admin / admin123 |
| 👷 **Spark Worker 1** | http://localhost:8082 | - |
| 👷 **Spark Worker 2** | http://localhost:8083 | - |
| 👷 **Spark Worker 3** | http://localhost:8084 | - |

### Database Access

**MongoDB**
```bash
# Connect to MongoDB
docker-compose exec mongodb mongosh -u admin -p admin123
```

**PostgreSQL**
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d agriculture_meta
```

## 📊 Usage Examples

### 1. Start IoT Sensor Simulator

```bash
docker-compose exec gateway python src/sensor_simulator.py
```

### 2. Run Spark Batch Jobs

```bash
# Run disease analytics job
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  /opt/spark-apps/disease_analytics.py

# Run data aggregation job
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  /opt/spark-apps/data_aggregation.py
```

### 3. Upload Data to HDFS

```bash
# Copy data to HDFS
docker-compose exec namenode hdfs dfs -put /data/sensor_data.csv /agriculture/
```

### 4. View Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f spark-master
```

### 5. Health Check

```bash
chmod +x scripts/health-check.sh
./scripts/health-check.sh
```

## 🔧 Configuration

### Environment Variables

Key environment variables in `.env`:

```bash
# API Keys
WEATHER_API_KEY=your_openweathermap_api_key

# MongoDB
MONGODB_URI=mongodb://admin:admin123@mongodb:27017/
MONGO_INITDB_DATABASE=agriculture

# PostgreSQL
POSTGRES_DB=agriculture_meta
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123

# Spark
SPARK_MASTER_URL=spark://spark-master:7077

# API
API_HOST=0.0.0.0
API_PORT=8000

# Dashboard
REACT_APP_API_URL=http://localhost:8000
```

### Scaling Workers

To add more Spark workers, edit `docker-compose.yml` and add additional worker services.

## 🧪 Testing

### API Tests

```bash
# Run API tests
docker-compose exec api pytest src/tests/
```

### Service Health Check

```bash
./scripts/health-check.sh
```

## 📚 API Documentation

Once the API service is running, access interactive API documentation at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🎯 Key Workflows

### 1. Sensor Data Pipeline

```
IoT Sensors → Gateway Service → MongoDB → Spark Processing → Analytics
```

### 2. Disease Detection Pipeline

```
Image Upload → Computer Vision Model → Disease Classification → Alert Generation
```

### 3. Weather Analytics Pipeline

```
Weather API → Gateway → MongoDB → Spark Aggregation → Dashboard Visualization
```

## 🛑 Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove all data (⚠️ WARNING: This deletes all data)
docker-compose down -v

# Stop specific service
docker-compose stop <service-name>
```

## 🔍 Monitoring

### View Resource Usage

```bash
# Docker stats
docker stats

# View Spark cluster status
# Open http://localhost:8080

# View Hadoop cluster status
# Open http://localhost:9870
```

### Grafana Dashboards

1. Navigate to http://localhost:3001
2. Login with `admin` / `admin123`
3. Explore pre-configured dashboards for:
   - Sensor data trends
   - Disease detection statistics
   - Weather patterns
   - System health metrics

## 🐛 Troubleshooting

### Service won't start

```bash
# Check logs
docker-compose logs <service-name>

# Restart specific service
docker-compose restart <service-name>

# Rebuild service
docker-compose build <service-name>
docker-compose up -d <service-name>
```

### Network issues

```bash
# Recreate network
docker-compose down
docker network prune
docker-compose up -d
```

### Storage issues

```bash
# Check HDFS status
docker-compose exec namenode hdfs dfsadmin -report

# Check disk usage
docker system df
```

## 🎓 Learning Resources

- [Apache Spark Documentation](https://spark.apache.org/docs/latest/)
- [Hadoop Documentation](https://hadoop.apache.org/docs/stable/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MongoDB Manual](https://docs.mongodb.com/)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For issues and questions, please create an issue in the repository.

## 🎯 Future Enhancements

- [ ] Real-time streaming with Kafka integration
- [ ] Mobile application for farmers
- [ ] Advanced ML models for crop yield prediction
- [ ] Integration with drone imagery
- [ ] Multi-language support
- [ ] Enhanced security with OAuth2
- [ ] Automated backup and disaster recovery
- [ ] Support for additional IoT protocols (MQTT, CoAP)

## 📊 Project Status

This project is actively maintained and under continuous development. Check the [issues](../../issues) page for planned features and known bugs.

---

**Built with ❤️ for sustainable agriculture and precision farming**
