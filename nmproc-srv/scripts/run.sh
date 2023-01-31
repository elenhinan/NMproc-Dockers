#!/bin/bash
SCRATCH="/scratch"
SCRIPT="/app/sort.sh #a #c '#r' #p"
PORT="11112"
RCV_AET="NMPROC"
storescp -v -pm -sp -pdu 131072 +xa -aet ${RCV_AET} -tos 3 -od "${SCRATCH}" -xcs "${SCRIPT}" ${PORT}