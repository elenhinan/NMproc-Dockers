import os
import re
import json
import pydicom
from helpers import actions, operators

_alphanumeric = re.compile('[^\w/._\-]')

class RuleSet:
	def __init__(self, rulefile):
		with open(rulefile,'r') as fp:
			rules = json.load(fp)
			self.rules = []
			self.name = os.path.basename(rulefile)
			for params in rules:
				self.rules.append(Rule(**params))
				
	def testFile(self,fileinfo):
		fileinfo['success'] = False
		for rule in self.rules:
			success = rule.testFile(fileinfo)
			if success:
				fileinfo['newpath'] = rule.getNewPath(fileinfo)
				fileinfo['action'] = rule.action
				fileinfo['success'] = True
				break
		# sort list with latest matches on top to speed up sorting
		return None # or filepath

	def testRequirements(self):
		print(f"({self.name})")
		return all([r.testRequirement() for r in self.rules])

	def doAction(self, metadata, rootpath):
		if not metadata['success']:
			return
		abspath = metadata['fileinfo']['abspath']
		newpath = os.path.join(rootpath,metadata['newpath'])
		#if os.path.lexists(newpath):
		#	os.remove(newpath)
		actions[metadata['action']](abspath, newpath)



class Rule:
	# static regex parsers
	regex_placeholder = r'(?:(?:\{)(\w+)(?:\:\w+)?(?:\}))'
	regex_requirement = r'^n([<>=])(\d+)$'
	re_placeholder = re.compile(regex_placeholder)
	re_requirement = re.compile(regex_requirement)

	def __init__(self, name='default', destination='{name}/{filename}{ext}', action='move', tests=None, requirement=""):
		self.n = 0
		self.name = name
		self.destination = destination
		self.action = action
		self.requirement = Rule.re_requirement.findall(requirement)
		self.tests = [ValueTest(t) for t in tests]
		self.placeholders = Rule.re_placeholder.findall(destination)

	def testRequirement(self):
		if len(self.requirement) == 0:
			print(f"({self.name}) n: {self.n} (True)")
			return True
		op_, val_ = self.requirement[0]
		op = operators[op_]
		val = int(val_)
		res = op(self.n, val)
		print(f"\t({self.name}) n: {self.n} {op_} {val} ({res})")
		return res

	def testFile(self,fileinfo):
		success = all([vt.test(fileinfo) for vt in self.tests])
		self.n += success
		return success
	
	def getNewPath(self,metadata):
		values = {}
		for ph in self.placeholders:
			if ph in metadata['studyinfo']:
				values[ph] = metadata['studyinfo'][ph]
			elif ph in metadata['fileinfo']:
				values[ph] = metadata['fileinfo'][ph]
			elif ph in metadata['dicom']:
				values[ph] = metadata['dicom'].get(ph)
			else:
				#raise Exception('Key not found: %s, %s'%(ph,metadata['fileinfo']['filename']))
				values[ph] = 'None'
		return self.destination.format(**values)

class ValueTest:
	# static regex parsers
	regex_descriptor = r"(\w+)\(([\w,]+)\):(\w+)\((.*)\)$"
	desc_parser = re.compile(regex_descriptor)
	regex_math = r'^(<|>|<=|>=|=)((?:[0-9]+)(?:.[0-9]*)?)$'
	math_parser = re.compile(regex_math)

	def __init__(self, descriptor):
		match = ValueTest.desc_parser.match(descriptor)
		if match == None:
			print('Format error: %s'%descriptor)
			# throw exceptioncp /
		else:
			fieldtype, fieldname, testtype, testvalue = match.groups()
	
			if fieldtype == 'dicom':
				if ',' in fieldname:
					self.tag = int(fieldname.replace('0x','').replace(',',''),base=16)
				else:
					self.tag = pydicom.datadict.tag_for_keyword(fieldname)
				self.getValue = self.getDicomValue
			elif fieldtype == 'fileinfo':
				self.getValue = lambda metadata: metadata['fileinfo'][fieldname]
			elif fieldtype == 'studyinfo':
				self.getValue = lambda metadata: metadata['studyinfo'][fieldname]

			if testtype == 'bool':
				self.test = lambda metadata: self.getValue(metadata) == True
			elif testtype == 'regex':
				re_test = re.compile(testvalue)
				self.test = lambda metadata: re_test.match(self.getValue(metadata)) != None
			elif testtype == 'math':
				op, val = ValueTest.math_parser.match(testvalue).groups()
				op = operators[op]
				val = float(val)
				self.test = lambda metadata: op(self.getValue(metadata),val)
	
	def getDicomValue(self,metadata):
		if not metadata['isDicom']:
			return ""
		if self.tag in metadata['dicom']:
			return metadata['dicom'][self.tag].value
		else:
			return ""
