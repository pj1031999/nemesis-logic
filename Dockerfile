FROM debian:stretch-slim
LABEL maintainer "Paweł Jasiak contact@jasiak.xyz"

RUN apt-get update && apt-get install -y    \
    build-essential \
    protobuf-compiler   \
    python3-protobuf    \
    libzmq5 \
    python3-zmq \
    git \
    python3-sqlalchemy  \
    python3-psycopg2    \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root
COPY . /root
RUN make install

ENV PATH=/usr/local/bin:/usr/local/sbin:$PATH
ENV PYTHONPATH=/usr/local/lib/nemesis/python:$PYTHONPATH

ENTRYPOINT ["logic"]
