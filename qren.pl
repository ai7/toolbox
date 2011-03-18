#!/usr/local/bin/perl -w

# This program renames files to YYYYMMDD_HHMMSS_NNNN.ext
# based on the file timestamp and sequence number in the filename.

# It is useful to convert files from digital camera to a more
# meaningful name for archiving purposes

# (c) 2002-2011 Raymond Chi <raymondc@cal.berkeley.edu>

# requires Term/ReadKey package. To install
# 1) ppm3-bin.exe
# 2) install TermReadKey

package qren;

use strict;
use diagnostics;

use Switch;
use POSIX qw(strftime);

use Term::ReadKey;
use Time::Local;
use Image::ExifTool;

use Util;
use Args;
use Picture_cd;

# module vars

our $success = 0;  # statistics
our $failed = 0;
our $skipped = 0;
our $max_filename = 0;  # maximum filename length

# begin main script

######################################################################

my $min_valid_time = timelocal(0, 0, 0, 1, 2, 1995);  # Kodak DCS460
my $operation;

&Args::process_args();                            # process command line arguments

$max_filename = &Util::max_string(@Args::files);

&execute_commands();                              # do the actual work

# print statistics
print "\t$success file(s) $operation, $failed file(s) failed, $skipped file(s) skipped\n";

exit;

######################################################################


# do the required work (display info, rename, touch, etc..)
sub execute_commands
{
    switch ($Args::parm_mode) {
        case 1 { # info
            $operation = "processed";
            for my $f (@Args::files) {
                &display_exif_info($f);
            }
        }
        case 2 { # rename
            $operation = "renamed";
            for my $f (@Args::files) {
                &rename_file($f);
            }
        }
        case 3 { # touch
            $operation = "touched";
            for my $f (@Args::files) {
                &touch_file($f);
            }
        }
        case 4 { # pictureCD1
            # verify roll and date specified for picturecd
            if ($Args::parm_pcd_n == 0) {
                print "Error: roll number \"-x<XXXX>\" must be specified for -k!\n";
                exit;
            } elsif ($Args::parm_pcd_d eq "") {
                print "Error: date \"-d<YYYYMMDD>\" must be specified for -a\n";
                exit;
            }
            $operation = "renamed";
            for my $f (@Args::files) {
                &Picture_cd::rename_picturecd1($f);
            }
        }
        case 5 { # pictureCD2
            # verify roll or date specified for picturecd reprocess
            if ($Args::parm_pcd_n == 0 && $Args::parm_pcd_d eq "") {
                print "Error: -x AND/OR -d must be specified for -a\n";
                exit;
            }
            $operation = "renamed";
            for my $f (@Args::files) {
                &Picture_cd::rename_picturecd2($f);
            }
        }
    }
}


# generate the new filename for renaming
sub generate_new_filename
{
    my ($filename, $seq, $ext, $tag, $use_exif) = @_;

    my $new_name;   # return value #1
    my $new_time;   # return value #2

    # override exif flag for certain extensions
    if ($ext =~ /^\.((mp3)|(wav)|(flac))$/i) {
        $use_exif = 0;
    }

    if ($use_exif) {
        # extract exif timestamp as 2006:09:21 16:23:32
        my $exif_time_string = &Util::extract_exiftime($filename);
        if (! defined $exif_time_string) {
            print "no EXIF time! ";
            return;
        }
        # convert timestamp to # of sec since epoch
        my $exif_time = &Util::convert_timestamp_exif($exif_time_string);
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
        if ($Args::parm_pcd_d eq "") {
            # if no date explicitly specified, skip
            my $time_file = strftime("%Y-%m-%d %H:%M:%S", localtime($file_time));
            my $time_min  = strftime("%Y-%m-%d %H:%M:%S", localtime($min_valid_time));
            print $is_exif ? "EXIF" : "File";
            print " time too early: $time_file [< $time_min]\n";
            $skipped++;
            return;
        }
        $new_time = &Util::convert_timestamp_file($Args::parm_pcd_d . "_000000");
    } else {
        # construct final timestamp string with offset if any
        $new_time = $file_time + $Args::parm_offset;
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
    printf("[%+ds] ", $Args::parm_offset) if ($Args::parm_offset != 0);

    # target filename
    my $newname;
    my $newtime;
    my $reprocess_offset = 0;

    if ($filename =~ /^([a-zA-Z_]*)(\d+)(\..*)$/) {

        # If files are in original digital camera name format
        my $seq = sprintf("%.4d", $2);  # set seq length to 4
        my $ext = $3;
        my $tag = ""; # assign default value

        # force sequence length to be the last 4 digits
        $seq = substr($seq, -4) if (length($seq) > 4);

        $tag = $Args::parm_tag if (defined $Args::parm_tag);
        ($newname, $newtime) = &generate_new_filename($filename, $seq, $ext,
                                                      $tag, $Args::parm_exiftime);

    } elsif ($filename =~ /^(\d{6})_(\d{2})(\..*)$/) {

        # this matches YYMMDD_NN.mp3, voice files from sony pcm-m10
        my $seq = $2; # sequence as is without expanding into 4 chars
        my $ext = $3;
        my $tag = ""; # assign default value

        $tag = $Args::parm_tag if (defined $Args::parm_tag);
        ($newname, $newtime) = &generate_new_filename($filename, $seq, $ext, 
                                                      $tag, $Args::parm_exiftime);

        # removed ^ in matching so 20d_20050101* files will match
    } elsif ($filename =~ /(\d{8}_\d{6})_(\d+)(_(\w+))?(\..*)$/) {

        # matches already renamed file, needs to handle with caution
        # safety check, do nothing if offset, tag, or force not specified
        if ($Args::parm_offset == 0 && !defined $Args::parm_tag &&
            !$Args::parm_rename_force && length($2) <= 4) {
            print "requires <offset>, <tag>, -y, or seq > N{4}\n";
            $skipped++;
            return;
        }

        my $filename_time = &Util::convert_timestamp_file($1);
        # take seq as is, so shorter seq will be kept shorter
        my $seq = $2;
        my $ext = $5;
        my $tag = $3; # inner group

        # force sequence length to be the last 4 digits
        $seq = substr($seq, -4) if (length($seq) > 4);

        # tag on parameter overrides filename tag, including ""
        if (defined $Args::parm_tag) {
            $tag = $Args::parm_tag;
        } elsif (! defined $tag) {
            $tag = "";
        }

        if (!$Args::parm_rename_force) {
            # if -y is not specified, simply reprocess files using new offset/tag
            # from timestamp embedded in the filename
            my $timestamp = strftime("%Y%m%d_%H%M%S", localtime($filename_time + $Args::parm_offset));
            $newname = "$timestamp\_$seq$tag$ext";
        } else {
            # -y is specified, need to reprocess based on exif or file timestamp
            ($newname, $newtime) = &generate_new_filename($filename, $seq, $ext,
                                                          $tag, $Args::parm_exiftime);
            $reprocess_offset = $newtime - $filename_time if (defined $newtime);
        }

    } else {
        print "filename not in expected format!\n";
        $skipped++;
        return;
    }

    # return if can't generate filename
    if (! defined $newname || $newname eq "") {
        print "failed to generate new filename!\n";
        $failed++;
        return;
    }
    # skip if file is already in target name
    if ($filename eq $newname) {
        print "already in target name!\n";
        $skipped++;
        return;
    }

    print "$newname";
    printf(" [%+ds]", $reprocess_offset) if ($reprocess_offset != 0);

    # prompts the user
    if ($Args::parm_prompt) {
        my $char = &Util::promptUser(" (y/n/r)? ", "[ynr]");
        if ($char =~ /n/i) {
            $skipped++;
            goto finish;
        } elsif ($char =~ /r/i) {
            $Args::parm_prompt = 0;
        }
    }

    if (! $Args::parm_simulate) {
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
    printf("[%+ds] ", $Args::parm_offset) if ($Args::parm_offset != 0);

    # get the proper fields
    my $new_time;

    # the pattern here only recognizes ascii filenames
    if ($filename =~ /^(\d{8}_\d{6})_(.+)(\..*)$/) {
        $new_time = &Util::convert_timestamp_file($1) + $Args::parm_offset;
    } else {
        print "filename not in expected format!\n";
        $skipped++;
        return;
    }

    print strftime("%Y-%m-%d %H:%M:%S", localtime($new_time));

    # prompts the user
    if ($Args::parm_prompt) {
        my $char = &Util::promptUser(" (y/n/r)? ", "[ynr]");
        if ($char =~ /n/i) {
            $skipped++;
            goto finish;
        } elsif ($char =~ /r/i) {
            $Args::parm_prompt = 0;
        }
    }

    if (! $Args::parm_simulate) {
        my $ret = &Util::my_touch($filename, $new_time);
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


# display EXIF information from file
sub display_exif_info
{
    my ($filename) = @_;

    my $info = Image::ExifTool::ImageInfo($filename);
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

    if (!$Args::parm_info) {

        # listing mode, display essential information about image file
        my ($model, $f1, $f2, $f3, $f4, $f5, $f6, $f7, $offset, $filetime);

        $model = 0;
        if (defined $info->{Make}) {
            if    ($info->{Make} =~ /nikon/i) { $model = 1; }
            elsif ($info->{Make} =~ /canon/i) { $model = 2; }
            elsif ($info->{Make} =~ /sony/i)  { $model = 3; }
        }

        if ($Args::parm_exiftime) {
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
            my $filename_time = &Util::convert_timestamp_file($1);
            my $info_time;
            if ($Args::parm_exiftime) {
                $info_time = &Util::convert_timestamp_exif($f1);
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
        my $max_key = &Util::max_string(@key_names);
        # print data
        foreach my $key (sort @key_names) {
            printf("%s: %*s: %s\n", $filename, $max_key, $key, $$info{$key});
        }
    }
    $success++;
}


######################################################################
#
# Change History
#
# 1.1 (?)
#   - extracts sequence number from original filename, without them,
#     the files are too hard to identify
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
# 7.00 (03/18/2011)
#   - support for rename pcm-m10 files YYMMDD_NN.mp3
#   - split qren.pl into multiple modules for better organization!
#   - fixed missing newline when exif failed to extract time
#   - turn off exif time reading for mp3/wav/flac files
#
######################################################################
