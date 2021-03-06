#!/usr/bin/env python

import sys
sys.path.append('../tatt')

# Global Modules
from subprocess import *
import sys
import re
import os

# from configobj
from configobj import ConfigObj
from validate  import Validator
# To access the specfile:
from pkg_resources import resource_filename


from gentooPackage import gentooPackage as gP
from packageFinder import *
from scriptwriter import writeusecombiscript as writeUSE
from scriptwriter import writerdepscript as writeRdeps
from scriptwriter import writesucessreportscript as writeSuccess

########### Generate a global config obj #################

# resource_filename will give us platform-independent access to the specfile
specfile = resource_filename('tatt', 'dot-tatt-spec')
config = ConfigObj("~/.tatt", configspec=specfile)

# this validator will also do type conversion according to the spec file!
validator = Validator()
result = config.validate(validator)

if result != True:
    print('Config file validation failed!')
    sys.exit(1)

######### Main program starts here ###############

### USAGE and OPTIONS ###
from optparse import OptionParser

parser=OptionParser()
parser.add_option("-d", "--depend",
                  help="Determine stable rdeps",
                  dest="depend",
                  action="store_true",
                  default = False)
parser.add_option("-u", "--use", "--usecombis",
                  help="Determine use flag combinations",
                  dest="usecombi",
                  action="store_true",
                  default = False)
parser.add_option("-f", "--file", 
                  help="Input File containing packages",
                  dest="infile",
                  action="store"
                  )
# parser.add_option("-t", "--test",
#                   help="run emerge commands with FEATURES=\"test\"",
#                   dest="feature_test",
#                   action="store_true",
#                   default = True)
parser.add_option("-j", "--jobname",
                  help="name for the job, prefix of output files",
                  dest="jobname",
                  action="store")
parser.add_option("-b", "--bug",
                  help="do the full program for a given stable request bug",
                  dest="bugnum",
                  action="store")
parser.add_option("-s", "--success",
		  help="Comment that the program was successfully tested",
                  dest="succbugnum",
		  action="store")

(options,args) = parser.parse_args()

if (Popen(['whoami'], stdout=PIPE).communicate()[0].rstrip() == 'root'):
    isroot=True
else:
    print("You're not root!")
    isroot=False

## -s and a bugnumber was given ?
if options.succbugnum:
    print("Reporting success for bug number " + options.succbugnum)
    retcode = call(['bugz', 'modify', options.succbugnum, '-c', config['successmessage']])
    if retcode == 0:
        print("Success!");
        exit (0)
    else:
        print("Failure commenting on Bugzilla")
        exit(1)

# Will eventuall contain packages to handle:
packs=None

## -b and a bugnumber was given ?
if options.bugnum:
    print("Working on bug number " + options.bugnum)
    # For the time being we search only in the title
    p1 = Popen(['bugz', 'get', options.bugnum, '-n', '--skip-auth'], stdout=PIPE)
    bugraw = Popen(['grep', 'Title'], stdin=p1.stdout, stdout=PIPE).communicate()[0]
    if not re.search('[Ss][Tt][Aa][Bb]', bugraw):
        print("Does not look like a stable request bug !")
        print(bugraw)
        # Let's not exit here, maybe we still want to work on the bug
        # exit (1)    
    packs = findPackages(bugraw, re.compile(config['atom-regexp']))

## or maybe -f and a filename have been given:
elif options.infile: 
    try:
        bugfile=open(options.infile, 'r')
    except IOError:
        print("Given filename not found !")
        exit(1)
    bugraw = bugfile.read()
    bugfile.close()
    packs = findPackages(bugraw, re.compile(config['atom-regexp']))

# joint code for -f and -b
##########################

if not packs==None:
    
    ## Assigning jobname
    if options.jobname:
        jobname = options.jobname
    elif options.infile:
        jobname = options.infile
    else:
        jobname = packs[0].packageName()
    print(("Jobname: " + jobname))
    
    for p in packs:
        print("Found the following package atom : " + p.packageString())

    # Unmasking:
    if isroot:
        # If we are root, then we can write to package.keywords
        try:
            keywordfile=open("/etc/portage/package.keywords/arch", 'r+')
        except IOError:
            # create an empty file, this should be beautified
            keywordfile=open("/etc/portage/package.keywords/arch", 'w')
            keywordfile.write(" ")
            keywordfile.close()
            keywordfile=open("/etc/portage/package.keywords/arch", 'r+')

        keywordfilecontent = keywordfile.read()
        for p in packs:
            # Test if keywordfile already contains the atom
            if re.search(p.packageString(), keywordfilecontent):
                print((p.packageString() + " already in package.keywords."))
            else:
                keywordfile.write("\n" + p.packageString() + "\n")
                print(("Appended " + p.packageString()+ " to /etc/portage/package.keywords/arch"))
        keywordfile.close()
    else:
        print("You are not root, your unmaskstring would be:")
        print(("\n".join([p.packageString() for p in packs]) + "\n"))
    ## Write the scripts
    writeUSE(jobname, packs, config["ignoreprefix"])
    writeRdeps(jobname, packs)
    if options.bugnum:
        writeSuccess(jobname, options.bugnum, config["successmessage"])
    exit (0)

## If we arrive here then a package atom should be given
try:
    pack = gP(args[0])
except IndexError:
    print("Please call with package atom as argument")
    exit (1)

if options.depend:
    writerdepscript(pack)

if options.usecombi:
    writeusecombiscript(pack)

## That's all folks ##
