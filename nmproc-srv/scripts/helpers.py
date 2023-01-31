import os
import shutil
import operator

def finddirs(path):
	dirs = []
	for d in sorted(os.listdir(path)):
		dirname = (os.path.join(path,d))
		if os.path.isdir(dirname):
			dirs += finddirs(dirname)
	dirs.append(path)
	return dirs

def findfiles(paths):
	files = []
	for d in paths:
		for f in sorted(os.listdir(d)):
			filepath = os.path.join(d,f)
			if os.path.isfile(filepath):
				files.append(filepath)
	return files

def _link(src, dest):
   _makePath(dest)
   os.symlink(os.path.relpath(src,os.path.split(dest)[0]),dest)

def _copy(src, dest):
   _makePath(dest)
   shutil.copy(src,dest)

def _move(src, dest):
   _makePath(dest)
   shutil.move(src,dest)

def _del(src, dest):
   os.remove(src)

def _print(src, dest):
   print(f"{src} -> {dest}")

def _makePath(path):
	dirpath = os.path.split(path)[0]
	if not os.path.exists(dirpath):
		os.makedirs(dirpath)


operators = {
	'>':	operator.gt,
	'>=':	operator.ge,
	'=':	operator.eq,
	'<':	operator.lt,
	'<=':	operator.le
}

actions = {
	'ln':  _link,
	'mv':  _move,
	'cp':  _copy,
	'rm':  _del,
	'tst': _print
}

