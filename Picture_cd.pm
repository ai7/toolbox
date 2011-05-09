# This package contains functions to rename Kodak PictureCD files
#
# This module references global variables in qren directly,
# not good programming practice.
#

package Picture_cd;

use strict;
use diagnostics;

use Time::Local;
use Term::ReadKey;


# renames the input file to the name
# XXXX_NNNN_YYYYMMDD.ext name
sub rename_picturecd1
{
    my ($filename) = @_;

    # removes any begin and trailing blanks
    $filename =~ s/^\s+//;
    $filename =~ s/\s+$//;

    printf("%-*s => ", $qren::max_filename, $filename);

    # get the proper fields
    my $ext;
    my $seq;

    # picturecd filename such as 001_1a.jpg
    if ($filename =~ /^(\d+)_([0-9a-zA-Z]+)(\..*)$/) {
        $seq = $2;
        $ext = $3;
    } else {
        print "filename not in expected format!\n";
        $qren::skipped++;
        return;
    }

    my $roll_num = sprintf("%.4d", $Args::parm_pcd_n);
    while (length($seq) < 4) {
        $seq = "0$seq";
    }
    my $newname = "$roll_num\_$seq\_$Args::parm_pcd_d$ext";

    print "$newname";

    # prompts the user
    if ($Args::parm_prompt) {
        my $char = &Util::promptUser(" (y/n/r)? ", "[ynr]");
        if ($char =~ /n/i) {
            $qren::skipped++;
            goto finish;
        } elsif ($char =~ /r/i) {
            $Args::parm_prompt = 0;
        }
    }

    if (! $Args::parm_simulate) {
        if (! rename($filename, $newname)) {
            print " [rename failed]";
            $qren::failed++;
        } else {
            $qren::success++;
            print " [done]";
        }
    }

  finish:

    print "\n";
    return;
}


# reprocess renamed picturecd files for new roll number or date
sub rename_picturecd2
{
    my ($filename) = @_;

    # removes any begin and trailing blanks
    $filename =~ s/^\s+//;
    $filename =~ s/\s+$//;

    printf("%-*s => ", $qren::max_filename, $filename);

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
        $qren::skipped++;
        return;
    }

    if ($Args::parm_pcd_n == 0) {
        $roll_num = $tmp_roll;
    } else {
        $roll_num = sprintf("%.4d", $Args::parm_pcd_n);
    }
    if ($Args::parm_pcd_d eq "") {
        $roll_date = $tmp_date;
    } else {
        $roll_date = $Args::parm_pcd_d;
    }

    while (length($seq) < 4) {
        $seq = "0$seq";
    }

    my $newname = "$roll_num\_$seq\_$roll_date$ext";

    print "$newname";

    # prompts the user
    if ($Args::parm_prompt) {
        my $char = &Util::promptUser(" (y/n/r)? ", "[ynr]");
        if ($char =~ /n/i) {
            $qren::skipped++;
            goto finish;
        } elsif ($char =~ /r/i) {
            $Args::parm_prompt = 0;
        }
    }

    if (! $Args::parm_simulate) {
        if (! rename($filename, $newname)) {
            print " [rename failed]";
            $qren::failed++;
        } else {
            $qren::success++;
            print " [done]";
        }
    }

  finish:

    print "\n";
    return;
}


# required for modules
1;
