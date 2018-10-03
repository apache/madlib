#!/usr/bin/env python

import sys
import os

with open('funcs.txt', 'r+') as funcsf:
	funcs_list = funcsf.read().splitlines()
	# print funcs_list

with open('tests.txt', 'r+') as testsf:
	tests_list = testsf.read().splitlines()
	# print tests_list

print type(funcs_list)

for t in tests_list:
	myfile = open(t, 'r')
	filedata = myfile.read()
	myfile.close()
	tempfile = open(t+'.tmp', 'w')
	for func in funcs_list:
		if func in filedata:
			filedata = filedata.replace(' '+func, ' MADLIB_SCHEMA.'+func)
			filedata = filedata.replace('	'+func, ' MADLIB_SCHEMA.'+func)
			filedata = filedata.replace('('+func, '(MADLIB_SCHEMA.'+func)
			filedata = filedata.replace('\''+func, '\'MADLIB_SCHEMA.'+func)

	tempfile.write(filedata)
	tempfile.close()
	os.system('cp {0} {1}'.format(t+'.tmp', t))
	os.system('rm {0}'.format(t+'.tmp'))
