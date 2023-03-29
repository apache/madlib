#
# Routines to pull information out of YML config files:
#   - config/Version.yml
#   - config/Ports.yml
#   - config/Modules.yml
#
import yaml
import re
import subprocess
from itertools import chain

##
# A Python exception class for our use
##
class MadPackConfigError(Exception):
     def __init__(self, value):
         self.value = value
     def __str__(self):
         return repr(self.value)

##
# Convert dict key and value from bytes to str
##
def convert(data):
    if isinstance(data, bytes):  return data.decode()
    if isinstance(data, dict):   return dict(map(convert, data.items()))
    if isinstance(data, tuple):  return tuple(map(convert, data))
    if isinstance(data, list):   return list(map(convert, data))
    return data

## 
# Load version string from Version.yml file.
# Typical Version.yml file:
#       version: 0.01
# @param configdir the directory where we can find Version.yml
##
def get_version(configdir):

    try:
        conf = yaml.safe_load(open(configdir + '/Version.yml'))
    except:
        print("configyml : ERROR : missing or malformed Version.yml")
        exit(2)

    conf = convert(conf)
    try:
        conf['version']
    except:
        print("configyml : ERROR : malformed Version.yml")
        exit(2)
        
    return conf['version']

    
## 
# Load Ports.yml file
# @param configdir the directory where we can find Ports.yml
##
def get_ports(configdir):

    try:
        conf = yaml.safe_load(open(configdir + '/Ports.yml'))
    except:
        print("configyml : ERROR : missing or malformed Ports.yml")
        exit(2)

    # XXX
    conf = convert(conf)
    for port in conf:
        try:
            conf[port]['name']
        except:
            print("configyml : ERROR : malformed Ports.yml: no name element for port " + port)
            exit(2)
        
    return conf
    
## 
# Load modules
#
# @param configdir the directory where we can find the [port_id].yml file
# @param id the ID of the specific DB port
# @param src the directory of the source code for a specific port
##
def get_modules(confdir):

    fname = "Modules.yml"
    
    try:
        conf = yaml.safe_load( open( confdir + '/' + fname))
    except:
        print("configyml : ERROR : missing or malformed " + confdir + '/' + fname)
        raise Exception

    # XXX
    conf = convert(conf)
    try:
        conf['modules']
    except:
        print("configyml : ERROR : missing modules section in " + fname)
        raise Exception

    conf = topsort_modules(conf)
    
    return conf

##
# Helper function
##    
def flatten(listOfLists):
    "Flatten one level of nesting"
    return chain.from_iterable(listOfLists)

## 
# Quick and dirty topological sort
# Currently does dumb cycle detection.
# @param depdict an edgelist dictionary, e.g. {'b': ['a'], 'z': ['m', 'n'], 'm': ['a', 'b']}
##
def topsort(depdict):
    out = dict()
    candidates = set()
    curlevel = 0

    while len(depdict) > 0:
        found = 0  # flag to check if we find anything new this iteration
        newdepdict = dict()
        # find the keys with no values
        keynoval = [t for t in iter(depdict.items()) if t[1] == []]
        # find the values that are not keys
        valnotkey = set(flatten(iter(depdict.values()))) - set(depdict.keys())

        candidates = set([k[0] for k in keynoval]) | valnotkey
        for c in candidates:
            if c not in out:
                found += 1
                out[c] = curlevel

        for k in depdict.keys():
            if depdict[k] != []:
                newdepdict[k] = [v for v in depdict[k] if v not in valnotkey]
        # newdepdict = dict(newdepdict)
        if newdepdict == depdict:
            raise MadPackConfigError(str(depdict))
        else:
            depdict = newdepdict
        if found > 0:
            curlevel += 1
    
    return out

## 
# Top-sort the modules in conf
# @param conf a madpack configuration
##
def topsort_modules(conf):

    depdict = dict()    
    for m in conf['modules']:
        try:
            depdict[m['name']] = m['depends']
        except:
            depdict[m['name']] = []        
    try:
        module_dict = topsort(depdict)
    except MadPackConfigError as e:
        raise MadPackConfigError("invalid cyclic dependency between modules: " + e.value + "; check Modules.yml files")

    missing = set(module_dict.keys()) - set(depdict.keys())
    inverted = dict()
    if len(missing) > 0:
        for k in depdict.keys():
            for v in depdict[k]:
                if v not in inverted:
                    inverted[v] = set()
                inverted[v].add(k)
        print("configyml : ERROR : required modules missing from Modules.yml: ")
        for m in missing:
            print("    " + m + " (required by " + str(list(inverted[m])) + ")")
        exit(2)
    conf['modules'] = sorted(conf['modules'], key=lambda m:module_dict[m['name']])
    return conf
