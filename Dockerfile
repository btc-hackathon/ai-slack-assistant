FROM registry.access.redhat.com/ubi9/python-311

# Create a writable app directory
ENV APP_HOME=/opt/app
WORKDIR $APP_HOME

# Copy files first
COPY pyproject.toml ./

# Fix permissions to allow arbitrary UID to write
RUN mkdir -p $APP_HOME && \
    chmod -R g+rwX $APP_HOME && \
    chown -R 1001:0 $APP_HOME && \
    pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi

# Copy the rest of the code
COPY src/ ./src
COPY README.md LICENSE ./

# Expose the app port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=8080

# Default non-root user for OpenShift (will run as random UID)
USER 1001

CMD ["python", "src/app.py"]
