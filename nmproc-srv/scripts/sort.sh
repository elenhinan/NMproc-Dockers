#!/bin/bash
REMOTE_AET=$1
LOCAL_AET=$2
REMOTE_IP=$3
FOLDER=$4
DATA="/data"
JSON_FILE="${FOLDER}/studyinfo.json"
LOG_FILE="/var/log/nmproc.log"

echo "{" > $JSON_FILE
echo "   \"Local_AET\":   \"${LOCAL_AET}\"," >> $JSON_FILE
echo "   \"Remote_AET\":  \"${REMOTE_AET}\"," >> $JSON_FILE
echo "   \"Remote_Host\": \"${REMOTE_IP}\"" >> $JSON_FILE
echo "}" >> $JSON_FILE

# sort files
python3 /app/dicom_sorter.py ${FOLDER} ${DATA}

# cleanup
#rm -rf ${FOLDER}