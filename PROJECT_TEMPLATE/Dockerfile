# ---- base image with Python ----
FROM python:3.12-slim AS runtime

WORKDIR /app

# copy the server code
COPY rest_server.py .

# install only what we need
RUN pip install --no-cache-dir flask

# expose the app port
EXPOSE 8000

# default command
CMD ["python", "rest_server.py"]