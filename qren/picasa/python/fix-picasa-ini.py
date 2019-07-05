#!/usr/bin/env python
#
# this simple tool fixes .picasa.ini filename, in the case when the
# filenames have been renamed due to timestamp update.
# this is so that we can preserve the starred files if we rename files
# after we have done the selection in picasa.

import os
import click
import re
import time
import glob

# already renamed pattern,
PAT_ALREADY = r'(\d{8})[_-](\d{6})[_-](\d+[e]?)([_-][\w \+-]+)?(\..*)$'


@click.command()
@click.argument('in_file')
@click.argument('out_file')
@click.option('--offset', default=0)
def fix_picasa_ini(in_file, out_file, offset):

    with open(in_file) as in_fp:  # open .picasa.ini for reading
        lines = list(in_fp)

    did_work = False
    with open(out_file, "w") as out_fp:
        for line in lines:
            # check if it is a section: [.....]
            m = re.match(r'^\[(.+)\]$', line)

            # if not, just write to output
            if not m:
                out_fp.write(line)
                continue

            # this is a section, so check the file
            name = m.group(1)  # the image file
            click.echo('{}: '.format(name), nl=False)
            if os.path.exists(name):  # if file exist, we are done
                click.secho('OK', fg='green')
                out_fp.write(line)
                continue

            # file does not exist, need to find matching file
            new_name = locate_new_file(name, offset)
            if not new_name:
                out_fp.write(line)
            else:
                click.secho('{}'.format(new_name), fg='green')
                out_fp.write('[{}]\n'.format(new_name))  # remember new line
                did_work = True

    if not did_work:
        os.remove(out_file)


def locate_new_file(name, offset):
    # extract the components in 20190612_135951_6460_d750.JPG
    m = re.match(PAT_ALREADY, name)
    if not m:
        click.secho("filename != pattern", bold=True, fg='red')
        return

    # 20190612_135951_6460_d750.JPG: ('20190612', '135951', '6460', '_d750', '.JPG')
    s_date = m.group(1)
    s_time = m.group(2)
    s_counter = m.group(3)
    s_tag = m.group(4)
    s_ext = m.group(5)

    # if offset is specified, add offset and check again
    if offset != 0:
        new_time = increment_time(s_time, offset)
        if not new_time:
            return
        new_file = '{}_{}_{}{}{}'.format(s_date, new_time, s_counter, s_tag, s_ext)
        if not os.path.exists(new_file):
            click.echo('new file {} does not exist'.format(new_file))
            return
        return new_file  # new file located, done

    # no offset is specified, we need to find the file by the sequence number
    return locate_file_by_seq(s_counter, s_tag, s_ext)


def increment_time(time_str, offset):
    """increment hhmmss by offset seconds"""
    m = re.match(r'^(\d{2})(\d{2})(\d{2})$', time_str)
    if not m:
        click.echo("can't extract h:m:s from time str: {}".format(time_str))
        return
    h, m, s = m.group(1), m.group(2), m.group(3)
    sec = int(h) * 3600 + int(m) * 60 + int(s)  # convert to total seconds
    sec += offset
    if sec < 0:
        # sanity check to make sure sec is not negative
        # if negative we need to tweak the date, ignore for now
        click.echo("negative time is not yet supported")
        return

    return time.strftime('%H%M%S', time.gmtime(sec))  # works for negative number


def locate_file_by_seq(seq, tag, ext):
    """find file matching current sequence number"""
    m = glob.glob('*_*_{}{}{}'.format(seq, tag, ext))
    if not m:
        click.echo("no file with sequence {} found!".format(seq))
        return
    if len(m) > 1:
        click.echo("found more than 1 file with seq {}: {}".format(seq, len(m)))
        return
    return m[0]


if __name__ == '__main__':
    fix_picasa_ini()
