#!/usr/bin/env python
#
# my awesome music tagging utility

import pdb

import sys, os, platform, time, datetime
import argparse, re, logging
import signal

# for reading in memory file
import cStringIO

# for converting/resizing images
import Image

# for reading/writing tags in music files
import mutagen, mutagen.flac, mutagen.mp3, mutagen.id3


__version__ = '1.0.0.' + '$Revision: #1 $'[12:-2]
__date__    = '$Date: 2014/06/28 $'[7:-2].replace('/','-')

PROG_NAME   = 'qTag'
PROG_VER    = 'v%s (%s)' % (__version__, __date__)

PROG_NAME_MAIN = PROG_NAME + ' ' + PROG_VER

# command line options
g_args = None

# signal script to gracefully exit
g_exit = False

# statistics

######################################################################
# statistics object
######################################################################


class Stat:
    '''keeps track of statistics'''

    def __init__(self):
        self.folder = 0
        self.folderskipped = 0
        self.files = 0
        self.processed = 0
        self.skipped = 0
        self.replaced = 0
        self.nochange = 0
        self.current = 0        # current item being processed

    # var++ methods
    def folderInc(self):
        self.folder += 1

    def folderskippedInc(self):
        self.folderskipped += 1

    def filesInc(self):
        self.files += 1

    def processedInc(self):
        self.processed += 1

    def skippedInc(self):
        self.skipped += 1

    def replacedInc(self):
        self.replaced += 1

    def nochangeInc(self):
        self.nochange += 1

    def currentInc(self):
        self.current += 1

    # get methods
    def getCurrent(self):
        return self.current

    # convert to string
    def __str__(self):
        s = ('%d/%d dirs/skipped, %d files, %d/%d/%d processed/replaced/skipped, %d not changed' %
             (self.folder, self.folderskipped,
              self.files, self.processed, self.replaced, self.skipped,
              self.nochange))
        return s

g_stat = Stat()


######################################################################
# catch control-c
######################################################################


def signal_handler(signal, frame):
    logging.error('SIGINT detected!')
    global g_exit
    g_exit = True


######################################################################
# create album.jpg
######################################################################


def findFolderImage(files):
    '''Look for folder.jpg, folder.png, etc that will be used for the
    source for creating the cover image file album.jpg.

    @param files: list of files to look for
    @return: folder.jpg file, if any
    '''
    fname = 'folder'
    fext = ['.png', '.jpg']

    for f in files:
        name, ext = os.path.splitext(f)
        if (name.lower() == fname and
            ext.lower() in fext):
            # return the actual file with original casing
            return name + ext

    return None


def findAlbumImage(files):
    '''Find the album file that will be embedded into the mp3/flac. First
    Look for album.jpg, then folder.jpg

    @param files: list of files to process
    @return: image file to use as cover, or None
    '''
    if 'album.jpg' in files:
        return 'album.jpg'
    elif 'folder.jpg' in files:
        return 'folder.jpg'
    else:
        return None


def hasMusicFiles(files):
    '''Are there any mp3 or flac files in this folder

    @param files: list of files to look through
    @return: True/False
    '''
    fext = ['.mp3', '.flac']
    for f in files:
        name, ext = os.path.splitext(f)
        if (ext.lower() in fext):
            return True
    return False


def createCoverImage(root, folder_img):
    '''Create album.jpg from folder.jpg in the specified root folder.

    folder.jpg is the source image that could be of large dimension,
    album.jpg would be the smaller (600x600 default) image that would
    be embedded into the music files.

    if folder.jpg is smaller than the target dimension, then the image
    will be used as is. It will not be resized up.

    @param root: directory where folder.jpg resides
    @param_img: name of folder.jpg file
    '''
    changed = False

    in_file = os.path.join(root, folder_img)
    assert(os.path.exists(in_file))

    g_stat.currentInc()
    logging.info('[%d] %s', g_stat.getCurrent(), in_file)

    # does output file exist?
    out_file = os.path.join(root, g_args.target)
    if (os.path.exists(out_file)):
        if not g_args.force:
            logging.info("\t[0] target already exist: %s", g_args.target)
            sys.stdout.write('s')
            g_stat.skippedInc()
            return
        else:
            logging.info("\t[0] output exist, will overwrite!")

    im = Image.open(in_file)
    logging.info("\t[1] format: %s, size: %s, mode: %s",
                 im.format, im.size, im.mode)

    # convert to rgb if needed (for png files)
    # itune supposely don't read png files in mp3
    if im.mode != 'RGB':
        logging.info('\t[2] converting image to %s ...', 'RGB')
        im = im.convert('RGB')
        changed = True

    # shrink image if needed
    cur_max = max(im.size)
    if (cur_max > g_args.size):
        logging.info("\t[3] resizing image to %d ...", g_args.size)
        im.thumbnail((g_args.size, g_args.size), Image.ANTIALIAS)
        logging.info("\t\timage is (%d, %d)", im.size[0], im.size[1])
        changed = True

    # some png are already in RGB, so catch it here
    if im.format != 'JPEG':
        changed = True

    if changed:
        if not g_args.simulate:
            logging.info("\t[4] saving image to %s ...", g_args.target)
            im.save(out_file)
        else:
            logging.info("\t[4] simulate saving image to %s ...", g_args.target)
        g_stat.processedInc()
        sys.stdout.write('.')
    else:
        logging.info("\t[4] no change needed, skipped ...")
        sys.stdout.write('-')
        g_stat.nochangeInc()

    return


def createAllCovers(target_dir):
    '''Iterate through subdirectories in target_dir and create album.jpg
    in each music folder encountered.

    @param target_dir: root folder to process
    '''
    # output some help for the status screen
    print('')
    print('.: processed')
    print('s: skipped')
    print('-: not changed')
    print('/: no folder.jpg')
    print('')

    # register our ctrol-c handler to gracefully exit
    logging.info('registering SIGINT handler ...')
    signal.signal(signal.SIGINT, signal_handler)

    # returned tuple is for entire subtree, not just this level
    for root, dirs, files in os.walk(target_dir):
        if g_exit:
            sys.stdout.write('\n\nError: SIGINT')
            logging.error('exiting createAllCovers loop due to SIGINT')
            break
        # only interested in folders with music files. as this
        # corresponds to cd album. other folders, such as grouping
        # folders, are not interesting in the count.
        if (hasMusicFiles(files)):
            folder_img = findFolderImage(files)
            g_stat.folderInc()
            if folder_img:
                g_stat.filesInc()
                createCoverImage(root, folder_img)
            else:
                g_stat.folderskippedInc()
                sys.stdout.write('/')
    print('')


######################################################################
# embed album.jpg into mp3/flac files
######################################################################


def compareCover(curImage, newImage, newIm):
    '''Compare current and new artwork

    @param curImage: current embedded artwork, raw data
    @param newImage: new artwork, raw data
    @param newIm: Image obj of new artwork

    @return: True/False
    '''
    curIm = imFromMemory(curImage)
    logging.info("\t\t\tcur: format: %s, size: %s, mode: %s",
                 curIm.format, curIm.size, curIm.mode)
    logging.info("\t\t\tnew: format: %s, size: %s, mode: %s",
                 newIm.format, newIm.size, newIm.mode)
    if curImage == newImage:
        logging.debug('\t\t\tcurrent artwork is binarily identical')
        return True
    else:
        logging.debug('\t\t\tcurrent artwork is different')
        return False


def hasCoverArt(audio, newArtwork, newIm):
    '''Does this audio already have a cover art, and is it the same as the
    new one we are trying to add?

    @param audio: mutagen audio object, file we trying to update
    @param newArtwork: new artwork, raw data
    @param newIm: Image obj of new artwork, cache obj

    @return 0: no artwork
            1: identical artwork
            2: different artwork
    '''
    try:
        # this is for flac files
        x = audio.pictures
        if x:
            if compareCover(x[0].data, newArtwork, newIm):
                return 2
            else:
                return 1
    except Exception:
        pass

    # apic is for mp3 files
    if 'APIC:' in audio:
        if compareCover(audio.tags['APIC:'].data, newArtwork, newIm):
            return 2
        else:
            return 1

    return 0


def loadFile(f):
    '''Load the file into memory

    @param f: file to load
    @return: in memory object from read()
    '''
    return open(f, 'rb').read()


def imFromMemory(data):
    '''Return an IM object from in memory data

    @param data: in memory image file
    @return Image object
    '''
    return Image.open(cStringIO.StringIO(data))


def createFlacPicture(data):
    '''generate the Picture object to insert into flac files

    @param data: in memory jpg file
    @return: mutagen.flac.Picture object
    '''
    image = mutagen.flac.Picture()
    image.type = 3
    image.mime = 'image/jpeg'
    image.desc = ''
    image.data = data
    return image


def createApicObj(picData):
    '''Create the APIC object to insert into mp3 files

    @param picData: in memory jpg file
    @return: mutagen.id3.APIC object
    '''
    apic = mutagen.id3.APIC(
        encoding=3,        # 3 is for utf-8
        mime='image/jpeg', # image/jpeg or image/png
        type=3,            # 3 is for the cover image
        desc='',           # needed or will create APIC:None, silly!
        data=picData
    )
    return apic


# cover art for flac is stored in audio.pictures
def addCoverFlac(fname, imageData, im):
    '''add album cover into flac file

    @param fname: input flac file name
    @param imageData: in memory album.jpg to embed
    @param im: the Image object that corresponds to imageData
    '''
    logging.info("\t\t[1] reading flac file ...")
    audio = mutagen.File(fname)

    # compare artwork and use appropriate on screen display char
    artworkResult = hasCoverArt(audio, imageData, im)
    if artworkResult == 0:
        # no artwork
        statusChar = '.'
    elif artworkResult == 1:
        # different artwork
        statusChar = 'r'
    elif artworkResult == 2:
        # identical artwork
        statusChar = '#'
        if not g_args.force:
            logging.info('\t\t[2] cover art detected, skipping')
            sys.stdout.write('s')
            g_stat.skippedInc()
            return
        else:
            logging.info('\t\t[2] cover art detected')

    logging.info('\t\t[3] adding cover art ...')
    audio.clear_pictures()
    audio.add_picture(createFlacPicture(imageData))

    if not g_args.simulate:
        logging.info('\t\t[3] saving file ...')
        audio.save()
    else:
        logging.info('\t\t[3] simulating saving file ...')

    if artworkResult == 1:
        g_stat.replacedInc()
    else:
        g_stat.processedInc()
    sys.stdout.write(statusChar)


# cover art for mp3 is stored in audio['APIC']
def AddCoverMp3(fname, imageData, im):
    '''add cover into mp3 file f

    @param fname: input mp3 filename
    @param imageData: in memory album.jpg to embed
    @param im: the Image object that corresponds to imageData
    '''
    logging.info("\t\t[1] reading mp3 file ...")
    audio = mutagen.File(fname)

    # make sure we have id3 tags as safety mechanism. all my files
    # should have it, if not, probably reading error or corrupt files,
    # better to abort
    if audio.tags:
        logging.info('\t\t[2] id3 tags: %s', str(audio.tags.keys()))
    else:
        logging.info('\t\t[2] no id3 tags found, skipped ...')
        g_stat.skippedInc()
        sys.stdout.write('e')
        return
        # use this to create empty tag set to continue
        # audio.add_tags()

    # compare artwork and use appropriate on screen display char
    artworkResult = hasCoverArt(audio, imageData, im)
    if artworkResult == 0:
        statusChar = '.'
    elif artworkResult == 1:
        statusChar = 'r'
    elif artworkResult == 2:
        statusChar = '#'
        if not g_args.force:
            logging.info('\t\t[3] cover art detected, skipping')
            g_stat.skippedInc()
            sys.stdout.write('s')
            return
        else:
            logging.info('\t\t[3] cover art detected')

    # todo: compare existing coverart to see if same as new one trying
    # to add

    logging.info('\t\t[4] adding cover art ...')
    apicObj = createApicObj(imageData)
    audio.tags.add(apicObj)
    logging.info('\t\t[5] id3 tags: %s', str(audio.tags.keys()))

    if not g_args.simulate:
        logging.info('\t\t[6] saving file ...')
        audio.save()
    else:
        logging.info('\t\t[6] simulating saving file ...')

    if artworkResult == 1:
        g_stat.replacedInc()
    else:
        g_stat.processedInc()
    sys.stdout.write(statusChar)


def addCover(root, files, album_img):
    '''process music files in files, and embed album_img into files

    @param root: folder to process music files for
    @param files: list of files in folder
    @param album_img: album.jpg file to embed in music files
    '''
    count = 0;
    # load image into memory for reuse
    img_file = os.path.join(root, album_img)
    coverImg = loadFile(img_file)
    im = imFromMemory(coverImg)

    for f in files:
        # check to see if we need to quit
        if g_exit:
            return
        # ensure file exists
        in_file = os.path.join(root, f)
        assert(os.path.exists(in_file))
        name, ext = os.path.splitext(f)

        if ext.lower() in ['.mp3', '.flac']:
            # increment status, then log, or off by 1 error
            g_stat.filesInc()
            count += 1
            logging.info('\t[%d] %s', count, f)
            if (ext.lower() == '.mp3'):
                AddCoverMp3(in_file, coverImg, im)
            elif (ext.lower() == '.flac'):
                addCoverFlac(in_file, coverImg, im)
            # none music files are skipped


def embedAllCovers(target_dir):
    '''Iterate through subdirectories in target_dir and embed album.jpg
    into the corresponding mp3/flac file.

    @param target_dir: root folder to process
    '''
    print('')
    print('/: folder ')
    print('.: added artwork')
    print('r: replaced artwork (different)')
    print('s: skipped (same)')
    print('#: replaced artwork (same)')
    print('e: no id3 tag')
    print('')

    # register our ctrol-c handler to gracefully exit. this is needed
    # because audio.save() will corrupt file if interrupted!!
    logging.info('registering SIGINT handler ...')
    signal.signal(signal.SIGINT, signal_handler)

    # returned tuple is for entire subtree, not just this level
    for root, dirs, files in os.walk(target_dir):
        if g_exit:
            sys.stdout.write('\n\nError: SIGINT')
            logging.error('exiting embedAllCovers loop due to SIGINT')
            break
        # only interested in folders with music files
        if (hasMusicFiles(files)):
            # update stats
            g_stat.folderInc()
            g_stat.currentInc()
            # log info, needs to be after status or off by 1 error
            logging.info('[%d] %s', g_stat.getCurrent(), root)
            sys.stdout.write('/')
            # find the album cover file
            album_img = findAlbumImage(files)
            if album_img:
                # add cover to all music files in folder
                addCover(root, files, album_img)
            else:
                # consecutive // will indicate skipped folders on output
                logging.info('\tno album art file, skipping folder ...')
                g_stat.folderskippedInc()
    print('')


######################################################################
# main functions
######################################################################

def getLogName():
    '''Get the logfile name to use'''
    return os.path.join(os.environ['TEMP'], 'qtag.log')

def getSystemInfo():
   '''Get some system information for debugging
   '''
   name = platform.system()
   ver = platform.release()
   if name == 'Darwin':
      name = 'MacOS'
      ver = platform.mac_ver()[0]
   elif name == 'Linux':
      dist = platform.linux_distribution()
      name = dist[0]
      ver = dist[1]

   # host: MacOS 10.8.5, x86_64, python 2.7.2 [2014-03-18 14:43:18 PDT]
   infoStr = '%s: %s %s, %s, python %s [%s]' % \
       (platform.node(), name, ver,
        platform.machine(), sys.version.split()[0],
        time.strftime('%Y-%m-%d %H:%M:%S %Z'))

   return infoStr


def getTimeInfo(start, end):
    '''Returns elapsed time info

    @param start: starting time
    @param end: ending time
    @return: formatted elapsed time
    '''
    elapsed = (end - start)

    start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start))
    end_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end))

    # http://stackoverflow.com/questions/775049/python-time-seconds-to-hms
    elapsed_time = str(datetime.timedelta(seconds=elapsed))

    return 'start   : %s\nend     : %s\nelapsed : %s' % (
        start_time, end_time, elapsed_time
    )


def MainCover():
    '''Main function for handling adding covers'''
    createAllCovers('.')
    print('\nTotal: ' + str(g_stat))
    return 0


def MainEmbed():
    '''Main function for handling embedding covers'''
    embedAllCovers('.')
    print('\nTotal: ' + str(g_stat))
    return 0


def MainInfo():
    print('\nNot yet implemented')
    return


def parseArgs():
   '''Parse command line arguments'''

   # add the parent parser
   parser = argparse.ArgumentParser(
       description = PROG_NAME_MAIN)

   # create a set of subcommand parsers
   subparsers = parser.add_subparsers(help='commands (-h for more help)',
                                      dest='mode')

   # create album cover art from folder.* files
   parser_c = subparsers.add_parser('c',
                                    help='create album.jpg from folder.jpg')
   parser_c.add_argument('-s', dest='size',
                         help='image size [600]',
                         type=int, default=600)
   parser_c.add_argument('-t', dest='target',
                         help='target file name [album.jpg]',
                         default='album.jpg')
   parser_c.add_argument('-f', dest='force',
                         help='overwrite target file, if any',
                         action='store_true')
   parser_c.add_argument('-n', dest='simulate',
                         help='do nothing, simulate operation',
                         action='store_true')

   # embed album.jpg into flac/mp3 files
   parser_e = subparsers.add_parser('e',
                                    help='embed album.jpg into music files')
   parser_e.add_argument('-f', dest='force',
                         help='overwrite embedded cover, if any',
                         action='store_true')
   parser_e.add_argument('-n', dest='simulate',
                         help='do nothing, simulate operation',
                         action='store_true')

   # display information about stuff
   #parser_i = subparsers.add_parser('i',
   #                                 help='get info about image/music file')

   return parser.parse_args()


def Main():
   '''The main function.
   '''
   global g_args
   g_args = parseArgs()

   if g_args.mode in ['i', 'c', 'e']:

       logFile = getLogName()
       logging.basicConfig(filename=logFile,
                           format='%(asctime)s| %(levelname)-8s| %(message)s',
                           level=logging.DEBUG)
       logging.info('***** %s started *****', PROG_NAME_MAIN)

       # print header, and record time
       print PROG_NAME_MAIN
       print getSystemInfo()
       print 'log: %s' % logFile

       start_time = time.time()

       if g_args.mode == 'i':
           MainInfo()

       if g_args.mode == 'c':
           MainCover()

       if g_args.mode == 'e':
           MainEmbed()

       # print time info
       end_time = time.time()
       print '\n' + getTimeInfo(start_time, end_time)

   else:
       parser.print_help()

   return 0


######################################################################
# script entry point, must be at the end
######################################################################

if __name__ == '__main__':
    sys.exit(Main())

######################################################################
#
# TODO:
#  - implement ctrl-c interrupt handler so don't corrupt files [done 6/28/2014]
#  - implement comparison of build-in image with one to add, skip if same [done 6/28/2014]
#  - implement 'i' command for info
#
######################################################################
