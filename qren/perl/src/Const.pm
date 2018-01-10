# This package contains various constants for qren.
#

package Const;

# perl behavior
use strict;
use warnings;

# standard perl modules
use File::Basename;
use YAML::XS 'LoadFile';
use Data::Dumper;

######################################################################


our $pat_rename;   # renaming standard digital camera files
our $pat_already;  # pattern for already renamed files (using either _ or - as divider)
our $pat_subdirs;  # already renamed files to process into subdirs

our $pat_s3;       # samsung galaxy s3 photos, 20120930_094102[(x)].jpg
our $pat_voice;    # sony pcm-m10 files, YYMMDD_NN.mp3
our $pat_lgphone;  # lg phone: 0422071811a.jpg MMDDYYHHMMx (up to +10 pics in one min)
our $pat_scan;     # vuescan generated scan files

our $image_ext;    # image files
our $video_ext;    # trigger video info for -i
our $exif_off_ext; # turn exif off

our %tag_lookup;   # hash of Model -> tags for auto tag generation
our @tag_trim;     # value to removed from exif Model field to generate tag

our @time_std;     # default exif time fields
our @time_png;     # exif time fields for iphone png files
our @time_mov;     # exif time fields for iphone mov files

######################################################################

# JSON is not a suitable format for our config file because backslash
# needs to be escaped inside strings, and we have lots of it in our
# configuration.

# read from config file and set module variables.
sub read_config
{
    my ($show_config) = (@_);

    # read yaml file, so simple!
    my $fn = File::Spec->join(dirname(__FILE__), 'qren.yaml');
    my $config = LoadFile($fn);

    if ($show_config) {
        print Dumper($config);
        exit;
    }

    # assign fields to module variables
    $pat_rename  = $config->{'filename'}->{'rename'};
    $pat_already = $config->{'filename'}->{'already'};
    $pat_subdirs = $config->{'filename'}->{'subdirs'};
    $pat_s3      = $config->{'filename'}->{'s3'};
    $pat_voice   = $config->{'filename'}->{'voice'};
    $pat_lgphone = $config->{'filename'}->{'lgphone'};
    $pat_scan    = $config->{'filename'}->{'scan'};

    $image_ext   = $config->{'extension'}->{'image'};
    $video_ext   = $config->{'extension'}->{'video'};
    $exif_off_ext = $config->{'extension'}->{'exif_off'};

    %tag_lookup  = %{$config->{'tag'}->{'lookup'}};  # dereference
    @tag_trim    = @{$config->{'tag'}->{'trim'}};    # dereference

    @time_std    = @{$config->{'timestamp'}->{'std'}};  # dereference
    @time_png    = @{$config->{'timestamp'}->{'png'}};  # dereference
    @time_mov    = @{$config->{'timestamp'}->{'mov'}};  # dereference
}


# required for modules
1;
