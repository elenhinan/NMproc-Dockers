#!/usr/bin/python3
import os
import sys
import json
import numpy as np
import pydicom as dicom
from pynetdicom import AE
from inotify.adapters import Inotify
from inotify.constants import IN_CREATE, IN_ISDIR
from DeepMRAC import predict_DeepUTE
from datetime import datetime

monitor = ["/data/UTE"]
json_file = "studyinfo.json"
local_aet="NMPROC"
ip_adr="10.85.77.52"

def send_dicom(dcm, remote_host, remote_port, remote_aet, local_aet):
   # setup application entry
   ae = AE(local_aet)
   ae.add_requested_context(dcm[0].SOPClassUID, dcm[0].file_meta.TransferSyntaxUID)
   # Associated with peer
   assoc = ae.associate(remote_host, remote_port, ae_title=remote_aet)

   if assoc.is_established:
      sent_files = 0
      failed = False
      for d in dcm:
         status = assoc.send_c_store(d)
         if not status:
            print('Connection timed out, was aborted or received invalid response')
            failed = True
            break
         elif status.Status != 0x0000:
            print(f"Sending failed, error 0x{status.Status:04X}")
            failed = True
            break
         sent_files += 1
      # Check the status of the storage request
      if not failed:
         # If the storage request succeeded this will be 0x0000
         print(f"Sent {sent_files} files succesfully to {remote_host}:{remote_port} ({remote_aet})")
      assoc.release()

   return not failed

def nda2dcm(DeepX,umap_orig):  
   dcm = [] # ready list
   maxVal = int(DeepX.max()) # find max value of output
   newSIUID = dicom.uid.generate_uid(prefix='1.3.12.2.1107.5.2.38.51014.') # generate new Series Instance uid

   # Read each file in UMAP container, replace relevant tags
   for f in os.listdir(umap_orig):
      ds=dicom.read_file(os.path.join(umap_orig,f))

      # get z index
      z = int(ds.InstanceNumber)-1

      # change relevant tags and pixel data      
      ds.SeriesInstanceUID = newSIUID
      ds.SeriesDescription = "DeepUTE"
      ds.SeriesNumber = "505"
      ds.SOPInstanceUID = dicom.uid.generate_uid(prefix='1.3.12.2.1107.5.2.38.51014.')
      ds.LargestImagePixelValue = maxVal
      ds.PixelData = DeepX[z,:,:].astype(ds.pixel_array.dtype).tobytes() # Inserts actual image info

      # append dicom to list
      dcm.append(ds)
   
   # return dicoms
   return dcm

def dcm2nda(path):
   vol = np.empty((192,192,192), dtype=float)
   for filename in os.listdir(path):
      ds = dicom.dcmread(os.path.join(path, filename))
      z = int(ds.InstanceNumber)-1
      vol[z,:,:] = ds.pixel_array
   return vol

def get_paths(path):
   folder = [ f for f in os.listdir(path) if os.path.isdir(os.path.join(path,f))]
   folder.sort(key=lambda x: int(x.split('-')[0]))
   ute1_path = os.path.join(path,folder[0])
   ute2_path = os.path.join(path,folder[1])
   umap_path = os.path.join(path,folder[2])
   return ute1_path, ute2_path, umap_path


def process_ute(path):
	#read json
   with open(os.path.join(path,json_file)) as file:
      studyinfo = json.load(file)

   ute1_path, ute2_path, umap_path = get_paths(path)

   # process data
   ute1 = dcm2nda(ute1_path)
   ute2 = dcm2nda(ute2_path)
   print("UTE loaded")
   DeepX = predict_DeepUTE(ute1,ute2,'VE11P')
   print("uMap generated")
   umap = nda2dcm(DeepX, umap_path)
    
   # send result
   if len(umap) == 192:
      #send_dicom(umap, studyinfo['Remote_Host'], 104, studyinfo['Remote_AET'], local_aet)
      send_dicom(umap, ip_adr, 104, studyinfo['Remote_AET'], local_aet)
   else:
      print(f"Processing of {path} failed")

# start monitoring data folder
if __name__ == "__main__":
   if len(sys.argv) > 1:
      process_ute(sys.argv[1])
      exit()
   i = Inotify()
   for m in monitor:
      i.add_watch(m, IN_CREATE)
      print(f"Monitoring '{m}'")
   for event in i.event_gen(yield_nones=False):
      (id, type_names, path, filename) = event
      
      # if new folder, watch for json file.
      if 'IN_ISDIR' in type_names:
         if not path.rsplit('/',1)[0] in monitor:
            new_path = os.path.join(path, filename)
            print(f"Watching {new_path}")
            i.add_watch(new_path, IN_CREATE)
      elif filename == json_file:
         i.remove_watch(path)
         process_ute(path)
