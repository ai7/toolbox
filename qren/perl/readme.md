# qren Perl

## Overview

This is the original version of `qren` started back in 2002, and has
been continuously refined over the years. Still the workhorse for all
my rename and image utility needs in 2019!

Perl was quite popular back in the 2000s. It was pretty fast, and have
lots of supporting libraries in CPAN, such as the excellent and up to
date `ExifTool`. Although Perl as a language has fallen out of favor
compare to more modern choices such as Python, it is still pretty well
supported and simple to use. For example, adding support for _YAML_
and Apple's _HEIC_ file format was pretty trivial.

For me, Perl reminds me of the good old dot-com era days, and keeping
this version up to date provided me a connection to the past!

## Perl Setup

`qren` requires Perl, obviously, and some extra perl packages to work.

### Windows

Windows doesn't come with Perl. For better part of a decade I've been
using `ActivePerl`, even using containerized ThinApp version of it.

Around 2017 I switched to using _Strawberry Perl_, an open source Perl
distribution that is more actively maintained. It also have a
_portable_ version which makes putting it on Windows a breeze. Simply
unzip to wherever you want to run it from, no need to worry about an
Installer that does who-knows-what to your system.

- Download portable version of __Strawberry Perl__.
  - https://strawberryperl.com/releases.html
    - ie: https://strawberryperl.com/download/5.32.1.1/strawberry-perl-5.32.1.1-64bit-portable.zip
  - Unzip to suitable location
    - ie: `c:\devtools\perl.strawberry`
- Download __ExifTool__.
  - https://exiftool.org/
    - ie: https://exiftool.org/Image-ExifTool-12.24.tar.gz
  - Unzip to a _temporary location_.
  - Copy _content_ of `lib` to Strawberry Perl's `perl\site\lib` folder.
    - From `Image-ExifTool-12.24\lib\*`
      - The `Image`, `File` folder
    - To: `perl.strawberry\perl\site\lib`

Run `qren.pl` and it should not complain about any dependencies.

```
Q-Rename 7.5.1 [Perl/MSWin32 v5.32.1, ExifTool/v12.24, 2021-04-17]
(c) 2002-2021 by Raymond Chi, all rights reserved.

Usage: qren.pl <options> <files...>

<Options>

  -i[d]        Display/dump EXIF information in files
  -r           Rename files to YYYYMMDD_HHMMSS_NNNN[_tag].ext
    -o<offset> time offset as [-]h:m:s | X<d|w>         [-r/-t]
    -e[+]<tag> append to or set tag (default: auto)     [-r]
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
  -g           Show configuration file content.
```

### Mac

Mac comes with perl, so we just need to install the `Image::ExifTool`
and `YAML::XS` package.

- If `cpan` hasn't been configured, run `cpan` on command line to
   configure it.
  - Can configure CPAN to use user's $HOME directory.
  - Can re-run configuration via: `cpan`, then `o conf init`.
  - Ensure environment variable is set before continuing.
- Install required packages.
  - run `cpan` to start cpan shell.
  - `install Image::ExifTool`
  - `install YAML::XS`

Run `qren`, with any luck, you should see the following:

```
Q-Rename 7.4.2 [Perl/darwin v5.18.2, ExifTool/v11.30, 2019-04-19]
(c) 2002-2019 by Raymond Chi, all rights reserved.

Usage: qren.pl <options> <files...>

<Options>

  -i[d]        Display/dump EXIF information in files
  -r           Rename files to YYYYMMDD_HHMMSS_NNNN[_tag].ext
    -o<offset> time offset as [-]h:m:s                  [-r/-t]
    -e[+]<tag> append to or set tag (default: auto)     [-r]
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
  -g           Show configuration file content.
```
