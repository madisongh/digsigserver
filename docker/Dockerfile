FROM ubuntu:18.04

RUN apt-get update && apt-get install -y \
  device-tree-compiler \
  git \
  python2.7 \
  python3.7 \
  python3.7-dev \
  python3-pip \
  wget \
  && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python  python  /usr/bin/python2.7 1
RUN update-alternatives --install /usr/bin/python2 python2 /usr/bin/python2.7 1
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1

RUN pip3 install --upgrade pip

ENV DIGSIGSERVER=/digsigserver
ENV DIGSIGSERVER_KEYFILE_URI=${DIGSIGSERVER}

WORKDIR ${DIGSIGSERVER}

# digsigserver utilizes a helper script which is only available in later
# versions of the dunfell branch
RUN git clone --branch dunfell https://github.com/OE4T/meta-tegra.git meta-tegra-dunfell

# L4T 32.5.2

RUN mkdir -p /opt/nvidia/L4T-32.5.2-tegra210
RUN wget -q -O - https://developer.download.nvidia.com/embedded/L4T/r32_Release_v5.2/T210/Jetson-210_Linux_R32.5.2_aarch64.tbz2 | \
    tar -xjf - -C /opt/nvidia/L4T-32.5.2-tegra210
RUN wget -q -O - https://developer.download.nvidia.com/embedded/L4T/r32_Release_v5.2/T210/secureboot_R32.5.2_aarch64.tbz2 | \
    tar -xjf - -C /opt/nvidia/L4T-32.5.2-tegra210

RUN mkdir -p /opt/nvidia/L4T-32.5.2-tegra186
RUN wget -q -O - https://developer.download.nvidia.com/embedded/L4T/r32_Release_v5.2/T186/Jetson_Linux_R32.5.2_aarch64.tbz2 | \
    tar -xjf - -C /opt/nvidia/L4T-32.5.2-tegra186
RUN wget -q -O - https://developer.download.nvidia.com/embedded/L4T/r32_Release_v5.2/T186/secureboot_R32.5.2_aarch64.tbz2 | \
    tar -xjf - -C /opt/nvidia/L4T-32.5.2-tegra186

RUN git clone --branch dunfell-l4t-r32.5.0 https://github.com/OE4T/meta-tegra.git meta-tegra-dunfell-l4t-r32.5.0

ARG TEGRA210_32_5_2_DIR=/opt/nvidia/L4T-32.5.2-tegra210/Linux_for_Tegra
ARG TEGRA186_32_5_2_DIR=/opt/nvidia/L4T-32.5.2-tegra186/Linux_for_Tegra

RUN cd meta-tegra-dunfell-l4t-r32.5.0/recipes-bsp/tegra-binaries/tegra-helper-scripts && \
    install -m 0755 tegra210-flash-helper.sh ${TEGRA210_32_5_2_DIR}/bootloader/tegra210-flash-helper && \
    install -m 0755 tegra194-flash-helper.sh ${TEGRA186_32_5_2_DIR}/bootloader/tegra194-flash-helper && \
    install -m 0755 nvflashxmlparse.py ${TEGRA210_32_5_2_DIR}/bootloader/nvflashxmlparse

RUN cd meta-tegra-dunfell/recipes-bsp/tegra-binaries/tegra-helper-scripts && \
    install -m 0755 tegra-signimage-helper.sh ${TEGRA210_32_5_2_DIR}/tegra-signimage-helper && \
    install -m 0755 tegra-signimage-helper.sh ${TEGRA186_32_5_2_DIR}/tegra-signimage-helper

RUN patch -p1 --directory=${TEGRA210_32_5_2_DIR} < meta-tegra-dunfell-l4t-r32.5.0/recipes-bsp/tegra-binaries/files/0002-Fix-typo-in-l4t_bup_gen.func.patch
RUN patch -p1 --directory=${TEGRA186_32_5_2_DIR} < meta-tegra-dunfell-l4t-r32.5.0/recipes-bsp/tegra-binaries/files/0002-Fix-typo-in-l4t_bup_gen.func.patch
RUN patch -p1 --directory=${TEGRA210_32_5_2_DIR} < meta-tegra-dunfell-l4t-r32.5.0/recipes-bsp/tegra-binaries/files/0008-Skip-qspi-sd-specific-entries-for-other-t210-BUP-pay.patch

# L4T 32.7.3

RUN mkdir -p /opt/nvidia/L4T-32.7.3-tegra210
RUN wget -q -O - https://developer.nvidia.com/downloads/remetpack-463r32releasev73t210jetson-210linur3273aarch64tbz2 | \
    tar -xjf - -C /opt/nvidia/L4T-32.7.3-tegra210
RUN wget -q -O - https://developer.nvidia.com/downloads/remsdksjetpack-463r32releasev73t210securebootr3273aarch64tbz2 | \
    tar -xjf - -C /opt/nvidia/L4T-32.7.3-tegra210

RUN mkdir -p /opt/nvidia/L4T-32.7.3-tegra186
RUN wget -q -O - https://developer.nvidia.com/downloads/remksjetpack-463r32releasev73t186jetsonlinur3273aarch64tbz2 | \
    tar -xjf - -C /opt/nvidia/L4T-32.7.3-tegra186
RUN wget -q -O - https://developer.nvidia.com/downloads/remsdksjetpack-463r32releasev73t186securebootr3273aarch64tbz2 | \
    tar -xjf - -C /opt/nvidia/L4T-32.7.3-tegra186

ARG TEGRA210_32_7_3_DIR=/opt/nvidia/L4T-32.7.3-tegra210/Linux_for_Tegra
ARG TEGRA186_32_7_3_DIR=/opt/nvidia/L4T-32.7.3-tegra186/Linux_for_Tegra

RUN cd meta-tegra-dunfell/recipes-bsp/tegra-binaries/tegra-helper-scripts && \
    install -m 0755 tegra210-flash-helper.sh ${TEGRA210_32_7_3_DIR}/bootloader/tegra210-flash-helper && \
    install -m 0755 tegra194-flash-helper.sh ${TEGRA186_32_7_3_DIR}/bootloader/tegra194-flash-helper && \
    install -m 0755 tegra-signimage-helper.sh ${TEGRA210_32_7_3_DIR}/tegra-signimage-helper && \
    install -m 0755 tegra-signimage-helper.sh ${TEGRA186_32_7_3_DIR}/tegra-signimage-helper && \
    install -m 0755 nvflashxmlparse.py ${TEGRA210_32_7_3_DIR}/bootloader/nvflashxmlparse

RUN patch -p1 --directory=${TEGRA210_32_7_3_DIR} < meta-tegra-dunfell/recipes-bsp/tegra-binaries/files/0013-Fix-location-of-bsp_version-file-in-l4t_bup_gen.func.patch
RUN patch -p1 --directory=${TEGRA186_32_7_3_DIR} < meta-tegra-dunfell/recipes-bsp/tegra-binaries/files/0013-Fix-location-of-bsp_version-file-in-l4t_bup_gen.func.patch

COPY digsigserver ${DIGSIGSERVER}/digsigserver
COPY requirements.txt ${DIGSIGSERVER}
COPY setup.cfg ${DIGSIGSERVER}
COPY setup.py ${DIGSIGSERVER}

RUN pip3 install -e .

CMD [ "digsigserver", "--debug" ]
