FROM l4t-release:32.5.2 AS l4t-32.5.2
FROM l4t-release:32.7.4 AS l4t-32.7.4
FROM l4t-release:35.4.1 AS l4t-35.4.1
FROM l4t-release:35.5.0 AS l4t-35.5.0
FROM l4t-release:35.6.0 AS l4t-35.6.0

FROM ubuntu:18.04 as mkimage

# Dependencies for building u-boot tools
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    gcc-aarch64-linux-gnu \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Download u-boot source
RUN git clone https://github.com/madisongh/u-boot-rockchip-downstream.git -b patches-2024.04-rockchip-v2017.09 --depth 1 u-boot
WORKDIR /u-boot
RUN make rk3568_defconfig && \
    echo CONFIG_FIT_SIGNATURE=y >> .config && \
    make olddefconfig && \
    make CROSS_COMPILE=aarch64-linux-gnu- tools

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

RUN pip3 install \
  PyYAML \
  cryptograpy \
  pycryptodome

ENV DIGSIGSERVER=/digsigserver
ENV DIGSIGSERVER_KEYFILE_URI=${DIGSIGSERVER}

WORKDIR ${DIGSIGSERVER}

COPY --from=l4t-32.5.2 /opt/nvidia /opt/nvidia
COPY --from=l4t-32.7.4 /opt/nvidia /opt/nvidia
COPY --from=l4t-35.4.1 /opt/nvidia /opt/nvidia
COPY --from=l4t-35.5.0 /opt/nvidia /opt/nvidia
COPY --from=l4t-35.6.0 /opt/nvidia /opt/nvidia
# Rockchip
ARG ROCKCHIP_TOOLS_REPO_URL=https://github.com/rockchip-linux/rkbin/raw/829d7a6a2272938aac67dfe9f807277fa617809b/
ENV DIGSIGSERVER_RK_TOOLS_PATH=/opt
ADD --chmod=755 ${ROCKCHIP_TOOLS_REPO_URL}/tools/rk_sign_tool ${DIGSIGSERVER_RK_TOOLS_PATH}/rkbin-tools/
ADD --chmod=755 ${ROCKCHIP_TOOLS_REPO_URL}/tools/setting.ini ${DIGSIGSERVER_RK_TOOLS_PATH}/rkbin-tools/
ADD --chmod=755 ${ROCKCHIP_TOOLS_REPO_URL}/tools/boot_merger ${DIGSIGSERVER_RK_TOOLS_PATH}/rkbin-tools/
COPY --from=mkimage /u-boot/tools/mkimage /usr/local/bin/

COPY digsigserver ${DIGSIGSERVER}/digsigserver
COPY requirements.txt ${DIGSIGSERVER}
COPY setup.cfg ${DIGSIGSERVER}
COPY setup.py ${DIGSIGSERVER}

RUN pip3 install -e .

CMD [ "digsigserver", "--debug" ]
