# This package contains functions to process command line options
#

package Args;

# perl behavior
use strict;
use warnings;

# module vars
our $parm_mode = 0;          # mode of operation
our $parm_info = 0;          # how to display exif info
our $parm_exiftime = 1;      # whether to use exif time or file time
our $parm_tag;               # tag value in filename
our $parm_tag_append;        # whether to append to (auto) tag or set
our $parm_offset = 0;        # time offset
our $parm_rename_force = 0;  # force rename operation
our $parm_pcd_n = 0;         # film roll id
our $parm_pcd_d = "";        # date
our $parm_simulate = 0;      # simulate operation
our $parm_prompt = 0;        # confirm each operation
our $parm_clr_orien = 1;     # clear exif orientation value
our $parm_show_config = 0;   # show configuration content
our @files;                  # list of files to process

# local vars
my @options;                 # list of cmd line flags
my $argv0 = $0;              # executable name

my $usage_ver =
    "Q-Rename 7.4.2 [Perl/$^O $^V, 2019-04-18]\n" .
    "(c) 2002-2019 by Raymond Chi, all rights reserved.\n";

my $usage_help =
    "\nUsage: $argv0 <options> <files...>\n\n" .
    "<Options>\n\n" .
    "  -i[d]        Display/dump EXIF information in files\n" .
    "  -r           Rename files to YYYYMMDD_HHMMSS_NNNN[_tag].ext\n" .
    "    -o<offset> time offset as [-]h:m:s                  [-r/-t]\n" .
    "    -e[+]<tag> append to or set tag (default: auto)     [-r]\n" .
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
    "  -n           Do nothing. Simulate the operation.\n".
    "  -g           Show configuration file content.\n";


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
                    print "$f: file not found!\n";
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
        if ($i =~ /^i(.*)$/i) {    # -i, (1) info
            $parm_mode = 1;
            if ($1 eq "d") {
                $parm_info = 1;
            }
        }
        elsif ($i =~ /^r$/i) {     # -r, (2) rename
            $parm_mode = 2;
        }
        elsif ($i =~ /^f$/i) {     # -f, use file timestamp
            $parm_exiftime = 0;
        }
        elsif ($i =~ /^e(\+?)(.*)$/i) { # -e, tag
            $parm_tag = Util::verify_tag($2);
            if ($1) {
                $parm_tag_append = 1;
            }
        }
        elsif ($i =~ /^o(.*)$/i) { # -o, offset
            $parm_offset = Util::verify_offset($1);
        }
        elsif ($i =~ /^y$/i) {     # -y, force rename already processed
            $parm_rename_force = 1;
        }
        elsif ($i =~ /^t$/i) {     # -t, (3) touch file
            $parm_mode = 3;
        }
        elsif ($i =~ /^c(.*)$/i) { # -c, (6) clear orientation
            $parm_mode = 6;
            if ($1 =~ /^(\d+)$/) {
                $parm_clr_orien = $1;
            }
        }
        elsif ($i =~ /^b$/i) {     # -b, (7) extract thumbnail
            $parm_mode = 7;
        }
        elsif ($i =~ /^s$/i) {     # -s, (8) process into subdirs
            $parm_mode = 8;
        }
        elsif ($i =~ /^q$/i) {     # -a, (9) vuescan files
            $parm_mode = 9;
        }
        elsif ($i =~ /^k$/i) {     # -k, (4) kodak pictureCD
            $parm_mode = 4;
        }
        elsif ($i =~ /^a$/i) {     # -a, (5) pictureCD
            $parm_mode = 5;
        }
        elsif ($i =~ /^x(.*)$/i) { # -x, film roll ID
            $parm_pcd_n = Util::verify_roll($1);
        }
        elsif ($i =~ /^d(.*)$/i) { # -d, date
            $parm_pcd_d = Util::verify_date($1);
        }
        elsif ($i =~ /^n$/i) {     # simulate mode
            $parm_simulate = 1;
        }
        elsif ($i =~ /^p$/i) {     # prompt mode
            $parm_prompt = 1;
        }
        elsif ($i =~ /^g$/i) {     # show configuration info
            $parm_show_config = 1;
        }
        else {
            print_usage();
        }
    }

    # if show config, return, don't check/show help page
    if ($parm_show_config) {
        return
    }

    # must specify one of the modes, or a file to process
    if (!$parm_mode || scalar(@files) < 1) {
        print_usage();
    }

}


# required for modules
1;
