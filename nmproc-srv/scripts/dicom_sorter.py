#!/usr/bin/env python3
import pydicom
import sys
import os
import re
import json
from helpers import finddirs, findfiles
from rules import RuleSet
from datetime import datetime

def main():
	rulesets = []
	rulesdir = os.path.join(os.path.dirname(os.path.realpath(__file__)),'rulesets')
	for f in os.listdir(rulesdir):
		if f.endswith('.json'):
			print(f)
			rulefile = os.path.join(rulesdir,f)
			rulesets.append(RuleSet(rulefile))

	searchpath = sys.argv[1]
	files = findfiles(finddirs(searchpath))
	
	data_out = sys.argv[2]

	#read info.json
	try:
		with open(os.path.join(searchpath,'studyinfo.json')) as json_file:
			studyinfo = json.load(json_file)
	except:
		studyinfo = {}

	isotime = datetime.now().isoformat()

	n = len(files)
	n_dcm = 0
	print('')
	metadata_collection = []
	for i,path in zip(range(n),files):
		sys.stdout.write("\rScanning files %000d/%000d"%(i+1,n))
		sys.stdout.flush()
		metadata = {}
		metadata['studyinfo'] = studyinfo.copy() # copy data from json file
		metadata['fileinfo'] = {
			'isotime' : isotime,
			'filename': os.path.basename(path),
			'abspath' : os.path.abspath(path),
			'relpath' : os.path.dirname(path)
		}
		# split relative path into folders
		for lvl, folder in enumerate(filter(lambda x: x != "", reversed(metadata['fileinfo']['relpath'].split('/')))):
			metadata['fileinfo']['relpath%d'%lvl] = folder
		try:
			dcmfile = pydicom.filereader.read_file(path, stop_before_pixels=True)
			metadata['dicom'] = dcmfile
			metadata['isDicom'] = True
		except:
			metadata['isDicom'] = False
			metadata['dicom'] = {}
		# test file
		metadata_collection.append(metadata)
	sys.stdout.write('\n')

	# perform tests	
	for ruleset in rulesets:
		for metadata in metadata_collection:
			ruleset.testFile(metadata)
	# if tests succesful, do action
		if ruleset.testRequirements():
			for metadata in metadata_collection:
				ruleset.doAction(metadata, data_out)

if __name__ == '__main__':
	main()
