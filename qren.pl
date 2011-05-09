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

my $video_ext    = "(mts)|(m2ts)|(mkv)|(avi)|(mov)|(mp3)|(wav)|(flac)"; # trigger video info for -i
my $exif_off_ext = "(mp3)|(wav)|(flac)";             # turn exif off


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
        case 6 { # clear exif orientation
            $operation = "processed";
            for my $f (@Args::files) {
                &clear_exif_orientation($f);
            }
        }
        case 7 { # extract thumb image
            $operation = "extracted";
            for my $f (@Args::files) {
                &extract_thumb_image($f);
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
    if ($ext =~ /^\.($exif_off_ext)$/i) {
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

    # optional alpha, required digit, optional alpha, .ext
    if ($filename =~ /^([a-zA-Z_]*)(\d+)([a-zA-Z]*)(\..*)$/) {

        # If files are in original digital camera name format
        my $seq = sprintf("%.4d", $2);  # set seq length to 4
        my $ext = $4;
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

    my $model = &Util::extract_make($info);

    if (!$Args::parm_info) {

        my ($ext) = $filename =~ /\.(\w+)$/;
        if ($ext =~ /^($video_ext)$/i) {
            &display_video_info_short($filename, $info, $model);
        } else {
            &display_image_info_short($filename, $info, $model);
        }

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
        my $filename_time = &Util::convert_timestamp_file($1);
        my $info_time;
        if ($Args::parm_exiftime) {
            $info_time = &Util::convert_timestamp_exif($datetime);
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
    my $rotation = &get_orientation($info);
    $output .= sprintf(", %3d\xf8", $rotation) if (defined $rotation);
    # $output .= sprintf(", %3dr", $rotation) if (defined $rotation);

    # get the image size
    my $size = $info->{ImageSize};
    $output .= ", $size" if (defined $size);

    # get the thumbnail image size
    if (defined $info->{ThumbnailImage}) {
        my $tsize = &get_thumbnail_size($info);
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
    if (defined $fl && $fl =~ /^(\d+)/) {
        $fl = $1;
    }
    $output .= ", $fl" . "mm" if (defined $fl);

    # get the the 35mm equivalent focal length
    my $fl35 = $info->{FocalLengthIn35mmFormat}; # nikon/panasonic
    if (defined $fl35) {
        if ($fl35 =~ /^(\d+)/) {
            $fl35 = $1;     # extract out the digits in front, in case "41 mm"
        }
    } else {
        $fl35 = $info->{FocalLength35efl}; # canon
        # 5.8mm (35mm equivalent: 35.2mm)
        if (defined $fl35 && $fl35 =~ /equivalent:\s+(.+)mm\)$/) {
            $fl35 = $1;
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
        my $filename_time = &Util::convert_timestamp_file($1);
        my $info_time;
        if ($Args::parm_exiftime) {
            $info_time = &Util::convert_timestamp_exif($datetime);
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
    my $rotation = &get_orientation($info);
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
    my $orientation = &get_orientation($info);
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
    if (! &Util::get_confirm()) {
        $skipped++;
        goto finish;
    }

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
    if (! &Util::get_confirm()) {
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
# 7.01 (04/19/2011)
#   - updated display of 1-line info for image/video
#   - tested with new exiftool that parses .mts!!
#
# 7.02 (05/09/2011)
#   - display and clear rotation setting via -c
#   - extract out embedded thumbnail into .thm via -b
#   - tested/updated with iphone4 jpg/mov files
#
######################################################################

# @ todo
# * once default exiftool in repository reaches 7.5.2, can have duration, and can
#   calculate correct .mts filename for gf1 video based on duration substraction.
# * reset exif orientation flag
# http://www.sno.phy.queensu.ca/~phil/exiftool/ExifTool.html#SetNewValue
