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

USER airflow

COPY requirements.txt /
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt

WORKDIR $AIRFLOW_HOME

# user location for install python pacakges
RUN mkdir -p /home/airflow/.local/lib/python3.8/site-packages
RUN mkdir -p /home/airflow/airflow

