# This package contains functions to process command line options
#

package Args;

use v5.10;
use strict;
use diagnostics;

# disable experimental warning on 5.18 and higher
no if ($] >= 5.018), 'warnings' => 'experimental';

# use Getopt::Std;

# exit after print help
# $Getopt::Std::STANDARD_HELP_VERSION = 1;

# module vars
our $parm_mode = 0;          # mode of operation
our $parm_info = 0;          # how to display exif info
our $parm_exiftime = 1;      # whether to use exif time or file time
our $parm_tag;               # tag value in filename
our $parm_offset = 0;        # time offset
our $parm_rename_force = 0;  # force rename operation
our $parm_pcd_n = 0;         # film roll id
our $parm_pcd_d = "";        # date
our $parm_simulate = 0;      # simulate operation
our $parm_prompt = 0;        # confirm each operation
our $parm_clr_orien = 1;     # clear exif orientation value
our @files;                  # list of files to process

# local vars
my @options;                 # list of cmd line flags
my $argv0 = $0;              # executable name

my $usage_ver =
    "Q-Rename 7.3.5 [Perl/$^O $^V, 2015-02-20]\n" .
    "(c) 2002-2015 by Raymond Chi, all rights reserved.\n";

my $usage_help =
    "\nUsage: $argv0 <options> <files...>\n\n" .
    "<Options>\n\n" .
    "  -i[d]        Display/dump EXIF information in files\n" .
    "  -r           Rename files to YYYYMMDD_HHMMSS_NNNN[_tag].ext\n" .
    "    -o<offset> time offset as [-]h:m:s                  [-r/-t]\n" .
    "    -e<tag>    tag such as camera model (default: auto) [-r]\n" .
    "    -f         use file timestamp instead of EXIF time  [-i/-r]\n" .
    "    -y         re-process based on exif/file time       [-r]\n" .
    "    -d<date>   manual date if exif/file time < 1995/03  [-r]\n" .
    "  -t           Touch files based on timestamp in filename\n" .
    "  -c[n]        Clear/set EXIF orientation flag\n" .
    "  -b           Extract thumbnail image\n" .
    "  -s           Move renamed files into YYYY_MM_DD sub-dirs\n" .
    "\n" .
    "  -q           Rename scan files from Scan-YYMMDD-NNNN.ext to\n" .
    "                 <roll>_NN_<date>[_tag].ext [needs -x & -d]\n" .
    "  -k           Rename PictureCD files from DDD_NNN.ext to\n" .
    "                 <roll>_NNNN_<date>.ext [needs -x & -d]\n" .
    "  -a           Rename XXXX_NNNN_YYYYMMDD.ext files [needs -x & -d]\n" .
    "    -x<roll>   film roll ID as XXXX [-k/-a]\n" .
    "    -d<date>   date as YYYYMMDD     [-k/-a]\n" .
    "\n" .
    "  -p           Ask the user to confirm each file.\n" .
    "  -n           Do nothing. Simulate the operation.\n";


# called by getopt and my print_usage
sub main::HELP_MESSAGE
{
    print $usage_help;
}
sub main::VERSION_MESSAGE
{
    print $usage_ver;
}

sub print_usage
{
    main::VERSION_MESSAGE();
    main::HELP_MESSAGE();
    exit;
}


# process the ARGV array and setup @options/@files
sub process_args
{
    # print help if no args given
    unless (@ARGV) { print_usage(); }

    # not using getopt because this is better, opt/file can interleave
    # args needs to directly follow flag, without space

    # do the initial parsing through the parameters
    for my $i (@ARGV) {
        # check to see if it is an option
        if ($i =~ /^[\-\/](.*)/) {
            push(@options, $1);
        } else {
            for my $f (glob($i)) {
                if (! -e $f) {
                    print("$f: file not found!\n");
                    $qren::failed++;
                } else {
                    # skip directories
                    push(@files, $f) if (-f $f);
                }
            }
        }
    }

    # processing options here
    for my $i (@options) {
        given ($i) {
            when (/^i(.*)$/i) { # -i, (1) info
                $parm_mode = 1;
                if ($1 eq "d") {
                    $parm_info = 1;
                }
            }
            when (/^r$/i) {     # -r, (2) rename
                $parm_mode = 2;
            }
            when (/^f$/i) {     # -f, use file timestamp
                $parm_exiftime = 0;
            }
            when (/^e(.*)$/i) { # -e, tag
                $parm_tag = Util::verify_tag($1);
            }
            when (/^o(.*)$/i) { # -o, offset
                $parm_offset = Util::verify_offset($1);
            }
            when (/^y$/i) {     # -y, force rename already processed
                $parm_rename_force = 1;
            }
            when (/^t$/i) {     # -t, (3) touch file
                $parm_mode = 3;
            }
            when (/^c(.*)$/i) { # -c, (6) clear orientation
                $parm_mode = 6;
                if ($1 =~ /^(\d+)$/) {
                    $parm_clr_orien = $1;
                }
            }
            when (/^b$/i) {     # -b, (7) extract thumbnail
                $parm_mode = 7;
            }
            when (/^s$/i) {     # -s, (8) process into subdirs
                $parm_mode = 8;
            }
            when (/^q$/i) {     # -a, (9) vuescan files
                $parm_mode = 9;
            }
            when (/^k$/i) {     # -k, (4) kodak pictureCD
                $parm_mode = 4;
            }
            when (/^a$/i) {     # -a, (5) pictureCD
                $parm_mode = 5;
            }
            when (/^x(.*)$/i) { # -x, film roll ID
                $parm_pcd_n = Util::verify_roll($1);
            }
            when (/^d(.*)$/i) { # -d, date
                $parm_pcd_d = Util::verify_date($1);
            }
            when (/^n$/i) {     # simulate mode
                $parm_simulate = 1;
            }
            when (/^p$/i) {     # prompt mode
                $parm_prompt = 1;
            }
            default {
                print_usage();
            }
        }
    }

    # must specify one of the modes, or a file to process
    if (!$parm_mode || scalar(@files) < 1) {
        print_usage();
    }

}


# required for modules
1;
