# This package contains utility functions for qren tool
#

package Util;

use v5.10;
use strict;
use diagnostics;

# disable experimental warning on 5.18 and higher
no if ($] >= 5.018), 'warnings' => 'experimental';

use Time::Local;
use Term::ReadKey;
use Image::ExifTool;


# hash of Model -> tags for auto tag generation. some are not needed
# due to intelligent auto processing.
my %tag_lookup = (
    "SCH-I535", "galaxys3",
    "Canon PowerShot SD1200 IS", "sd1200",
    "COOLPIX L12", "L12",
    "FinePix XP70 XP71 XP75", "xp70",
    "iPhone 6 Plus", "iphone6p",
    "Canon EOS DIGITAL REBEL XTi", "rebel_xti",
#    "NIKON D90", "d90",
#    "NIKON D70", "d70",
#    "DMC-GF1", "gf1",
#    "iPhone 4", "iphone4",
#    "Canon PowerShot S90", "s90",
#    "Canon PowerShot SD500", "sd500",
);

# value that should be removed from exif Model field to generate tag
my @tag_trim = ("NIKON", "Canon", "PowerShot", "DMC-", "COOLPIX");


######################################################################


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
    my $offset_sec = 0;
    # start with an optional -, and followed by 1 to 4 digits
    if ($offset =~ /^([-]?)(\d{1,}):(\d{1,2}):(\d{1,2})$/) {
        my ($hour, $min, $sec) = ($2, $3, $4);
        $offset_sec = $hour * 3600 + $min * 60 + $sec;
        if ($1 eq "-") {
            $offset_sec *= -1;
        }
    } else {
        print "Error: offset for /o must be in [-]h:m:s format - `$offset\'\n";
        exit;
    }
    return $offset_sec;
}


# verifies the tag, returns _tag
sub verify_tag
{
    my ($tag) = @_;
    # contains an alpha numeric sequence
    if ($tag =~ /^(\w*)$/) {
        return ($1) ? "_$tag" : "";
    } else {
        print "Error: tag must be alpha-numeric - `$tag\'\n";
        exit;
    }
}


######################################################################


# Take a string as "YYYYMMDD_HHMMSS" and return the number of seconds
# since epoch date for that date
sub convert_timestamp_file
{
    my ($string) = @_;
    # handles both _ or - as divider
    if ($string =~ /^(\d{4})(\d{2})(\d{2})[_-](\d{2})(\d{2})(\d{2})$/) {
        # get the proper fields
        my ($year, $mon, $day, $hour, $min, $sec) = ($1, $2, $3, $4, $5, $6);
        # convert from time to seconds since epoch date
        # http://perldoc.perl.org/Time/Local.html
        # works with actual YYYY format (for year > 999)
        return timelocal($sec, $min, $hour, $day, $mon - 1, $year);
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
    # this handles a timezone notion after the time! from canon I think
    if ($string =~ /^(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})(.*)$/) {
        # get the proper fields
        my ($year, $mon, $day, $hour, $min, $sec) = ($1, $2, $3, $4, $5, $6);
        # convert from time to seconds since epoch date
        # http://perldoc.perl.org/Time/Local.html
        # works with actual YYYY format (for year > 999)
        return timelocal($sec, $min, $hour, $day, $mon - 1, $year);
    } else {
        print "exif timestamp not in expected format! - $string\n";
        exit;
    }
}


# return a numeric representation of make brands
sub extract_make
{
    my ($info) = @_;
    my $model = 0;

    if ($info->{Make}) {
        given ($info->{Make}) {
            when (/nikon/i)      { $model = 1; }
            when (/canon/i)      { $model = 2; }
            when (/sony/i)       { $model = 3; }
            when (/panasonic/i)  { $model = 4; }
            when (/apple/i)      { $model = 5; }
        }
    }

    return $model;
}


# figure out the tag to use based on the model field in the exif
# tag is a short concise id representing the camera
sub auto_generate_tag
{
    my ($info) = @_;
    my $model = $info->{Model};
    my $tag;

    if (defined $model) {
        # do we have a predefined value for this Model?
        # if not, will trying to construct a tag automatically
        $tag = $tag_lookup{$model};
        if (!defined $tag) {
            # first remove branding strings
            for my $remove_str (@tag_trim) {
                $model =~ s/$remove_str//i;
            }
            # remove whitespace from string
            $model =~ s/\s+//;
            # lowercase all chars
            $tag = lc($model);
        }
    }

    return $tag;
}


# extract the DateTimeOriginal field from EXIF data and return it as a
# string in the format 2006:09:21 16:02:32
sub extract_exiftime
{
    my ($filename) = @_;

    my $info = &Image::ExifTool::ImageInfo($filename);

    if (defined $info->{Error}) {
        print "$info->{Error}! ";
        return;
    }

    if (defined $info->{Warning}) {
        #print "$info->{Warning}!\n";
        #return;
    }

    # Do not use FileModifyDate as this must extract the exif date, if any
    my $datetime = $info->{DateTimeOriginal};
    my $make = extract_make($info);
    # generate an automatic tag based on exif info
    my $tag = auto_generate_tag($info);
    if (!defined $tag) {
        print "no {Model} ";
    }

    if (!defined $datetime && $make == 5) {
        $datetime = $info->{CreateDate};
    }

    return ($datetime, $tag);
}


# figure out the max string length from the list of strings
sub max_string
{
    my ($strings_ref) = @_;
    my $max = 0;

    for my $str (@$strings_ref) {
        my $key_len = length($str);
        $max = $key_len if ($key_len > $max);
    }

    return $max;
}


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


# checks to see if user needs confirm of each action, and get
# confirmation if needed
# 0 - skip
# 1 - continue
sub get_confirm
{
    # prompts the user
    # this can be made into a function!!
    if ($Args::parm_prompt) {
        my $char = &promptUser(" (y/n/r)? ", "[ynr]");
        print ' ';
        if ($char =~ /n/i) {
            return 0;
        } elsif ($char =~ /r/i) {
            $Args::parm_prompt = 0;
        }
    }
    return 1;
}


# required for modules
1;
