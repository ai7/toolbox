# This package contains utility functions for qren tool
#

package Util;

# perl behavior
use strict;
use warnings;

# standard perl modules
use Time::Local;
use Term::ReadKey;

# additional modules
use Image::ExifTool;  # http://search.cpan.org/~exiftool/


######################################################################

sub verify_date
{
    my ($date) = @_;
    if ($date !~ /^(\d{8})$/) {
        die "Error: date for /d must be in YYYYMMDD format - `$date\'\n";
    }
    return $date;
}


sub verify_roll
{
    my ($roll) = @_;
    if ($roll !~ /^(\d+)$/) {
        die "Error: roll for /x must be in NNNN format - `$roll\'\n";
    }
    return $roll;
}


# verifies the offset, returns the number of SECONDS
sub verify_offset
{
    my ($offset) = @_;
    my $offset_sec = 0;
    # start with an optional -, and followed by h:m:s
    if ($offset =~ /^([-]?)(\d{1,}):(\d{1,2}):(\d{1,2})$/) {
        my ($hour, $min, $sec) = ($2, $3, $4);
        $offset_sec = $hour * 3600 + $min * 60 + $sec;
        if ($1 eq "-") {
            $offset_sec *= -1;
        }
    # start with an optional -, and followed by X[day/week]
    # we don't do (y)ear or (m)onth because those don't have fixed duration.
    } elsif ($offset =~ /^([-]?)(\d{1,})([dw])$/) {
        my ($n, $unit) = ($2, $3);
        if    ($unit eq "d") { $offset_sec = $n * 24 * 3600 }
        elsif ($unit eq 'w') { $offset_sec = $n * 7 * 24 * 3600 }  # for gps rollover
        if ($1 eq "-") {
            $offset_sec *= -1;
        }
    } else {
        die "Error: offset for -o must be in [-]h:m:s | X<d|w> format - `$offset\'\n";
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
        die "Error: tag must be alpha-numeric - `$tag\'\n";
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
        die "timestamp not in expected format! - $string\n";
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
        die "exif timestamp not in expected format! - $string\n";
    }
}


# return a numeric representation of make brands
sub extract_make
{
    my ($info) = @_;
    my $model = 0;
    my $make;

    if ($info->{Make}) {
        $make = $info->{Make};
        if    ($make =~ /nikon/i)     { $model = 1; }
        elsif ($make =~ /canon/i)     { $model = 2; }
        elsif ($make =~ /sony/i)      { $model = 3; }
        elsif ($make =~ /panasonic/i) { $model = 4; }
        elsif ($make =~ /apple/i)     { $model = 5; }
    }

    return $model;
}


# change "iPhone xx Plus" -> "iphonexxp"
# can test at: https://regex101.com/
sub process_iphone_tag
{
    my ($model) = @_;

    # Can't encode the replacement string into variable (and therefore
    # can't store this as constants or in config files). It will
    # require using eval to make it work which is dangerious.

    # "iphone xx plus|pro" -> "iphonexxp"
    if ($model =~  /^iPhone ([\ds]+)[ ]*(Plus|Pro)$/) {
        $model =~ s/^iPhone ([\ds]+)[ ]*(Plus|Pro)$/iphone$1p/i;
    }

    # "iphone xx pro max" -> "iphonexxpm"
    elsif ($model =~ /^iPhone ([\ds]+)[ ]*(Pro Max)$/) {
        $model =~   s/^iPhone ([\ds]+)[ ]*(Pro Max)$/iphone$1pm/i;
    }

    return $model;
}


# figure out the tag to use based on the model field in the exif
# tag is a short concise id representing the camera
sub auto_generate_tag
{
    my ($info, $make) = @_;
    my $model = $info->{Model};
    my $tag;

    if (defined $model) {
        # if we have a predefined value for this Model, use it.
        # otherwise, try to generate one.
        $tag = $Const::tag_lookup{$model};
        if (defined $tag) {
            return $tag;
        }

        # handle iphone tags, do this before any trim so matching is
        # more accurate.
        if ($make == 5) {
            $model = process_iphone_tag($model);
        }
        # remove branding strings
        for my $remove_str (@Const::tag_trim) {
            $model =~ s/$remove_str//i;
        }
        # remove leading/trailing whitespaces first, this often happens
        # due to branding strings removal
        $model =~ s/^\s+|\s+$//g;
        # replace all whitespace (middle ones) with _
        $model =~ s/\s+/_/g;
        # lowercase all chars
        $tag = lc($model);
    }

    return $tag;
}


# given an exif INFO object and a list of fields,
# return the first field that contains data
sub get_field_helper
{
    my ($info, $fields) = @_;
    my $retval;

    # first get the time using the standard fields
    for my $field (@{$fields}) {
        $retval = $info->{$field};
        if (defined $retval) {
            last;
        }
    }

    return $retval;
}


# extract the DateTimeOriginal field from EXIF data and return it as a
# string in the format 2006:09:21 16:02:32
sub extract_exiftime
{
    my ($filename, $ext) = @_;

    my $info = &Image::ExifTool::ImageInfo($filename);
    my $datetime;

    if (defined $info->{Error}) {
        print "$info->{Error}! ";
        return;
    }

    if (defined $info->{Warning}) {
        #print "$info->{Warning}!\n";
        #return;
    }

    # first get the time using the standard fields
    $datetime = get_field_helper($info, \@Const::time_std);  # pass by ref

    # if no timestamp, resort to the extension specific rules
    if (!defined $datetime) {
        # Do this only for iphone PNG file?
        if ($ext =~ /png$/i) {
            $datetime = get_field_helper($info, \@Const::time_png);
        } elsif ($ext =~ /mov$/i) {
            $datetime = get_field_helper($info, \@Const::time_mov);
        }
    }

    # generate an automatic tag based on exif info
    my $make = extract_make($info);
    my $tag = auto_generate_tag($info, $make);
    if (!defined $tag) {
        print "no {Model} ";
    } else {
        # add owner info, if any
        $tag = add_owner($tag);
        # for iphone mov, add _live tag if video is a live photo
        # this is added after any owner info, so we have *_live.mov
        if ($make == 5 && $ext =~ /mov$/i) {
            if (is_live_photo($info)) {
                $tag = "${tag}_live";
            }
        }
    }

    return ($datetime, $tag);
}

sub add_owner
{
    my ($tag) = @_;
    my $owner = $Const::tag_owner{$tag};
    if (defined $owner) {
        return "${tag}_${owner}";
    }
    return $tag;
}

sub is_live_photo
{
    my ($info) = @_;

    # size is something like: 1920x1440
    my $size = $info->{ImageSize};
    return 0 if (!defined $size);

    my ($x, $y) = $size =~ /^(\d+)x(\d+)$/;  # extract x and y dimension
    my $ratio = $x / $y;

    # if ratio is 4/3, then it is a live photo video.
    # normal video should have aspect ratio 16/9
    if (abs($ratio - 4/3) < 0.000001) {
        return 1;
    }

    # in the future, we could potentially also check duration,
    # and make sure it is no more than 4s or something.

    return 0;
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
    select()->flush();

    ReadMode 3;
    my $key = ReadKey(0);
    while ($key !~ /$valid/i) {
        $key = ReadKey(0);
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
