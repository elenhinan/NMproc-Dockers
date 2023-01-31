# based on cuda 10.0 running on ubuntu 18.04 host
#FROM nvidia/cuda:11.4.2-cudnn8-runtime-ubuntu20.04
FROM nvidia/cuda:11.4.2-cudnn8-devel-ubuntu20.04

# ready ubuntu environment
# python 2.7 for FSL
# python 3.7 for DeepAC
RUN \
  apt-get update \
  && apt-get upgrade -y \
  && apt-get install -y \
    python \
    python3 \
    python3-pip \
    wget \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* /var/log/*

# install FSL
RUN \
  cd /tmp && \
  wget https://git.fmrib.ox.ac.uk/fsl/conda/installer/-/raw/master/fsl/installer/fslinstaller.py && \
  python ./fslinstaller.py -d /usr/local/fsl && \
  cd && \
  rm /tmp/*

# install DeepAC
COPY files/DeepMRAC /app/DeepMRAC
RUN \
  cd /app/DeepMRAC \
  python3 -m pip install --upgrade pip setuptools \
  && python3 -m pip install -r requirements.txt \
  && python3 ./install.py

WORKDIR /app
COPY files/app/* /app
RUN \
  pip install -r /app/requirements.txt && \
  ln -s DeepMRAC/scripts/DeepMRAC.py DeepMRAC.py

ENTRYPOINT [ "/app/run.py" ]
ENV PYTHONUNBUFFERED=1
