# -----------------------------------------------------------------------------
# Global Arguments
# -----------------------------------------------------------------------------
# Or a more recent UBI 9 tag if available
ARG BASE_UBI_IMAGE_TAG=9.6
ARG PYTHON_VERSION=3.12

# -----------------------------------------------------------------------------
# Base Layer
# -----------------------------------------------------------------------------
FROM registry.access.redhat.com/ubi9/ubi-minimal:${BASE_UBI_IMAGE_TAG} as base
ARG PYTHON_VERSION

ENV PYTHON_VERSION=${PYTHON_VERSION}

RUN microdnf -y update && \
    microdnf install -y \
    python${PYTHON_VERSION}-pip \
    python${PYTHON_VERSION}-wheel && \
    microdnf clean all

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /workspace

# -----------------------------------------------------------------------------
# Python Installer Layer (for creating a virtual environment)
# -----------------------------------------------------------------------------
FROM base as python-install
ARG PYTHON_VERSION

ENV VIRTUAL_ENV=/opt/mcp
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN microdnf install -y python${PYTHON_VERSION}-devel && \
    python${PYTHON_VERSION} -m venv $VIRTUAL_ENV && \
    . $VIRTUAL_ENV/bin/activate && \
    pip install --no-cache-dir --upgrade pip wheel uv && \
    microdnf clean all

# -----------------------------------------------------------------------------
# Development Layer (install dependencies)
# -----------------------------------------------------------------------------
FROM python-install as dev


# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt ./

RUN --mount=type=cache,id=pip-cache,target=/root/.cache/pip \
    --mount=type=cache,id=uv-cache,target=/root/.cache/uv \
    uv pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Builder Layer (build the application)
# -----------------------------------------------------------------------------
FROM dev as build

# Copy necessary files for building the wheel
COPY setup.py ./
COPY README.md ./
COPY LICENSE ./
COPY requirements.txt ./
COPY src ./src/

# Run setup.py from the project root (/workspace)
# Ensure python from venv is used
RUN $VIRTUAL_ENV/bin/python setup.py bdist_wheel --dist-dir=dist

# -----------------------------------------------------------------------------
# Final Production Layer
# -----------------------------------------------------------------------------
FROM python-install as final


ENV APP_USER_HOME=/home/mcp \
    APP_USER_NAME=mcp \
    APP_USER_UID=2000
ENV HOME=${APP_USER_HOME}

RUN useradd --uid ${APP_USER_UID} --gid 0 -d ${APP_USER_HOME} -m ${APP_USER_NAME} && \
    chown -R ${APP_USER_UID}:0 ${VIRTUAL_ENV} /workspace ${APP_USER_HOME} && \
    chmod -R g+rwx ${VIRTUAL_ENV} /workspace ${APP_USER_HOME}

# Copy the built wheel from the builder stage
# Source path is /workspace/dist in the 'build' stage
COPY --from=build /workspace/dist /workspace/dist

# Copy the application source code (needed for app.py to run directly)
# Source path is /workspace/src in the 'build' stage
COPY --from=build /workspace/src /workspace/src

# Install the wheel into the virtual environment
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN $VIRTUAL_ENV/bin/pip install --no-cache-dir /workspace/dist/*.whl && \
    rm -rf /workspace/dist

# Set WORKDIR to the directory containing app.py
WORKDIR ${APP_USER_HOME}

# Change to non-root user
USER ${APP_USER_UID}

# Command to run the application
ENTRYPOINT ["python", "-m", "ai_slack_assistant"]