#!/usr/bin/env python

# merge pdf1, pdf2, pdf3
#   ./pdf-merge.py m doc1.pdf doc2.pdf doc3.pdf
# merge pdf1 (all except last 2 pages), and pdf2
#   ./pdf-merge.py m doc1.pdf -p :-1 doc2.pdf
# display info about pdf file
#   ./pdf-merge.py i doc.pdf

import click
from PyPDF2 import PdfFileReader, PdfFileMerger, PageRange


# https://github.com/mstamy2/PyPDF2/blob/master/PyPDF2/pagerange.py
PAGE_RANGE_HELP = """Remember, page indices start with zero.
        Page range expression examples:
            :     all pages.                   -1    last page.
            22    just the 23rd page.          :-1   all but the last page.
            0:3   the first three pages.       -2    second-to-last page.
            :3    the first three pages.       -2:   last two pages.
            5:    from the sixth page onward.  -3:-1 third & second to last.
        The third, "stride" or "step" number is also recognized.
            ::2       0 2 4 ... to the end.    3:0:-1    3 2 1 but not 0.
            1:10:2    1 3 5 7 9                2::-1     2 1 0.
            ::-1      all pages in reverse order.
"""


@click.group()
def main():
    pass


def print_dict_aligned(values):
    # type: (dict) -> None
    max_len = 0
    for k in values:
        max_len = max(max_len, len(k))
    f = '   {:<' + str(max_len) + '} : {}'  # left align fixed width -> "{:<XX}: {}"
    for k, v in values.items():
        print(f.format(k, v))


@main.command(name='i', help='display info about PDF file')
@click.argument('pdf_file', required=True, type=click.File('rb'))
def pdf_info(pdf_file):
    # open pdf file
    pdf = PdfFileReader(pdf_file)
    # get useful data
    number_of_pages = pdf.getNumPages()
    info = pdf.getDocumentInfo()
    # print the stuff
    print('{}: {} page(s)'.format(pdf_file.name, number_of_pages))
    print_dict_aligned(info)


@main.command(name='m', help='merge multiple PDFs into one PDF file')
@click.argument('pdf_files', required=True, type=click.File('rb'), nargs=-1)
@click.option('-o', '--output', 'output_file', type=click.File('wb'),
              default='output.pdf', help='output PDF file [output.pdf]')
@click.option('-p', '--pages', multiple=True, help='PageRange specification for each input pdf')
def pdf_merge(pdf_files, output_file, pages):
    print('creating {} ...'.format(output_file.name))
    merger = PdfFileMerger()
    for i, f in enumerate(pdf_files):
        if i < len(pages):
            print('  {}: merging in pages -> {}'.format(f.name, pages[i]))
            # directly use PageRange specification
            merger.append(fileobj=f, pages=PageRange(pages[i]))
        else:
            print('  {}: merging all pages'.format(f.name))
            merger.append(fileobj=f)
    print('writing {} ...'.format(output_file.name))
    merger.write(output_file)


if __name__ == '__main__':
    main()
