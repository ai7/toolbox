#!/usr/local/bin/perl -w

# This program renames files to YYYYMMDD_HHMMSS_NNNN.ext
# based on the file timestamp and sequence number in the filename.

# It is useful to convert files from digital camera to a more
# meaningful name for archiving purposes

# (c) 2002-2017 Raymond Chi <raymondc@cal.berkeley.edu>

package qren;

# perl behavior
use strict;
use diagnostics;

# standard perl modules
use POSIX qw(strftime);
use Time::Local;
use File::Spec;
use File::Basename;

# additional modules
use Image::ExifTool;  # http://search.cpan.org/~exiftool/

# local qren modules
use lib dirname(__FILE__);  # add script dir to @INC
use Const;
use Util;
use Args;
use Picture_cd;

# module vars, visible to other pm files
our $success = 0;       # statistics
our $failed = 0;
our $skipped = 0;
our $max_filename = 0;  # maximum filename length

# global vars
my $min_valid_time = timelocal(0, 0, 0, 1, 2, 1995);  # Kodak DCS460
my $operation;


######################################################################

# entry point function
sub main
{
    # process command line arguments
    Args::process_args();

    # figure out the maximum input filename length
    $max_filename = Util::max_string(\@Args::files);

    # do the actual work
    execute_commands();

    # print statistics
    print "\t$success file(s) $operation, $failed file(s) failed, $skipped file(s) skipped\n";

    return 0;
}


# do the required work (display info, rename, touch, etc..)
sub execute_commands
{
    # Removed given/when construct as it became experimental in perl
    # v5.18. Now Uses standard if/elsif block to be most compatible
    # going forward.

    if ($Args::parm_mode == 1) {     # info
        $operation = "processed";
        for my $f (@Args::files) {
            display_exif_info($f);
        }
    }

    elsif ($Args::parm_mode == 2) {  # rename
        $operation = "renamed";
        for my $f (@Args::files) {
            rename_file($f);
        }
    }

    elsif ($Args::parm_mode == 3) {  # touch
        $operation = "touched";
        for my $f (@Args::files) {
            touch_file($f);
        }
    }

    elsif ($Args::parm_mode == 4) {  # pictureCD1
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
            Picture_cd::rename_picturecd1($f);
        }
    }

    elsif ($Args::parm_mode == 5) {  # pictureCD2
        # verify roll or date specified for picturecd reprocess
        if ($Args::parm_pcd_n == 0 && $Args::parm_pcd_d eq "") {
            print "Error: -x AND/OR -d must be specified for -a\n";
            exit;
        }
        $operation = "renamed";
        for my $f (@Args::files) {
            Picture_cd::rename_picturecd2($f);
        }
    }

    elsif ($Args::parm_mode == 6) {  # clear exif orientation
        $operation = "processed";
        for my $f (@Args::files) {
            clear_exif_orientation($f);
        }
    }

    elsif ($Args::parm_mode == 7) {  # extract thumb image
        $operation = "extracted";
        for my $f (@Args::files) {
            extract_thumb_image($f);
        }
    }

    elsif ($Args::parm_mode == 8) {  # process files into subdirs
        $operation = "processed";
        process_into_folders(\@Args::files); # pass by ref
    }

    elsif ($Args::parm_mode == 9) {  # rename scan files
        if ($Args::parm_pcd_n == 0) {
            print "Error: roll number \"-x<XXX>\" must be specified for -q!\n";
            exit;
        } elsif ($Args::parm_pcd_d eq "") {
            print "Error: date \"-d<YYYYMMDD>\" must be specified for -q\n";
            exit;
        }
        $operation = "renamed";
        for my $f (@Args::files) {
            Picture_cd::rename_scanned($f);
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
    if ($ext =~ /^\.($Const::exif_off_ext)$/i) {
        $use_exif = 0;
    }

    if ($use_exif) {
        # extract exif timestamp as 2006:09:21 16:23:32
        # also get the auto generated tag to use
        my ($exif_time_string, $gtag) = Util::extract_exiftime($filename);
        if (! defined $exif_time_string) {
            print "no EXIF time! ";
            return;
        }
        if (!defined $Args::parm_tag && $gtag) {
            # tag is not specified on the command line, use the auto
            # generated tag name based on the exif Model field.
            $tag = "_$gtag";
        }
        # convert timestamp to # of sec since epoch
        my $exif_time = Util::convert_timestamp_exif($exif_time_string);
        $new_time = check_min_time($exif_time, 1);
    } else {
        # fstat[9] contains timestamp in seconds since 1970.
        my @fstat = stat($filename);
        $new_time = check_min_time($fstat[9], 0);
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
        $new_time = Util::convert_timestamp_file($Args::parm_pcd_d . "_000000");
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

    # handles this first as standard rename matches this too
    if ($filename =~ /$Const::pat_lgphone/) {

        my ($month, $day, $year, $hour, $min) = ($1, $2, $3, $4, $5);

        my $seq = 1; # default seq
        if ($6) { # process extra 'a', 'b', etc after filename
            $seq = ord($6) - ord('a') + 2;
        }
        my $ext = $7;
        my $tag = ($Args::parm_tag) ? $Args::parm_tag : "";

        # TODO: lg vx8300 bug!! 2011=01, 2012=02
        # assumes won't be using this in 2017!
        if ($year < 7) {
            print "(Year $year->";
            $year += 10;
            print "$year) ";
        }
        $newname = sprintf("20%s%s%s_%s%s00_%.4d%s%s",
                           $year, $month, $day, $hour, $min, $seq, $tag, $ext);

    # optional alpha, required digit, optional alpha, .ext
    } elsif ($filename =~ /$Const::pat_rename/) {

        # If files are in original digital camera name format
        my $seq = sprintf("%.4d", $2);  # set seq length to 4
        my $ext = $4;
        my $tag = ($Args::parm_tag) ? $Args::parm_tag : "";

        # force sequence length to be the last 4 digits
        $seq = substr($seq, -4) if (length($seq) > 4);

        ($newname, $newtime) = generate_new_filename($filename, $seq, $ext,
                                                      $tag, $Args::parm_exiftime);

    } elsif ($filename =~ /$Const::pat_voice/) {

        # this matches YYMMDD_NN.mp3, voice files from sony pcm-m10
        my $seq = $2; # sequence as is without expanding into 4 chars
        my $ext = $3;
        my $tag = ($Args::parm_tag) ? $Args::parm_tag : "";

        ($newname, $newtime) = generate_new_filename($filename, $seq, $ext,
                                                      $tag, $Args::parm_exiftime);

        # removed ^ in matching so 20d_20050101* files will match
    } elsif ($filename =~ /$Const::pat_already/) {

        my $filename_time = Util::convert_timestamp_file($1);
        # take seq as is, so shorter seq will be kept shorter
        # for example, voice files
        my $seq = $2;
        my $ext = $5;
        my $tag = $3; # out group

        # force sequence length to be the last 4 digits if it is longer
        $seq = substr($seq, -4)      if (length($seq) > 4);
        # increase to 4 digits if image files and less than 4 digits
        $seq = sprintf("%.4d", $seq) if (length($seq) < 4 && $ext =~ /^\.($Const::image_ext)$/i);

        # matches already renamed file, needs to handle with caution
        # safety check, do nothing if offset, tag, or force not specified
        if ($Args::parm_offset == 0 && !defined $Args::parm_tag &&
            !$Args::parm_rename_force && length($2) == length($seq)) {
            print "requires <offset>, <tag>, -y, or seq len change\n";
            $skipped++;
            return;
        }

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
            ($newname, $newtime) = generate_new_filename($filename, $seq, $ext,
                                                          $tag, $Args::parm_exiftime);
            $reprocess_offset = $newtime - $filename_time if (defined $newtime);
        }

    } elsif ($filename =~ /$Const::pat_s3/) {

        # the s3 creates files with timestamp in its name, nice!!
        my $filename_time = Util::convert_timestamp_file($1);
        # usually s3 files have no sequence number in them. If
        # take two pics within a second, a "(0)" is appended to
        # the 2nd pic. So we take this seq number and add one, to
        # have it start at 1.
        my $seq = sprintf("%.4d", (defined $3) ? $3+1 : 0);
        my $ext = $4;

        # s3 files have no tags, so we either figure it out based on
        # exif, or take whatever is specified in tag parameter.
        my $tag;
        if (defined $Args::parm_tag) {
            $tag = $Args::parm_tag;
        } else {
            my ($exif_time_string, $gtag) = Util::extract_exiftime($filename);
            $tag = ($gtag) ? "_$gtag" : "";
        }

        if (!$Args::parm_rename_force) {
            # if -y is not specified, simply reprocess files using new offset/tag
            # from timestamp embedded in the filename
            my $timestamp = strftime("%Y%m%d_%H%M%S", localtime($filename_time + $Args::parm_offset));
            $newname = "$timestamp\_$seq$tag$ext";
        } else {
            # -y is specified, need to reprocess based on exif or file timestamp
            ($newname, $newtime) = generate_new_filename($filename, $seq, $ext,
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
        my $char = Util::promptUser(" (y/n/r)? ", "[ynr]");
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
        $new_time = Util::convert_timestamp_file($1) + $Args::parm_offset;
    } else {
        print "filename not in expected format!\n";
        $skipped++;
        return;
    }

    print strftime("%Y-%m-%d %H:%M:%S", localtime($new_time));

    # prompts the user
    if ($Args::parm_prompt) {
        my $char = Util::promptUser(" (y/n/r)? ", "[ynr]");
        if ($char =~ /n/i) {
            $skipped++;
            goto finish;
        } elsif ($char =~ /r/i) {
            $Args::parm_prompt = 0;
        }
    }

    if (! $Args::parm_simulate) {
        my $ret = Util::my_touch($filename, $new_time);
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

    my $model = Util::extract_make($info);

    if (!$Args::parm_info) {

        my ($ext) = $filename =~ /\.(\w+)$/;
        if ($ext =~ /^($Const::video_ext)$/i) {
            display_video_info_short($filename, $info, $model);
        } else {
            display_image_info_short($filename, $info, $model);
        }

    } else {
        my @key_names = keys %$info;
        my $max_key = Util::max_string(\@key_names);
        # print data
        for my $key (sort @key_names) {
            printf("%s: %*s: %s\n", $filename, $max_key, $key, $$info{$key});
        }
    }
    $success++;
}


# returns a rotation degree setting, if any
sub get_orientation
{
    my ($info) = @_;
    my $rotation = ($info->{"Orientation"} || $info->{Rotation});

    if (defined $rotation) {
        if ($rotation =~ /horizontal \(normal\)/i) {
            $rotation = 0;
        } elsif ($rotation =~ /Rotate (\d+) CW/i) {
            $rotation = $1;
        } elsif ($rotation =~ /Rotate (\d+)/i) {
            $rotation = $1;
        }
    }

    return $rotation;
}


# displays one-line info about image files
# 2010:09:15 19:34:04 [+0s], 1600x1069, ISO  100, F 1.7,  1/40, ??mm, DMC-GF1
sub display_image_info_short
{
    my ($filename, $info, $make) = @_;

    my $datetime;
    my $filetime;
    my $offset;
    my $output = "";

    if ($Args::parm_exiftime) {
        $datetime = $info->{DateTimeOriginal};
        if (!defined $datetime) { $datetime = "?"; }
    } else {
        # fstat[9] contains timestamp in seconds since 1970.
        my @fstat = stat($filename);
        $filetime = $fstat[9];
        $datetime = strftime("%Y-%m-%d %H:%M:%S", localtime($filetime));
    }

    if ($datetime !~ /\?/ && $filename =~ /^(\d{8}_\d{6})_(\d+)(_(\w+))?(\..*)$/) {
        # calculate offset between timestamp embedded in the filename,
        # and the displayed exif/file timestamp, if file is already renamed
        my $filename_time = Util::convert_timestamp_file($1);
        my $info_time;
        if ($Args::parm_exiftime) {
            $info_time = Util::convert_timestamp_exif($datetime);
        } else {
            $info_time = $filetime;
        }
        my $diff = $filename_time - $info_time;
        my $hour = abs($diff) / 3600;
        my $min  = abs($diff) % 3600 / 60;
        my $sec  = abs($diff) % 3600 % 60;
        # display short notion if difference less than 60 seconds
        if ($diff > -60 && $diff < 60) {
            $offset = sprintf("[%+ds]", $diff);
        } else {
            # need this manual sign calculation because h/m/s is positive
            my $sign;
            if ($diff < 0) {
                $sign = "-";
            } else {
                $sign = "+";
            }
            $offset = sprintf("[%s%02d:%02d:%02d]", $sign, $hour, $min, $sec);
        }
        if ($diff == 0) {
            # $datetime = ""; # hide date if no offset
        }
    } else {
        # not renamed, difference is 0
        $offset = "";
    }

    $output = $datetime;
    if ($offset ne "") {
        if ($datetime eq "") {
            $output .= $offset;
        } else {
            $output .= " $offset";
        }
    }

    # get the rotation setting
    my $rotation = get_orientation($info);
    $output .= sprintf(", %3d\xf8", $rotation) if (defined $rotation);
    # $output .= sprintf(", %3dr", $rotation) if (defined $rotation);

    # get the image size
    my $size = $info->{ImageSize};
    $output .= ", $size" if (defined $size);

    # get the thumbnail image size
    if (defined $info->{ThumbnailImage}) {
        my $tsize = get_thumbnail_size($info);
        $output .= " [$tsize]" if (defined $tsize);
    }

    # get the iso
    my $iso = $info->{ISO};
    $output .= ", ISO $iso" if (defined $iso);

    # get the aperture
    my $aperture = $info->{Aperture};
    $output .= ", F$aperture" if (defined $aperture);

    # get shutter speed
    my $shutter = $info->{ShutterSpeed};
    $shutter = $info->{ShutterSpeedValue} if (!defined $shutter);
    $output .= ", $shutter" if (defined $shutter);

    # get the focal length
    my $fl = $info->{FocalLength};
    if (defined $fl && $fl =~ /^([\d\.]+)/) {
        $fl = $1;
        $fl =~ s/\.0$//; # remove trailing .0
    }
    $output .= ", $fl" . "mm" if (defined $fl);

    # get the the 35mm equivalent focal length
    my $fl35 = $info->{FocalLengthIn35mmFormat}; # nikon/panasonic
    if (defined $fl35) {
        if ($fl35 =~ /^([\d\.]+)/) {
            $fl35 = $1;     # extract out the digits in front, in case "41 mm"
        }
    } else {
        $fl35 = $info->{FocalLength35efl}; # canon
        if (defined $fl35) {
            # 5.8mm (35mm equivalent: 35.2mm)
            if ($fl35 =~ /equivalent:\s+(.+)mm\)$/) {
                $fl35 = $1;
            } elsif ($fl35 =~ /^([\d\.]+)/) {
                $fl35 = $1;     # extract out the digits in front, in case "41 mm"
            }
        }
    }
    if (defined $fl35) {
        if (defined $fl) {
            $output .= " ";
        } else {
            $output .= ", ";
        }
        $output .= "($fl35" . "mm)";
    }

    # get the model
    my $model = $info->{Model};
    if (defined $model) {
        # shorten some model names
        $model =~ s/PowerShot //;
        $output .= ", $model"
    }

    printf("%-*s: %s\n", $max_filename, $filename, $output);
}


# displays one-line info about video/audio files
sub display_video_info_short
{
    my ($filename, $info, $make) = @_;

    my $datetime;
    my $filetime;
    my $offset;
    my $output = "";

    if ($Args::parm_exiftime) {
        # extract out the date time, do not use fileModifyDate as it is useless info
        $datetime = $info->{DateTimeOriginal};
        $datetime = $info->{CreateDate} if (!defined $datetime && $make == 5);
        if (!defined $datetime) { $datetime = "?"; }
    } else {
        # fstat[9] contains timestamp in seconds since 1970.
        my @fstat = stat($filename);
        $filetime = $fstat[9];
        $datetime = strftime("%Y-%m-%d %H:%M:%S", localtime($filetime));
    }

    if ($datetime !~ /\?/ && $filename =~ /^(\d{8}_\d{6})_(\d+)(_(\w+))?(\..*)$/) {
        # calculate offset between timestamp embedded in the filename,
        # and the displayed exif/file timestamp, if file is already renamed
        my $filename_time = Util::convert_timestamp_file($1);
        my $info_time;
        if ($Args::parm_exiftime) {
            $info_time = Util::convert_timestamp_exif($datetime);
        } else {
            $info_time = $filetime;
        }
        my $diff = $filename_time - $info_time;
        my $hour = abs($diff) / 3600;
        my $min  = abs($diff) % 3600 / 60;
        my $sec  = abs($diff) % 3600 % 60;
        # display short notion if difference less than 60 seconds
        if ($diff > -60 && $diff < 60) {
            $offset = sprintf("[%+ds]", $diff);
        } else {
            # need this manual sign calculation because h/m/s is positive
            my $sign;
            if ($diff < 0) {
                $sign = "-";
            } else {
                $sign = "+";
            }
            $offset = sprintf("[%s%02d:%02d:%02d]", $sign, $hour, $min, $sec);
        }
        if ($diff == 0) {
            # $datetime = ""; # hide date if no offset
        }
    } else {
        # not renamed, difference is 0
        $offset = "";
    }

    $output = $datetime;
    if ($offset ne "") {
        if ($datetime eq "") {
            $output .= $offset;
        } else {
            $output .= " $offset";
        }
    }

    # get the video image size
    my $size = $info->{ImageSize};
    $output .= ", $size" if (defined $size);

    # get duration
    my $duration = $info->{Duration};
    $output .= " [$duration]" if (defined $duration);

    # get the rotation setting
    my $rotation = get_orientation($info);
    $output .= ", $rotation\xf8" if (defined $rotation);

    # get the audio/video type
    my $type = $info->{MIMEType};
    $output .= ", $type" if (defined $type);

    # get audio type
    my $audio = $info->{AudioStreamType};
    $output .= ", $audio" if (defined $audio);

    # get audio sample rate
    my $audio_rate = $info->{SampleRate};
    $audio_rate = $info->{AudioSampleRate} if (!defined $audio_rate);
    $output .= ", $audio_rate" . "hz"  if (defined $audio_rate);

    # get audio channels
    my $audio_chan = $info->{AudioChannels};
    $audio_chan = $info->{NumChannels} if (!defined $audio_chan);
    $audio_chan = $info->{Channels} if (!defined $audio_chan);
    $output .= "/$audio_chan" . "c" if (defined $audio_chan);

    # get audio bit sample
    my $audio_bits = $info->{AudioBitsPerSample};
    $audio_bits = $info->{BitsPerSample} if (!defined $audio_bits);
    $audio_bits = $info->{AudioBitrate} if (!defined $audio_bits);
    if (defined $audio_bits) {
        $output .= "/$audio_bits";
        if ($audio_bits !~ /\D/) { # add 'bit' if digits only
            $output .= "bit"
        }
    }

    my $model = $info->{Model};
    $model = $info->{Make} if (!defined $model);
    $output .= ", $model" if (defined $model);

    printf("%-*s: %s\n", $max_filename, $filename, $output);
}


# clears the exif orientation flag to the specified value
# used for jpg files that was rotated, but the flag was not reset
sub clear_exif_orientation
{
    my ($filename) = @_;

    # return if not an ordinary file
    if (! -f $filename) {
        return;
    }

    my $exifTool = new Image::ExifTool;
    # read exif info
    my $info = $exifTool->ImageInfo($filename);
    if (defined $info->{Error}) {
        printf("%-*s: %s!\n", $max_filename, $filename, $info->{Error});
        $failed++;
        return;
    }

    printf("%-*s => ", $max_filename, $filename);

    # get the current orientation
    my $orientation = get_orientation($info);
    if (!defined $orientation) {
        printf("missing orientation setting");
        $skipped++;
        goto finish;
    }

    # TODO: this comparison is wrong
    if ($orientation == 0 && $Args::parm_clr_orien == 1) {
        printf("already=%s, not needed!", $orientation);
        $skipped++;
        goto finish;
    }

    my $status = 0;

    # @TODO: figure out a list of models that can safely
    # process, make sure don't process on d90 files, for example

    # prompts the user if needed
    if (! Util::get_confirm()) {
        $skipped++;
        goto finish;
    }

    # http://www.sno.phy.queensu.ca/~phil/exiftool/ExifTool.html#SetNewValue
    $status = $exifTool->SetNewValue('Orientation#' => $Args::parm_clr_orien,
                                     EditOnly => 1);
    if ($status <= 0) {
        printf("SetNewValue() failed: %d", $status);
        $failed++;
        goto finish;
    }

    my $newname = $filename . ".new";
    if (! $Args::parm_simulate) {
        $status = $exifTool->WriteInfo($filename, $newname);
        if ($status != 1) {
            printf("failed (%d): %s", $status,
                   $exifTool->GetValue('Error'));
            $failed++;
            goto finish;
        }
        $success++;
    }

    printf("$newname (%s=>%s) [OK]", $orientation, $Args::parm_clr_orien);

  finish:

    print "\n";
    return;
}


# extract out the thumbnail image into a .thm file
sub extract_thumb_image
{
    my ($filename) = @_;

    # return if not an ordinary file
    if (! -f $filename) {
        return;
    }

    my $exifTool = new Image::ExifTool;

    # read exif info
    my $info = $exifTool->ImageInfo($filename);
    if (defined $info->{Error}) {
        printf("%-*s: %s!\n", $max_filename, $filename, $info->{Error});
        $failed++;
        return;
    }

    printf("%-*s => ", $max_filename, $filename);

    # chop off the extension, and use .thm
    $filename =~ s/(\.\w*)$//;
    my $outfile = $filename . ".thm";
    if (-e $outfile) {
        printf("%s already exist!", $outfile);
        $skipped++;
        goto finish;
    }

    # prompts the user if needed
    if (! Util::get_confirm()) {
        $skipped++;
        goto finish;
    }

    # now write the output file
    if (! $Args::parm_simulate) {
        open OUT, ">$outfile";
        binmode OUT;
        print OUT ${$$info{ThumbnailImage}};
        close OUT;
        $success++;
    }

    printf("%s [done]", $outfile);

  finish:

    print "\n";
    return;
}


# returns the thumbnail image size
sub get_thumbnail_size
{
    my ($info) = @_;
    my $tinfo = Image::ExifTool::ImageInfo($$info{ThumbnailImage});
    return $tinfo->{ImageSize};
}


# based on the filename, create a mapping of dirs (YYYY_MM_DD) to list
# of files that will go into that directory
sub get_subdirs_from_files
{
    my ($files_ref) = @_;

    my %hashtable = ();

    # don't need to test if file exist or not as Args does it
    for my $f (@$files_ref) {
        printf("%-*s => ", $max_filename, $f);
        # see if file matches already renamed pattern
        if ($f =~ /$Const::pat_subdirs/) {
            # construct folder name
            my $folder = "$1_$2_$3";
            if ($hashtable{$folder}) {
                # perl 5.24 disallows push on scalar expression
                # push($hashtable{$folder}, $f);
                push(@{$hashtable{$folder}}, $f);
            } else {
                $hashtable{$folder} = [$f];
            }
            # kind of complicated, better way?
            my $array_ref = $hashtable{$folder};
            printf("%s (%d)\n", $folder, scalar(@$array_ref));
        } else {
            print "pattern does not match, skipped\n";
            $skipped++;
        }
    }
    print "\n";

    return %hashtable;
}


# create the set of directories that the files will be moved to
sub create_folders
{
    my ($folders_ref) = @_;

    for my $dir (@$folders_ref) {

        print "$dir =>";

        if ($Args::parm_prompt) {
            my $char = Util::promptUser(" (y/n/r)? ", "[ynr]");
            if ($char =~ /n/i) {
                $skipped++;
                print "\n";
                next;
            } elsif ($char =~ /r/i) {
                $Args::parm_prompt = 0;
            }
        }

        if (! $Args::parm_simulate) {
            if (! -d $dir) {
                if (!mkdir($dir)) {
                    print " [mkdir failed]";
                    $failed++;
                    # return instead of continue processing
                    print "\n";
                    return 0;
                } else {
                    print " [done]";
                }
            } else {
                print " [already exist]";
            }
        }
        print "\n";
    }

    return 1;
}


# move the files into their respective subdirectories
sub move_files
{
    # key is dir name, value is list of files
    my ($hashtable_ref) = @_;
    my ($dir, $files_ref);

    while ( ($dir, $files_ref) = each(%$hashtable_ref) ) { # for each dirs

        for my $f (@$files_ref) { # for each target files in the dir

	    # join path in platform independent way
	    my $newname = File::Spec->join($dir, $f);

            printf("%-*s -> %s =>", $max_filename, $f, $dir);

            if ($Args::parm_prompt) {
                my $char = Util::promptUser(" (y/n/r)? ", "[ynr]");
                if ($char =~ /n/i) {
                    $skipped++;
                    print "\n";
                    next;
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
                    if (! rename($f, $newname)) {
                        print " [rename failed]";
                        $failed++;
                    } else {
                        $success++;
                        print " [done]";
                    }
                }
            }
            print "\n";

        }
    }

}


# process digital camera files into unique date based sub directories
sub process_into_folders
{
    my ($files_ref) = @_;

    my %hashtable = get_subdirs_from_files($files_ref);

    # now if hash table has 2 or more keys, continue
    my @subdirs = sort keys %hashtable;
    my $size = @subdirs;

    # print the list of directories and number of files in them
    if ($size > 0) {
        print "$size dirs:\n";
        for my $s (@subdirs) {
            my $array_ref = $hashtable{$s};
            printf("\t%s (%d)\n", $s, scalar(@$array_ref));
        }
        print "\n";
    }

    # if no dirs found, exit
    if ($size < 1) {
        print "$size dir, no actions needed.\n";
        goto finish;
    }

    # if only one dir, ask to confirm
    if ($size < 2) {
        print "Only $size dir, continue";
        my $char = Util::promptUser(" (y/n)? ", "[yn]");
        print "\n";
        if ($char =~ /n/i) {
            goto finish;
        }
        print "\n";
    }

    # prompt to create folders
    print "Create directories";
    my $char = Util::promptUser(" (y/n)? ", "[yn]");
    print "\n";
    if ($char =~ /n/i) {
        goto finish;
    }
    print "\n";

    if (! create_folders(\@subdirs)) {
        goto finish;
    }

    # prompt to move files
    print "\nMove files";
    $char = Util::promptUser(" (y/n)? ", "[yn]");
    print "\n";
    if ($char =~ /n/i) {
        goto finish;
    }
    print "\n";

    move_files(\%hashtable);

  finish:

    print "\n";
    return;

}


######################################################################

# begin main script
exit main();

######################################################################


# @ todo
# * once default exiftool in repository reaches 7.5.2, can have duration, and can
#   calculate correct .mts filename for gf1 video based on duration substraction.
