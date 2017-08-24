# This package contains functions to rename Kodak PictureCD files
#
# This module references global variables in qren directly,
# not good programming practice.
#

package Picture_cd;

# perl behavior
use strict;
use diagnostics;


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
        my $char = Util::promptUser(" (y/n/r)? ", "[ynr]");
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
        my $char = Util::promptUser(" (y/n/r)? ", "[ynr]");
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


# renames the input file from Scan-YYMMDD-NNNN.ext to
# RRR_NN_YYYYMMDD[_tag].ext name
sub rename_scanned
{
    my ($filename) = @_;

    # removes any begin and trailing blanks
    $filename =~ s/^\s+//;
    $filename =~ s/\s+$//;

    printf("%-*s => ", $qren::max_filename, $filename);

    # target filename
    my $newname;

    # handles this first as standard rename matches this too
    if ($filename =~ /$Const::pat_scan/) {

        # extract data from the pattern
        my ($prefix, $scandate, $seq1, $ext) = ($1, $2, $3, $4);

        my $roll_num = sprintf("%.4d", $Args::parm_pcd_n);
        my $seq = sprintf("%.3d", $seq1);

        my $tag = "";
        my ($exif_time_string, $gtag) = Util::extract_exiftime($filename);
        if (!defined $Args::parm_tag && $gtag) {
            # tag is not specified on the command line, use the auto
            # generated tag name based on the exif Model field.
            $tag = "_$gtag";
        }

        $newname = "$roll_num\_$seq\_$Args::parm_pcd_d$tag$ext";

    } else {
        print "filename not in expected format!\n";
        $qren::skipped++;
        return;
    }

    # return if can't generate filename
    if (! defined $newname || $newname eq "") {
        print "failed to generate new filename!\n";
        $qren::failed++;
        return;
    }
    # skip if file is already in target name
    if ($filename eq $newname) {
        print "already in target name!\n";
        $qren::skipped++;
        return;
    }

    print "$newname";

    # prompts the user
    if ($Args::parm_prompt) {
        my $char = Util::promptUser(" (y/n/r)? ", "[ynr]");
        if ($char =~ /n/i) {
            $qren::skipped++;
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
            $qren::skipped++;
        } else {
            if (! rename($filename, $newname)) {
                print " [rename failed]";
                $qren::failed++;
            } else {
                $qren::success++;
                print " [done]";
            }
        }
    }

  finish:

    print "\n";
    return;
}


# required for modules
1;
