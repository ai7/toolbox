#!/usr/bin/env gawk -f

# script to convert garmin gpx files's comment/description field's
# silly DD-MMM-YY format to ISO date format, so native ascii order
# will sort waypoints by the time they are created.
#
# from: <cmt>05-JUL-13 16:34:05</cmt>
#   to: <cmt>2013-07-05 16:34:05</cmt>

BEGIN {
    # use < or > as field separator for XML content
    FS = "[<>]"

    # we are only interested in these lines
    p_line = "<cmt>|<desc>"

    # regex pattern for the timestamp garmin outputs
    # 05-JUL-13 16:34:05
    # the hour can be one digit, so we group it separately
    p_date = "([0-9]{2})-([a-zA-Z]{3})-([0-9]{2}) ([0-9]{1,2}):([0-9]{2}:[0-9]{2})"

    # create the month['jan'] = '01' ... array
    build_month()
}

# print non matching lines (implicit action)
$0 !~ p_line

# matching lines, convert matching timestamp
$0 ~ p_line {
    date = $3  # get the date we are interested in

    if (match(date, p_date, A)) {
        new_date = sprintf("20%s-%s-%s %02d:%s",  # assumes > year 2000
                           A[3],
                           month[tolower(A[2])],
                           A[1],
                           A[4],
                           A[5])
        # print date " -> " new_date
        # replace date with new_date in line
        sub(date, new_date, $0)
        count++
    }
    print
}

END {
    print FILENAME ":", count, "line(s) update." > "/dev/stderr"
}

# create the month['jan'] = '01' ... array
function build_month(   i, n, mlist)
{
    # parameters are used as local vars, no need to pass it in
    n = split("jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec", mlist, "|")
    for (i = 1; i <= n; i++) {
        month[mlist[i]] = sprintf("%02d", i)
    }
}

# var initializes to 0 or "" as appropriate depend on use.
# so basically no need to initialize variables
