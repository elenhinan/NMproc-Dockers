FROM alpine:3.16
# install dcmtk
RUN apk update && \
    apk add --no-cache libstdc++ g++ bash make cmake git && \
    cd /tmp && \
    git clone https://github.com/DCMTK/dcmtk.git && \
    mkdir dcmtk-build && \
    cd dcmtk-build && \
    cmake -DCMAKE_CXX_STANDARD=11 ../dcmtk && \
    make -j8 && \
    make install && \
    cd .. && \
    rm -rf * && \
    apk del g++ cmake git && \
    rm /var/cache/apk/*
# install python and pydicom
RUN apk add --update --no-cache python3 && \
    python3 -m ensurepip && \
    pip3 install --no-cache --upgrade pip setuptools pydicom
COPY scripts/ /app/
RUN mkdir -p /data /scratch
WORKDIR /app
EXPOSE 11112
ENTRYPOINT [ "/app/run.sh" ]
ENV PYTHONUNBUFFERED=1