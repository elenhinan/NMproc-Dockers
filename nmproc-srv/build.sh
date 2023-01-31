#!/bin/bash
docker build \
   --build-arg http_proxy=http://proxy.ihelse.net:3128 \
   --tag nmproc-srv \
	.