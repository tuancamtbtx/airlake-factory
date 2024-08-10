FROM apache/airflow:2.9.2-python3.9 

USER root

RUN apt-get update \
    && apt-get autoremove -yqq --purge \
    && apt-get install -y --no-install-recommends git \
    && apt-get install -y --no-install-recommends htop git libsnappy-dev liblzma-dev patch curl\
    && curl -fsSLo /usr/bin/kubectl "https://dl.k8s.io/release/v1.20.4/bin/linux/amd64/kubectl"\
    && chmod +x /usr/bin/kubectl\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
# set default timezone
RUN rm -f /etc/localtime && ln -s /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime

# our codes
RUN mkdir -p /bigdata/airfactory
COPY --chown=airflow:airflow . /bigdata/airfactory
COPY requirements.txt /
ENV PYTHONPATH=$PYTHONPATH:/bigdata/airfactory

COPY requirements.txt /
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt



ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini-static /usr/bin/tini
RUN chmod +x /usr/bin/tini

ENV AIRFLOW_HOME=/home/airflow/airflow

RUN mkdir -p $AIRFLOW_HOME
RUN chown airflow:airflow $AIRFLOW_HOME
