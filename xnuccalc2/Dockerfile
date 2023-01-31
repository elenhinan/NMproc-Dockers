FROM alpine:3.16
# install python and pydicom
RUN apk add --update --no-cache bash python3 py3-numpy py3-scipy py3-matplotlib && \
    python3 -m ensurepip && \
    pip3 install --no-cache --upgrade pip setuptools
RUN pip3 install --no-cache \
        pydicom==2.3.1 \
        nibabel==4.0.2 \
        lmfit==1.0.3 \
        pynetdicom==2.0.2 \
        inotify==0.2.10
RUN mkdir -p /data
COPY app/ /app/
WORKDIR /app
ENTRYPOINT [ "/app/run.py" ]
ENV PYTHONUNBUFFERED=1