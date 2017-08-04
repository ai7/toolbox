# qren

Quick Rename Utility

## Overview

This time tested utility allows you to easily rename and organize digital camera images.

## Usage

```
Q-Rename 7.3.5 [Perl/MSWin32 v5.14.2, 2015-02-20]
(c) 2002-2015 by Raymond Chi, all rights reserved.

Usage: c:\util\bin\qren\src\perl\qren.pl <options> <files...>

<Options>

  -i[d]        Display/dump EXIF information in files
  -r           Rename files to YYYYMMDD_HHMMSS_NNNN[_tag].ext
    -o<offset> time offset as [-]h:m:s                  [-r/-t]
    -e<tag>    tag such as camera model (default: auto) [-r]
    -f         use file timestamp instead of EXIF time  [-i/-r]
    -y         re-process based on exif/file time       [-r]
    -d<date>   manual date if exif/file time < 1995/03  [-r]
  -t           Touch files based on timestamp in filename
  -c[n]        Clear/set EXIF orientation flag
  -b           Extract thumbnail image
  -s           Move renamed files into YYYY_MM_DD sub-dirs

  -q           Rename scan files from Scan-YYMMDD-NNNN.ext to
                 <roll>_NN_<date>[_tag].ext [needs -x & -d]
  -k           Rename PictureCD files from DDD_NNN.ext to
                 <roll>_NNNN_<date>.ext [needs -x & -d]
  -a           Rename XXXX_NNNN_YYYYMMDD.ext files [needs -x & -d]
    -x<roll>   film roll ID as XXXX [-k/-a]
    -d<date>   date as YYYYMMDD     [-k/-a]

  -p           Ask the user to confirm each file.
  -n           Do nothing. Simulate the operation.
```
