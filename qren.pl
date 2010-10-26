#!/usr/local/bin/perl -w

# This program renames files to YYYYMMDD_HHMMSS_NNNN.ext
# based on the file timestamp and sequence number in the filename.

# It is useful to convert files from digital camera to a more
# meaningful name for archiving purposes

# v1.1 extracts sequence number from original filename, without them,
# the files are too hard to identify

# (c) 2002-2010 Raymond Chi <raymondc@cal.berkeley.edu>

# requires Term/ReadKey package. To install
# 1) ppm3-bin.exe
# 2) install TermReadKey

use strict;
use diagnostics;

use POSIX qw(strftime);

use Term::ReadKey;
use Time::Local;
use Image::ExifTool qw(:Public);

# begin main script

######################################################################

# executable name
my $argv0 = $0;

# statistics
my $success = 0;
my $failed = 0;
my $skipped = 0;

my $parm_mode = 0;

my $parm_info = 0;
my $parm_exiftime = 1;
my $parm_tag;
my $parm_offset = 0;
my $parm_rename_force = 0;

my $parm_pcd_n = 0;
my $parm_pcd_d = "";

my $parm_simulate = 0;
my $parm_prompt = 0;

my $min_valid_time = timelocal(0, 0, 0, 1, 2, 1995); # Kodak DCS460
my $max_filename = 0;

my $operation;

my $usage =
    (
     "Q-Rename 6.33 [Perl, 2010-10-26]\n" .
     "(c) 2002-2010 by Raymond Chi, all rights reserved.\n\n" .
     "Usage: $argv0 <options> <files...>\n\n" .
     "<Options>\n\n" .
     "  -i[d]        Display/dump EXIF information in files\n" .
     "  -r           Rename files to YYYYMMDD_HHMMSS_NNNN[_tag].ext\n" .
     "    -o<offset> time offset as [-]h:m:s [-r/-t]\n" .
     "    -e<tag>    tag such as camera model [-r]\n" .
     "    -f         use file timestamp instead of EXIF time [-i/-r]\n" .
     "    -y         re-process based on exif/file time [-r]\n" .
     "    -d<date>   manual date if exif/file time < 1995/03 [-r]\n" .
     "  -t           Touch files based on timestamp in filename\n" .
     "\n" .
     "  -k           Rename PictureCD files from DDD_NNN.ext to\n" .
     "                 <roll>_NNNN_<date>.jpg [needs -x and -d]\n" .
     "  -a           Rename XXXX_NNNN_YYYYMMDD.ext files [needs -x and -d]\n" .
     "    -x<roll>   film roll ID as XXXX [-k/-a]\n" .
     "    -d<date>   date as YYYYMMDD [-k/-a]\n" .
     "\n" .
     "  -p           Ask the user to confirm each file.\n" .
     "  -n           Do nothing. Simulate the operation.\n"
     );

if ($#ARGV + 1 < 1) {
    print $usage;
    exit;
}

my @options = ();
my @files = ();

# do the initial parsing through the parameters
for my $i (@ARGV) {

    # check to see if it is an option
    if ($i =~ /^[\-\/](.*)/)
    {
        push(@options, $1);
    }
    else
    {
        foreach my $f (glob($i)) {
            if (! -e $f) {
                print("$f: file not found!\n");
                $failed++;
            } else {
                # skip directories
                push(@files, $f) if (-f $f);
            }
        }
    }
}

# processing options here
for my $i (@options) {

    if ($i =~ /^i(.*)$/i) {      # -i, (1) info
        $parm_mode = 1;
        if ($1 eq "d") {
            $parm_info = 1;
        }

    } elsif ($i =~ /^r$/i) {     # -r, (2) rename
        $parm_mode = 2;

    } elsif ($i =~ /^f$/i) {     # -f, use file timestamp
        $parm_exiftime = 0;

    } elsif ($i =~ /^e(.*)$/i) { # -e, tag
        $parm_tag = &verify_tag($1);

    } elsif ($i =~ /^o(.*)$/i) { # -o, offset
        $parm_offset = &verify_offset($1);

    } elsif ($i =~ /^y$/i) {     # -y, force rename already processed
        $parm_rename_force = 1;

    } elsif ($i =~ /^t$/i) {     # -t, (3) touch file
        $parm_mode = 3;

    } elsif ($i =~ /^k$/i) {     # -k, (4) kodak pictureCD
        $parm_mode = 4;
    } elsif ($i =~ /^a$/i) {     # -a, (5) pictureCD
        $parm_mode = 5;
    } elsif ($i =~ /^x(.*)$/i) { # -x, film roll ID
        $parm_pcd_n = &verify_roll($1);
    } elsif ($i =~ /^d(.*)$/i) { # -d, date
        $parm_pcd_d = &verify_date($1);

    } elsif ($i =~ /^n$/i) {
        $parm_simulate = 1;      # simulate mode

    } elsif ($i =~ /^p$/i) {
        $parm_prompt = 1;        # prompt mode

    } else {
        print $usage;
        exit;
    }
}

# must specify one of the modes
if (!$parm_mode) {
    print $usage;
    exit;
}

# figure out the maximum filename length
$max_filename = &max_string(@files);

SWITCH: {

    # info
    if ($parm_mode == 1) {
        $operation = "processed";
        for my $f (@files) {
            &display_exif_info($f, $parm_info);
        }
        last SWITCH;
    }

    # rename
    if ($parm_mode == 2) {
        $operation = "renamed";
        for my $f (@files) {
            &rename_file($f);
        }
        last SWITCH;
    }

    # touch
    if ($parm_mode == 3) {
        $operation = "touched";
        for my $f (@files) {
            &touch_file($f);
        }
        last SWITCH;
    }

    # pictureCD1
    if ($parm_mode == 4) {
        # verify roll and date specified for picturecd
        if ($parm_pcd_n == 0) {
            print "Error: roll number \"-x<XXXX>\" must be specified for -k!\n";
            exit;
        } elsif ($parm_pcd_d eq "") {
            print "Error: date \"-d<YYYYMMDD>\" must be specified for -a\n";
            exit;
        }
        $operation = "renamed";
        for my $f (@files) {
            &rename_picturecd1($f);
        }
        last SWITCH;
    }

    # pictureCD2
    if ($parm_mode == 5) {
        # verify roll or date specified for picturecd reprocess
        if ($parm_pcd_n == 0 && $parm_pcd_d eq "") {
            print "Error: -x AND/OR -d must be specified for -a\n";
            exit;
        }
        $operation = "renamed";
        for my $f (@files) {
            &rename_picturecd2($f);
        }
        last SWITCH;
    }
}

# print statistics
print "\t$success file(s) $operation, $failed file(s) failed, $skipped file(s) skipped\n";

exit;

######################################################################

# find all files matching the list of patterns
# NO LONGER IN USE, now uses glob() function, and don't
# have the limitation of have to be in current directory
sub find_all_match
{
    my ($patterns) = @_;

    # opens the directory and get all the files
    opendir (DIR_HANDLE, ".");
    my @dirfiles = readdir(DIR_HANDLE);
    closedir (DIR_HANDLE);

    # matches it against the file pattern
    my @files = ();

    for my $i (@dirfiles) {

        # skip . and ..
        if (($i eq ".") || ($i eq "..")) {
            next;
        }

        # compare the file against each pattern
        for my $p (@$patterns) {
            if ($i =~ /$p/i) {
                push(@files, $i);
                last;
            }
        }

    }

    return @files;
}

######################################################################

# prompts the user for input
# returns if the user presses the key in given pattern
# the pattern matching is not case sensitive
sub promptUser
{
    my ($prompt_string, $valid) = @_;

    print $prompt_string;

    ReadMode 3;
    my $key = ReadKey;
    while ($key !~ /$valid/i) {
        $key = ReadKey;
    }
    ReadMode 0;

    print $key;
    return $key;
}

######################################################################

# generate the new filename for renaming
sub generate_new_filename
{
    my ($filename, $seq, $ext, $tag) = @_;

    my $new_name;   # return value #1
    my $new_time;   # return value #2

    if ($parm_exiftime) {
        # extract exif timestamp as 2006:09:21 16:23:32
        my $exif_time_string = &extract_exiftime($filename);
        if (! defined $exif_time_string) {
            $failed++;
            return;
        }
        # convert timestamp to # of sec since epoch
        my $exif_time = &convert_timestamp_exif($exif_time_string);
        $new_time = &check_min_time($exif_time, 1);
    } else {
        # fstat[9] contains timestamp in seconds since 1970.
        my @fstat = stat($filename);
        $new_time = &check_min_time($fstat[9], 0);
    }
    return if (! defined $new_time);

    my $timestr = strftime("%Y%m%d_%H%M%S", localtime($new_time));
    $new_name = "$timestr\_$seq$tag$ext";

    return ($new_name, $new_time);
}

# check the exif/file time against the min requirement
sub check_min_time
{
    my ($file_time, $is_exif) = @_;
    my $new_time;

    if ($file_time < $min_valid_time) {
        # if timestamp is too early
        if ($parm_pcd_d eq "") {
            # if no date explicitly specified, skip
            my $time_file = strftime("%Y-%m-%d %H:%M:%S", localtime($file_time));
            my $time_min  = strftime("%Y-%m-%d %H:%M:%S", localtime($min_valid_time));
            print $is_exif ? "EXIF" : "File";
            print " time too early: $time_file [< $time_min]\n";
            $skipped++;
            return;
        }
        $new_time = &convert_timestamp_file($parm_pcd_d . "_000000");
    } else {
        # construct final timestamp string with offset if any
        $new_time = $file_time + $parm_offset;
    }

    return $new_time;
}

# renames the input file to the name
# YYYYMMDD_HHMMSS_NNN_tag.ext name
sub rename_file
{
    my ($filename) = @_;

    # removes any begin and trailing blanks
    $filename =~ s/^\s+//;
    $filename =~ s/\s+$//;

    printf("%-*s => ", $max_filename, $filename);

    # print offset information if specified
    printf("[%+ds] ", $parm_offset) if ($parm_offset != 0);

    # target filename
    my $newname;
    my $newtime;
    my $reprocess_offset = 0;

    if ($filename =~ /^([a-zA-Z_]*)(\d+)(\..*)$/) {

        # If files are in original digital camera name format
        my $seq = sprintf("%.4d", $2);
        my $ext = $3;
        my $tag = ""; # assign default value

        # force sequence length to be the last 4 digits
        $seq = substr($seq, -4) if (length($seq) > 4);

        $tag = $parm_tag if (defined $parm_tag);
        ($newname, $newtime) = &generate_new_filename($filename, $seq, $ext, $tag);
        return if (! defined $newname || $newname eq "");

        # removed ^ in matching so 20d_20050101* files will match
    } elsif ($filename =~ /(\d{8}_\d{6})_(\d+)(_(\w+))?(\..*)$/) {

        # matches already renamed file, needs to handle with caution
        # safety check, do nothing if offset, tag, or force not specified
        if ($parm_offset == 0 && (!defined $parm_tag) && 
            !$parm_rename_force && length($2) == 4) {
            print "requires <offset>, <tag>, -y, or seq not N{4}\n";
            $skipped++;
            return;
        }

        my $filename_time = &convert_timestamp_file($1);
        my $seq = sprintf("%.4d", $2);
        my $ext = $5;
        my $tag = $3; # inner group

        # force sequence length to be the last 4 digits
        $seq = substr($seq, -4) if (length($seq) > 4);

        # tag on parameter overrides filename tag, including ""
        if (defined $parm_tag) {
            $tag = $parm_tag;
        } elsif (! defined $tag) {
            $tag = "";
        }

        if (!$parm_rename_force) {
            # if -y is not specified, simply reprocess files using new offset/tag
            # from timestamp embedded in the filename
            my $timestamp = strftime("%Y%m%d_%H%M%S", localtime($filename_time + $parm_offset));
            $newname = "$timestamp\_$seq$tag$ext";
        } else {
            # -y is specified, need to reprocess based on exif or file timestamp
            ($newname, $newtime) = &generate_new_filename($filename, $seq, $ext, $tag);
            return if (! defined $newname || $newname eq "");
            $reprocess_offset = $newtime - $filename_time;
        }

        # skip if file is already in target name
        if ($filename eq $newname) {
            print "already in target name!\n";
            $skipped++;
            return;
        }

    } else {
        print "filename not in expected format!\n";
        $skipped++;
        return;
    }

    print "$newname";
    printf(" [%+ds]", $reprocess_offset) if ($reprocess_offset != 0);

    # prompts the user
    if ($parm_prompt) {
        my $char = &promptUser(" (y/n/r)? ", "[ynr]");
        if ($char =~ /n/i) {
            $skipped++;
            goto finish;
        } elsif ($char =~ /r/i) {
            $parm_prompt = 0;
        }
    }

    if (! $parm_simulate) {
        # make sure the target does not exist because rename will kill it
        # not losing file is of utmost importance
        if (-f $newname) {
            print " [file exist]";
            $skipped++;
        } else {
            if (! rename($filename, $newname)) {
                print " [rename failed]";
                $failed++;
            } else {
                $success++;
                print " [done]";
            }
        }
    }

  finish:

    print "\n";
    return;
}

######################################################################

# touches a specific file to the specific time
# 0 - successfully touched
# 1 - failed
# 2 - skipped (no need to touch)
sub my_touch
{
    my ($file, $newtime) = @_;

    # get the current statistics
    my @current_stat = stat $file;
    my $atime = $current_stat[8];
    my $mtime = $current_stat[9];

    if ($newtime != $mtime) {
        if (utime($atime, $newtime, $file) < 1) {
            return 1;
        } else {
            return 0;
        }
    } else {
        return 2;
    }
}

sub touch_file
{
    my ($filename) = @_;

    # removes any begin and trailing blanks
    $filename =~ s/^\s+//;
    $filename =~ s/\s+$//;

    # return if not an ordinary file
    if (! -f $filename) {
        return;
    }

    printf("%-*s => ", $max_filename, $filename);

    # print offset information if specified
    printf("[%+ds] ", $parm_offset) if ($parm_offset != 0);

    # get the proper fields
    my $new_time;

    # the pattern here only recognizes ascii filenames
    if ($filename =~ /^(\d{8}_\d{6})_(.+)(\..*)$/) {
        $new_time = &convert_timestamp_file($1) + $parm_offset;
    } else {
        print "filename not in expected format!\n";
        $skipped++;
        return;
    }

    print strftime("%Y-%m-%d %H:%M:%S", localtime($new_time));

    # prompts the user
    if ($parm_prompt) {
        my $char = &promptUser(" (y/n/r)? ", "[ynr]");
        if ($char =~ /n/i) {
            $skipped++;
            goto finish;
        } elsif ($char =~ /r/i) {
            $parm_prompt = 0;
        }
    }

    if (! $parm_simulate) {
        my $ret = &my_touch($filename, $new_time);
        if ($ret == 1) {
            print " [touch failed]";
            $failed++;
        } elsif ($ret == 2) {
            print " [no need]";
            $skipped++;
        } else {
            $success++;
            print " [done]";
        }
    }

  finish:

    print "\n";
    return;

}

######################################################################

# renames the input file to the name
# XXXX_NNNN_YYYYMMDD.ext name
sub rename_picturecd1
{
    my ($filename) = @_;

    # removes any begin and trailing blanks
    $filename =~ s/^\s+//;
    $filename =~ s/\s+$//;

    printf("%-*s => ", $max_filename, $filename);

    # get the proper fields
    my $ext;
    my $seq;

    # picturecd filename such as 001_1a.jpg
    if ($filename =~ /^(\d+)_([0-9a-zA-Z]+)(\..*)$/) {
        $seq = $2;
        $ext = $3;
    } else {
        print "filename not in expected format!\n";
        $skipped++;
        return;
    }

    my $roll_num = sprintf("%.4d", $parm_pcd_n);
    while (length($seq) < 4) {
        $seq = "0$seq";
    }
    my $newname = "$roll_num\_$seq\_$parm_pcd_d$ext";

    print "$newname";

    # prompts the user
    if ($parm_prompt) {
        my $char = &promptUser(" (y/n/r)? ", "[ynr]");
        if ($char =~ /n/i) {
            $skipped++;
            goto finish;
        } elsif ($char =~ /r/i) {
            $parm_prompt = 0;
        }
    }

    if (! $parm_simulate) {
        if (! rename($filename, $newname)) {
            print " [rename failed]";
            $failed++;
        } else {
            $success++;
            print " [done]";
        }
    }

  finish:

    print "\n";
    return;
}

sub verify_date
{
    my ($date) = @_;
    if ($date !~ /^(\d{8})$/) {
        print "Error: date for /d must be in YYYYMMDD format - `$date\'\n";
        exit;
    }
    return $date;
}

sub verify_roll
{
    my ($roll) = @_;
    if ($roll !~ /^(\d+)$/) {
        print "Error: roll for /x must be in NNNN format - `$roll\'\n";
        exit;
    }
    return $roll;
}

# verifies the offset, returns the number of SECONDS
sub verify_offset
{
    my ($offset) = @_;
    my $hour;
    my $min;
    my $sec;
    my $offset_sec = 0;
    # start with an optional -, and followed by 1 to 4 digits
    if ($offset =~ /^([-]?)(\d{1,}):(\d{1,2}):(\d{1,2})$/) {
        $hour = $2;
        $min = $3;
        $sec = $4;
        $offset_sec = $hour * 3600 + $min * 60 + $sec;
        if ("$1" eq "-") {
            $offset_sec *= -1;
        }
    } else {
        print "Error: offset for /o must be in [-]h:m:s format - `$offset\'\n";
        exit;
    }
    return $offset_sec;
}

# verifies the offset, returns the number of SECONDS
sub verify_tag
{
    my ($tag) = @_;
    # contains an alpha numeric sequence
    if ($tag =~ /^(\w*)$/) {
        if (defined $1 && $1 ne "") {
            return "_$tag";
        } else {
            return "";
        }
    } else {
        print "Error: tag must be alpha-numeric - `$tag\'\n";
        exit;
    }
}


# reprocess renamed picturecd files for new roll number or date
sub rename_picturecd2
{
    my ($filename) = @_;

    # removes any begin and trailing blanks
    $filename =~ s/^\s+//;
    $filename =~ s/\s+$//;

    printf("%-*s => ", $max_filename, $filename);

    # get the proper fields
    my $tmp_roll;
    my $tmp_date;
    my $roll_num;
    my $roll_date;
    my $ext;
    my $seq;

    # already converted filename, do new roll number and date
    if ($filename =~ /^(\d{4})_([0-9a-zA-Z]{4})_(\d{8})(\..*)$/) {
        $tmp_roll = $1;
        $seq = $2;
        $tmp_date = $3;
        $ext = $4;
    } else {
        print "filename not in expected format!\n";
        $skipped++;
        return;
    }

    if ($parm_pcd_n == 0) {
        $roll_num = $tmp_roll;
    } else {
        $roll_num = sprintf("%.4d", $parm_pcd_n);
    }
    if ($parm_pcd_d eq "") {
        $roll_date = $tmp_date;
    } else {
        $roll_date = $parm_pcd_d;
    }

    while (length($seq) < 4) {
        $seq = "0$seq";
    }

    my $newname = "$roll_num\_$seq\_$roll_date$ext";

    print "$newname";

    # prompts the user
    if ($parm_prompt) {
        my $char = &promptUser(" (y/n/r)? ", "[ynr]");
        if ($char =~ /n/i) {
            $skipped++;
            goto finish;
        } elsif ($char =~ /r/i) {
            $parm_prompt = 0;
        }
    }

    if (! $parm_simulate) {
        if (! rename($filename, $newname)) {
            print " [rename failed]";
            $failed++;
        } else {
            $success++;
            print " [done]";
        }
    }

  finish:

    print "\n";
    return;
}

######################################################################

# display EXIF information from file
sub display_exif_info
{
    my ($filename, $info_mode) = @_;

    my $info = ImageInfo($filename);
    if (defined $info->{Error}) {
        printf("%-*s: %s!\n", $max_filename, $filename, $info->{Error});
        $failed++;
        return;
    }

    if (defined $info->{Warning}) {
        #print "$filename: $info->{Warning}!\n";
        #$skipped++;
        #return;
    }

    if (!$info_mode) {

        # listing mode, display essential information about image file
        my ($model, $f1, $f2, $f3, $f4, $f5, $f6, $f7, $offset, $filetime);

        $model = 0;
        if (defined $info->{Make}) {
            if    ($info->{Make} =~ /nikon/i) { $model = 1; }
            elsif ($info->{Make} =~ /canon/i) { $model = 2; }
            elsif ($info->{Make} =~ /sony/i)  { $model = 3; }
        }

        if ($parm_exiftime) {
            $f1 = $info->{DateTimeOriginal};
            if (!defined $f1) { $f1 = "????:??:?? ??:??:??"; }
        } else {
            # fstat[9] contains timestamp in seconds since 1970.
            my @fstat = stat($filename);
            $filetime = $fstat[9];
            $f1 = strftime("%Y-%m-%d %H:%M:%S", localtime($filetime));
        }

        if ($f1 !~ /\?/ && $filename =~ /^(\d{8}_\d{6})_(\d+)(_(\w+))?(\..*)$/) {
            # calculate offset between timestamp embedded in the filename,
            # and the displayed exif/file timestamp, if file is already renamed
            my $filename_time = &convert_timestamp_file($1);
            my $info_time;
            if ($parm_exiftime) {
                $info_time = &convert_timestamp_exif($f1);
            } else {
                $info_time = $filetime;
            }
            my $diff = $filename_time - $info_time;
            my $hour = abs($diff) / 3600;
            my $min  = abs($diff) % 3600 / 60;
            my $sec  = abs($diff) % 3600 % 60;
            # display short notion if difference less than 60 seconds
            if ($diff > -60 && $diff < 60) {
                $offset = sprintf(" [%+ds]", $diff);
            } else {
                # need this manual sign calculation because h/m/s is positive
                my $sign;
                if ($diff < 0) {
                    $sign = "-";
                } else {
                    $sign = "+";
                }
                $offset = sprintf(" [%s%02d:%02d:%02d]", $sign, $hour, $min, $sec);
            }
        } else {
            # not renamed, difference is 0
            $offset = "";
        }

        $f2 = $info->{ImageSize};
        if (!defined $f2) { $f2 = "????x????"; }

        $f3 = $info->{ISO};
        if (!defined $f3) { $f3 = "???"; }

        $f4 = $info->{Aperture};
        if (!defined $f4) { $f4 = "?.?"; }

        if ($model == 2) {
            $f5 = $info->{ShutterSpeedValue};
        } else {
            $f5 = $info->{ShutterSpeed};
        }
        if (!defined $f5) { $f5 = "??"; }

        if ($model == 1) {
            # Nikon writes a simple 35mm equivalent value
            $f6 = $info->{FocalLengthIn35mmFormat};
        } elsif ($model == 2) {
            my $f35mm = $info->{FocalLength35efl};
            # 5.8mm (35mm equivalent: 35.2mm)
            if ($f35mm =~ /equivalent:\s+(.+)mm\)$/) {
                $f6 = $1;
            }
        }
        if (!defined $f6) { $f6 = "??"; }

        $f7 = $info->{Model};
        if (!defined $f7) { $f7 = "??"; }

        printf("%-*s: %s%s, %s, ISO %4s, F%4s, %5s, %smm, %s\n",
               $max_filename, $filename, $f1, $offset, $f2, $f3, $f4, $f5, $f6, $f7);

    } else {
        my @key_names = keys %$info;
        my $max_key = &max_string(@key_names);
        # print data
        foreach my $key (sort @key_names) {
            printf("%s: %*s: %s\n", $filename, $max_key, $key, $$info{$key});
        }
    }
    $success++;
}

######################################################################

# Take a string as "YYYYMMDD_HHMMSS" and return the number of seconds
# since epoch date for that date
sub convert_timestamp_file
{
    my ($string) = @_;
    if ($string =~ /^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/) {
        # get the proper fields
        my $year = $1;
        my $mon = $2;
        my $day = $3;
        my $hour = $4;
        my $min = $5;
        my $sec = $6;
        # convert from time to seconds since epoch date
        # http://perldoc.perl.org/Time/Local.html
        # works with actual YYYY format (for year > 999)
        return timelocal($sec,
                         $min,
                         $hour,
                         $day,
                         $mon - 1,
                         $year);
    } else {
        print "timestamp not in expected format! - $string\n";
        exit;
    }
}

# Take a string as "2006:09:21 16:23:32" and return the number of seconds
# since epoch date for that date
sub convert_timestamp_exif
{
    my ($string) = @_;
    if ($string =~ /^(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})(.*)$/) {
        # get the proper fields
        my $year = $1;
        my $mon = $2;
        my $day = $3;
        my $hour = $4;
        my $min = $5;
        my $sec = $6;
        # convert from time to seconds since epoch date
        # http://perldoc.perl.org/Time/Local.html
        # works with actual YYYY format (for year > 999)
        return timelocal($sec,
                         $min,
                         $hour,
                         $day,
                         $mon - 1,
                         $year);
    } else {
        print "exif timestamp not in expected format! - $string\n";
        exit;
    }
}

# extract the DateTimeOriginal field from EXIF data and return it as a
# string in the format 2006:09:21 16:02:32
sub extract_exiftime
{
    my ($filename) = @_;

    my $info = ImageInfo($filename);

    if (defined $info->{Error}) {
        print "$info->{Error}!\n";
        return;
    }

    if (defined $info->{Warning}) {
        #print "$info->{Warning}!\n";
        #return;
    }

    return $info->{DateTimeOriginal};
}


# figure out the max string length from the list of strings
sub max_string
{
    my (@strings) = @_;
    my $max = 0;

    foreach my $str (@strings) {
        my $key_len = length($str);
        $max = $key_len if ($key_len > $max);
    }

    return $max;
}

######################################################################
#
# Change History
#
# 6.0 (1/2007)
#   - used EXIFTools perl library to read and parse exif time
#   - more clean up
#
# 6.2 (2/5/2007)
#   - general code clean up, moved blocks into subroutines
#   - max filename length used in all messages
#   - removed current directory check
#   - moved check for file exist / directory in glob() block
#
# 6.3 (10/17/2007)
#   - take Canon 40d "2007:10:06 10:52:15+08:00" type exif timestamp
#
# 6.31 (1/17/2008)
#   - relaxed already generated filename matching rule
#
# 6.32 (7/8/2010)
#   - force 4 chars for seq NNNN. GF1's NNN is too many digits
#
# 6.33 (10/26/2010)
#   - force 4 chars works for already processed files
#
######################################################################
