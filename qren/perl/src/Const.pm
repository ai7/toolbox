# This package contains various constants for qren.
#

package Const;


######################################################################

# trigger video info for -i
our $video_ext     = '(mts)|(m2ts)|(mkv)|(avi)|(mov)|(mp3)|(wav)|(flac)';

# image files
our $image_ext     = '(jpg)|(png)';

# turn exif off
our $exif_off_ext  = '(mp3)|(wav)|(flac)';

# pattern for renaming standard digital camera files
# 2nd last, everything except dot, to gobble up " (x)" in filename.
our $pat_rename  = '^([a-zA-Z_]*)(\d+)([a-zA-Z]*)(\..*)$';

# pattern for samsung galaxy s3 photos, 20120930_094102[(x)].jpg
our $pat_s3      = '^(\d{8}[_]\d{6})(\((\d+)\))?(\..*)$';

# sony pcm-m10 files, YYMMDD_NN.mp3
our $pat_voice   = '^(\d{6})_(\d{2})(\..*)$';

# pattern for already renamed files (using either _ or - as divider)
our $pat_already = '(\d{8}[_-]\d{6})[_-](\d+)([_-]([\w \+-]+))?(\..*)$';

# lg phone: 0422071811a.jpg MMDDYYHHMMx (up to +10 pics in one min)
our $pat_lgphone = '^(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})([a-j])?(\..*)$';

# already renamed files to process into subdirs
our $pat_subdirs = '^(\d{4})(\d{2})(\d{2})_\d{6}_(\d+)(_([\w\+-]+))?(\..*)$';

# vuescan generated scan files
our $pat_scan    = '^([a-zA-Z]*)-(\d{6})-(\d+)(\..*)$';

# hash of Model -> tags for auto tag generation. some are not needed
# due to intelligent auto processing.
our %tag_lookup = (
    "SCH-I535", "galaxys3",
    "Canon PowerShot SD1200 IS", "sd1200",
    "COOLPIX L12", "L12",
    "FinePix XP70 XP71 XP75", "xp70",
    "iPhone 6 Plus", "iphone6p",
    "iPhone 6s Plus", "iphone6sp",
    "Canon EOS DIGITAL REBEL XTi", "rebel_xti",
#    "NIKON D90", "d90",
#    "NIKON D70", "d70",
#    "DMC-GF1", "gf1",
#    "iPhone 4", "iphone4",
#    "Canon PowerShot S90", "s90",
#    "Canon PowerShot SD500", "sd500",
);

# value that should be removed from exif Model field to generate tag
our @tag_trim = ("NIKON", "Canon", "PowerShot", "DMC-", "COOLPIX");


######################################################################


# required for modules
1;
