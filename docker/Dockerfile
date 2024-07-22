FROM l4t-release:32.5.2 AS l4t-32.5.2
FROM l4t-release:32.7.4 AS l4t-32.7.4
FROM l4t-release:35.4.1 AS l4t-35.4.1
FROM l4t-release:35.5.0 AS l4t-35.5.0

FROM ubuntu:18.04

RUN apt-get update && apt-get install -y \
  device-tree-compiler \
  liblz4-tool \
  python2.7 \
  python3.7 \
  python3.7-dev \
  python3-pip \
  sbsigntool \
  && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python  python  /usr/bin/python2.7 1
RUN update-alternatives --install /usr/bin/python2 python2 /usr/bin/python2.7 1
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1

RUN pip3 install --upgrade pip

RUN pip3 install PyYAML

ENV DIGSIGSERVER=/digsigserver
ENV DIGSIGSERVER_KEYFILE_URI=${DIGSIGSERVER}

WORKDIR ${DIGSIGSERVER}

COPY --from=l4t-32.5.2 /opt/nvidia /opt/nvidia
COPY --from=l4t-32.7.4 /opt/nvidia /opt/nvidia
COPY --from=l4t-35.4.1 /opt/nvidia /opt/nvidia
COPY --from=l4t-35.5.0 /opt/nvidia /opt/nvidia

COPY digsigserver ${DIGSIGSERVER}/digsigserver
COPY requirements.txt ${DIGSIGSERVER}
COPY setup.cfg ${DIGSIGSERVER}
COPY setup.py ${DIGSIGSERVER}

RUN pip3 install -e .

CMD [ "digsigserver", "--debug" ]
