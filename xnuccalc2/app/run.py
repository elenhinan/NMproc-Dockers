#!/usr/bin/python3
import os
import json
from xnuccalc import process_fids
from pynetdicom import AE
from inotify.adapters import Inotify
from inotify.constants import IN_CREATE, IN_ISDIR

monitor = "/data"
json_file = "studyinfo.json"
local_aet="NMPROC"
ip_adr="10.85.77.52"

def send_dicom(dcm, remote_host, remote_port, remote_aet, local_aet):
   # setup application entry
   ae = AE(local_aet)
   ae.add_requested_context(dcm.SOPClassUID, dcm.file_meta.TransferSyntaxUID)
   # Associated with peer
   assoc = ae.associate(remote_host, remote_port, ae_title=remote_aet)

   if assoc.is_established:
      status = assoc.send_c_store(dcm)
      # Check the status of the storage request
      if status:
         # If the storage request succeeded this will be 0x0000
         print(f"Sent succesfully to {remote_host}:{remote_port} ({remote_aet})")
      else:
         print('Connection timed out, was aborted or received invalid response')
         print('C-STORE request status: 0x{0:04x}'.format(status.Status))
   else:
      print(f"Could not connect to {remote_host}:{remote_port}")
   assoc.release()

def process_folder(path):
   # if file found, to stuff
	#read json
   with open(os.path.join(path,json_file)) as file:
      studyinfo = json.load(file)

   dcms = process_fids(path)
   if dcms:
      #send_dicom(dcm, studyinfo['Remote_Host'], 104, studyinfo['Remote_AET'], local_aet)
      for dcm in dcms:
         send_dicom(dcm, ip_adr, 104, studyinfo['Remote_AET'], local_aet)
   else:
      print(f"Processing of {path} failed")

# start monitoring data folder
i = Inotify()
i.add_watch(monitor, IN_CREATE)
print(f"Monitoring '{monitor}'")
for event in i.event_gen(yield_nones=False):
   (id, type_names, path, filename) = event
   
   # if new folder, watch for json file.
   if 'IN_ISDIR' in type_names:
      new_path = os.path.join(path, filename)
      print(f"Watching {new_path}")
      # check if file already exist, if so start processing job
      if os.path.isfile(os.path.join(new_path, json_file)):
         process_folder(new_path)
      else:
         i.add_watch(new_path, IN_CREATE)
   elif filename == json_file:
      i.remove_watch(path)
      process_folder(path)
