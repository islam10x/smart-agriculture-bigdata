FROM apache/spark:3.5.0

USER root

# 1. Install system dependencies
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        python3-pip \
        python3-dev && \
    rm -rf /var/lib/apt/lists/*

# 2. Upgrade pip
RUN pip3 install --upgrade pip

# 3. Use system Python paths
ENV PYTHON_EXEC=/usr/bin/python3
ENV PIP_EXEC=/usr/bin/pip3

# 4. Copy requirements and install
COPY requirements.txt /tmp/requirements.txt
RUN $PIP_EXEC install --no-cache-dir -r /tmp/requirements.txt --default-timeout=600

# 5. Create app directories
RUN mkdir -p /opt/spark-apps /opt/spark-models && \
    chmod -R 755 /opt/spark-apps /opt/spark-models

# 6. Download MongoDB Spark Connector JARs
RUN mkdir -p /opt/spark/extra-jars && \
    curl -L -o /opt/spark/extra-jars/mongo-spark-connector_2.12-10.1.1.jar \
    https://repo1.maven.org/maven2/org/mongodb/spark/mongo-spark-connector_2.12/10.1.1/mongo-spark-connector_2.12-10.1.1.jar && \
    curl -L -o /opt/spark/extra-jars/mongodb-driver-sync-4.9.0.jar \
    https://repo1.maven.org/maven2/org/mongodb/mongodb-driver-sync/4.9.0/mongodb-driver-sync-4.9.0.jar && \
    curl -L -o /opt/spark/extra-jars/mongodb-driver-core-4.9.0.jar \
    https://repo1.maven.org/maven2/org/mongodb/mongodb-driver-core/4.9.0/mongodb-driver-core-4.9.0.jar && \
    curl -L -o /opt/spark/extra-jars/bson-4.9.0.jar \
    https://repo1.maven.org/maven2/org/mongodb/bson/4.9.0/bson-4.9.0.jar && \
    chmod -R 755 /opt/spark/extra-jars

# 7. Set Python for Spark
ENV PYSPARK_PYTHON=$PYTHON_EXEC
ENV PYSPARK_DRIVER_PYTHON=$PYTHON_EXEC
ENV PYTHONPATH=${PYTHONPATH}:/usr/lib/python3/dist-packages

USER 185