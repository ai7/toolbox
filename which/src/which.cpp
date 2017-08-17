//////////////////////////////////////////////////////////////////////

// this is the which program, similar to the one on the unxi system
// with the following exceptions

// it will find any matching executables in all directories on the
// path in the order it is searched by the os.

// raymond chi (raychi@mosaix.com)
// 11/26/1997

//////////////////////////////////////////////////////////////////////

#include <stdio.h>
#include <stdlib.h>
#include <direct.h>
#include <io.h>
#include <time.h>
#include <windows.h>
#include <winver.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <tchar.h>
#include <locale.h>

#include "resource.h"

//////////////////////////////////////////////////////////////////////

#define WHICH_VERSION _T("2.30")   // current version number

#define PATH_SEP      _T(';')      // ; for dos, : for unix
#define PATH_CHAR     _T('\\')     // the path character in the environment
#define EXT_CHAR      _T('.')      // file extension character

#define EOS           _T('\0')     // end of string

// bitwise directory flag
#define DIR_NOEXIST 1        // directory doesn't exist
#define DIR_DUP     2        // duplicated entry
#define DIR_CWD     4        // current working dir
#define DIR_SPACE   8        // entry has space at end
#define DIR_NULL   16        // null entry
#define DIR_NET    32        // network drive

#define TMP_SIZE    1024     // temp array string size
#define ALIAS_SIZE 32768     // alias size

#define FILEINFO_SIZE 256

#define FILESIZE_WIDTH 9     // allows up to 999mb.

//////////////////////////////////////////////////////////////////////

// the number of random strings in the string table that's used random
// strings in the string table must be consecutive
int rand_size;

// used for string table access, etc
TCHAR szTmp[TMP_SIZE];
TCHAR szTmp1[TMP_SIZE];

// what we store with each directory in the path
typedef struct {
    BOOL bValid;
    INT id;                    // an unique id, 1 - x
    TCHAR orig[_MAX_PATH];     // as it appears in the %path%
    TCHAR expanded[_MAX_PATH]; // the expanded version if applicable
    UINT type;                 // type, bit masked value
    INT value;                 // stores additional info if needed
} dir;

typedef struct {
    BOOL bValid;
    INT id;
    TCHAR szName[_MAX_PATH];
    TCHAR szShare[_MAX_PATH];
    TCHAR szCwd[_MAX_PATH];
    UINT uType;
    INT value;
} DriveMap;

dir * sep_path;                // poINT to the list of directories
INT p_size;                    // array size

TCHAR cwd[_MAX_PATH];          // the current working directory
TCHAR szFilename[_MAX_PATH];   // the file to print
TCHAR szVersion[FILEINFO_SIZE];          // version info
TCHAR szFileTime[FILEINFO_SIZE];         // file time info
TCHAR szFileSize[FILEINFO_SIZE];         // file size info

TCHAR fname[_MAX_FNAME];       // filename pointed by comspec
TCHAR ext[_MAX_EXT];

LPCTSTR pUser;
TCHAR szUser[TMP_SIZE];

// how long a date/time string takes
INT nDTsize;

// if a path entry has a single period, the current directory will not
// be searched first (4nt only)
BOOL curr_first = TRUE;

BOOL bFound = FALSE;

// the search order for exe files on nt/95 systems
LPCTSTR order1[] = {_T("com"),
		   _T("exe"),
		   _T("btm"),
		   _T("bat"),
		   _T("cmd")};
LPCTSTR order2[] = {_T("com"),
		   _T("exe"),
		   _T("bat"),
		   _T("cmd")};

LPCTSTR * order = order1;
INT order_len = 5;

LPCTSTR pEXE;

BOOL bPath = FALSE;

BOOL bVersion = FALSE; // display version info on found files?
BOOL bTime = FALSE;
BOOL bCurDir = FALSE;
BOOL bSize = FALSE;
BOOL bAliasOnly = FALSE;
BOOL bUpdateAlias = FALSE;
BOOL bMapping = FALSE;

BOOL bIs4NT = FALSE;

// 4nt alias related stuff
TCHAR szAliasFile[_MAX_PATH];  // full path to the alias file
TCHAR alias[ALIAS_SIZE];       // array holds alias keys
LPCTSTR lpAlias[ALIAS_SIZE];   // pointer to alias
INT nAlias;                    // number of alias found
INT nMaxKey;                   // maximum alias key length

// used to obtain the UNC name of a resource
BYTE cbTmp[1024];
UNIVERSAL_NAME_INFO * uName = (UNIVERSAL_NAME_INFO *) cbTmp;
DWORD dwSize = 1024;

//////////////////////////////////////////////////////////////////////

// string related functions

INT MyLoadString(UINT nID,
		 LPTSTR lpBuffer = szTmp1,
		 INT nBufferMax = TMP_SIZE)
{
    return LoadString(NULL, nID, lpBuffer, nBufferMax);
}

//////////////////////////////////////////////////////////////////////

// returns TRUE if the new path exist
BOOL exist_path(LPCTSTR path)
{
    // _access() return 0 if success, -1 otherwise
    return !(_taccess(path, 0));
}

// does a case insensitive comparison to see if the name
// already exist in path or not, if exist, return its index, if not, -1
INT already_exist(const dir * path, INT len, LPCTSTR name)
{
    INT i;
    for (i = 0; i < len; i++) {
	if (path[i].bValid && (lstrcmpi(path[i].orig, name) == 0)) {
	    return i;
	}
    }
    return -1;
}

// returns true if line only contains whitespace
BOOL WhiteSpace(LPCTSTR szLine)
{
    while (szLine[0] != EOS) {
	if (!_istspace(szLine[0]))
	    return FALSE;
	szLine = CharNext(szLine);
    }
    return TRUE;
}

// separate the path env variable into its components
// and return the number of dirs in path
INT separate_path(LPCTSTR path)
{

    INT i = 0,               // iter through the env string
	j = p_size,          // iter through the sep_path array
	t = 0,               // local iter for this directory
	nLen = lstrlen(path),
	nTmp;

    // do up to the null
    while (i <= nLen) {

	// if reached a null, or a path separator, do the important stuff
	if (path[i] == PATH_SEP || path[i] == EOS) {

	    sep_path[j].orig[t] = EOS;  // null terminate it
	    sep_path[j].bValid = TRUE;   // tag it valid
	    sep_path[j].type = 0;        // null the type bitmask

	    if (t > 0) { // if it has something

		// first, if it contains only white space
		if (WhiteSpace(sep_path[j].orig)) {
		    sep_path[j].orig[0] = EOS;
		    sep_path[j].type |= DIR_SPACE;
		    sep_path[j].type |= DIR_NULL;
		    goto done;
		}

		// if entry ends in a white space, tag it
		if (_istspace(sep_path[j].orig[t - 1])) {
		    sep_path[j].type |= DIR_SPACE;
		}

		// first expand curr dir if it is a dot.
		if (lstrcmp(_T("."), sep_path[j].orig) == 0) {
		    lstrcpyn(sep_path[j].orig, cwd, _MAX_PATH); // copy cur dir
		    sep_path[j].type |= DIR_CWD;   // set bit flag
		    curr_first = FALSE; // will not insert current dir
		}

		// then check to see if it is a duplicate
		if ((nTmp = already_exist(sep_path, j, sep_path[j].orig)) != -1) {
		    // copy attribute plus the dir dup attribute
		    sep_path[j].type |= sep_path[nTmp].type | DIR_DUP;
		    sep_path[j].value = nTmp;
		} else { // only if not a duplicate do we check exist or not
		    // finally check to see if it exist or not
		    if (!exist_path(sep_path[j].orig)) { // if something & exist
			sep_path[j].type |= DIR_NOEXIST;
		    }
		}
	    } else { // a null entry
		sep_path[j].type |= DIR_NULL;
	    }

	  done:

	    t = 0;
	    j++; // always increase index

	} else { // not a path separator or null, so just copy it
	    sep_path[j].orig[t++] = path[i];
	}

	// finally increment the i counter
	i++;

    }

    // remove the last empty one if exist
    if (j > p_size && sep_path[j - 1].orig[0] == EOS)
	j--;

    // add the current working dir if applicable

    // if parsing PATH, and need to add, and first is not setup
    if (bPath && curr_first && !sep_path[0].bValid) {

	sep_path[0].bValid = TRUE;   // tag it valid

	// now, need to go through the array, and tag any one that
	// matches the cwd we inserted in the front as duplicate
	for (INT i = 1; i < j; i++) {
	    if (sep_path[i].bValid && sep_path[i].orig[0] != EOS) {
		if (lstrcmpi(sep_path[i].orig, sep_path[0].orig) == 0) {
		    sep_path[i].type = sep_path[i].type | DIR_DUP;
		    sep_path[i].value = 0;
		}
	    }
	}

    }

    return j;
}

// given a path, and a file, print the necessary info
// file, date/time, version, if requested
void print_file(LPCTSTR path, LPCTSTR file, BOOL bNoEnding)
{

    DWORD dwJunk;
    INT cbSize;
    LPVOID lpBuffer;
    UINT uLen;
    VS_FIXEDFILEINFO * vTest;

    struct _stat buf;
    struct tm * newtime;

    // first generate the filename
    if (bNoEnding) {
	_stprintf(szFilename, _T("%s\\%s"), path, file);
    } else {
	_stprintf(szFilename, _T("%s%s"), path, file);
    }

    // next obtain the version info if requested on the file
    if (bVersion) {
	cbSize = GetFileVersionInfoSize(szFilename, &dwJunk);
	if (cbSize == 0) {
	    szVersion[0] = EOS; // no version info available
	} else {
	    // allocate space for the version buffer
	    BYTE * pbVersion = new BYTE[cbSize];
	    if (GetFileVersionInfo(szFilename,
				   NULL, // ignored parameter
				   cbSize,
				   pbVersion) != 0) { // success
		if (VerQueryValue(pbVersion, // buffer pointer
				  _T("\\"),      // root structure
				  &lpBuffer,
				  &uLen)) {
		    // assign pointers
		    vTest = (VS_FIXEDFILEINFO *) lpBuffer;
		    _stprintf(szVersion, _T(" (%d.%d.%d.%d)"),
			      HIWORD(vTest->dwFileVersionMS),
			      LOWORD(vTest->dwFileVersionMS),
			      HIWORD(vTest->dwFileVersionLS),
			      LOWORD(vTest->dwFileVersionLS));
		} else {
		    //  [VerQueryValue() failed]
		    MyLoadString(IDS_FAIL_GETVER1, szVersion);
		}
	    } else { // get version failed
		//  [GetFileVersionInfo() failed]
		MyLoadString(IDS_FAIL_GETVER2, szVersion);
	    }
	    delete [] pbVersion;
	}
    } else {
	szVersion[0] = EOS; // version not requested
    }

    // finally, obtain the file date/time if requested
    szFileTime[0] = EOS;
    szFileSize[0] = EOS;

    if (bTime || bSize) {
	if (_tstat(szFilename, &buf) == 0) { // get the file statistics
	    if (bTime) {
		newtime = localtime(&buf.st_mtime); // convert time to local
		_tcsftime(szFileTime, FILEINFO_SIZE,
			  _T("%x %H:%M:%S "), newtime); // kinda cheated
	    }
	    if (bSize) {
		// size up to 999mb
		_stprintf(szFileSize, _T("%*ld "),
			  FILESIZE_WIDTH, buf.st_size);
	    }
	} else { // file statistics not obtained
	    if (bTime)
		_stprintf(szFileTime, _T("%*s"),
			  nDTsize + 1, ""); // 18 space
	    if (bSize)
		_stprintf(szFileSize, _T("%*s"),
			  FILESIZE_WIDTH + 1, ""); // 10 space
	}
    }

    // print out the requested info to the screen
    _tprintf(_T("%s%s%s%s%s\n"), szFileTime, szFileSize,
	     (bTime || bSize) ? _T(" ") : _T(""),
	     szFilename, szVersion);
}

// check to see if the string ends with a backslash, a bit complicated
// because of the dbcs stuff
BOOL EndInBackSlash(LPCTSTR szStr)
{
    LPCTSTR lpLastChar = NULL;  // the last character
    while (szStr[0] != EOS) { // while not null, go to next
	lpLastChar = szStr;
	szStr = CharNext(szStr);
    }
    return (lpLastChar && lpLastChar[0] == PATH_CHAR);
}

// print all files that matches the wild card, if used
// version information is also printed here
INT print_all(LPCTSTR file, LPCTSTR path)
{
    struct _tfinddata_t c_file;
    long hFile;
    BOOL no_ending = FALSE;

    if (!EndInBackSlash(path)) {
	no_ending = TRUE;
    }

    if ((hFile = _tfindfirst(file, &c_file)) == -1L) {
	return 0;
    } else {
	bFound = TRUE;
	print_file(path, c_file.name, no_ending);
	while(_tfindnext(hFile, &c_file) == 0) {
	    print_file(path, c_file.name, no_ending);
	}
	_findclose(hFile);
	return 1;
    }
}

// build a filename from whats there
void make_file(LPTSTR target, LPCTSTR path, LPCTSTR file)
{
    lstrcpy(target, path);
    if (!EndInBackSlash(path)) {
	lstrcat(target, _T("\\"));
    }
    lstrcat(target, file);
}

// make an file out of the path and file
void make_file(LPTSTR target, LPCTSTR path, LPCTSTR file, LPCTSTR ext)
{
    TCHAR buffer[_MAX_PATH];
    lstrcpyn(buffer, file, _MAX_PATH);
    lstrcat(buffer, _T("."));
    lstrcat(buffer, ext);
    make_file(target, path, buffer);
}

// returns true if the filename already has an extension
INT has_extension(LPCTSTR file)
{
    INT i;
    for (i = 0; file[i] != EOS; i++) {
	if (file[i] == EXT_CHAR)
	    return 1;
    }
    return 0;
}

// this file looks into the path to see where the file is
void path_find(LPCTSTR file)
{

    TCHAR filename[_MAX_PATH];
    INT i, j;

    if (has_extension(file)) {  // file has extension

	for (j = 0; j < p_size; j++) {   // for each dir in path
	    if (sep_path[j].bValid &&                // if valid
		sep_path[j].orig[0] != EOS &&       // has something
		!(sep_path[j].type & DIR_DUP) &&     // not duplicated
		!(sep_path[j].type & DIR_NOEXIST)) { // and exist
		make_file(filename, sep_path[j].orig, file);
		print_all(filename, sep_path[j].orig);
	    }
	}

    } else { // no extension, so has to search through all possible ext

	// then do the normal search
	for (j = 0; j < p_size; j++) {         // for each dir in path
	    for (i = 0; i < order_len; i++) {  // search each kind of exe
		if (sep_path[j].bValid &&                // if valid
		    sep_path[j].orig[0] != EOS &&       // has something
		    !(sep_path[j].type & DIR_DUP) &&     // not duplicated
		    !(sep_path[j].type & DIR_NOEXIST)) { // and exist
		    make_file(filename, sep_path[j].orig, file, order[i]);
		    print_all(filename, sep_path[j].orig);
		}
	    }
	}

    }

}

void print_path(void)
{
    INT i,
	j = 1, // number of dir in path count
	nWidth;

    // figure out how much space the [%d] takes
    TCHAR sTmp[256];
    _itot(p_size, sTmp, 10);
    nWidth = lstrlen(sTmp);

    for (i = 0; i < p_size; i++) {
	if (sep_path[i].bValid) {
	    if (sep_path[i].expanded[0] != EOS) {
		_stprintf(sTmp, _T(" [%s]"), sep_path[i].expanded);
	    } else {
		sTmp[0] = EOS;
	    }
	    _tprintf(_T("[%*d] %c%c%c%c%c%c  %s%s\n"),
		     nWidth,
		     j++,
		     (sep_path[i].type & DIR_CWD) ? _T('*') : _T('_'),
		     (sep_path[i].type & DIR_NOEXIST) ? _T('X') : _T('_'),
		     (sep_path[i].type & DIR_NET) ? _T('N') : _T('_'),
		     (sep_path[i].type & DIR_DUP) ? _T('D') : _T('_'),
		     (sep_path[i].type & DIR_NULL) ? _T('E') : _T('_'),
		     (sep_path[i].type & DIR_SPACE) ? _T('S') : _T('_'),
		     sep_path[i].orig,
		     sTmp);
	}
    }
}

// this function setup the path array
void setup_path(LPCTSTR p)
{
    if (p) {
	p_size = separate_path(p);
    } else {
	sep_path[0].bValid = TRUE;   // tag it valid
	p_size = 1;
    }
}

// this function detects to see if 4nt is running
int Is4NT()
{
    // first, obtain the comspec environment variable, and get the
    // filename from it, if it contains a 4, then it is

    LPTSTR p;

    TCHAR drive[_MAX_DRIVE];
    TCHAR dir[_MAX_DIR];

    INT i = 0;

    p = _tgetenv(_T("ComSpec"));

    if (p) {
	_tsplitpath(p, drive, dir, fname, ext);
	while (fname[i] != EOS) {
	    if (fname[i] == '4')
		return TRUE;
	    i++;
	}
    } else {
	return FALSE; // ComSpec not set, unlikely to be 4nt
    }

    // if not, then try a bit harder, see what
    // %@eval[3+7] is, if it is 7, then yes, else no.
    return FALSE; // for now, I mean the above should be sufficient

}

// figures out the path to the alias file
void AliasFile()
{
    // first, figure out the temp directory
    TCHAR szTemp[_MAX_PATH];

    if (GetTempPath(_MAX_PATH, szTemp) == 0) {
	lstrcpy(szTemp, _T("./")); // use current directory
    }

    // build the filename
    make_file(szAliasFile, szTemp, _T("which.tmp"));

}

// recreates the alias file
void MakeAliasFile()
{

    // next, delete the which.tmp
    DeleteFile(szAliasFile);

    // prepares the cmdline
    TCHAR szCmd[256];

    _stprintf(szCmd, _T("echo [alias] > %s"), szAliasFile);
    _tsystem(szCmd);
    _stprintf(szCmd, _T("alias >> %s"), szAliasFile);
    _tsystem(szCmd);

}

void ReadAliasList()
{

    // if file is not created, return
    if (!exist_path(szAliasFile)) {
	bIs4NT = FALSE;
	return;
    }

    // next, read in the file
    INT nSize;
    nSize = GetPrivateProfileString(_T("alias"), // section name
				    NULL, // keyname
				    _T(""),
				    alias,
				    ALIAS_SIZE,
				    szAliasFile);

    // finally break the alias array, separated by '\0''s.
    INT i = 0, j = 0;

    INT t;
    // while less than size
    while (i < nSize && alias[i] != EOS) {
	lpAlias[j++] = alias + i;
	t = lstrlen(alias + i);
	if (t > nMaxKey)
	    nMaxKey = t;
        i += lstrlen(alias + i) + 1; // skip the string and null
    }
    nAlias = j; // set alias size

}

// does lpA match lpB, * and ? are only effective in lpA
// only * and ? have special meaning
BOOL RegMatch(LPCTSTR lpA, LPCTSTR lpB)
{

    INT i = 0;

    if (lpA[0] == EOS && lpB[0] == EOS) { // both string reached end
	return TRUE;
    } else if (lpA[0] == EOS) { // end of pattern but not string
	return FALSE;
    } else if (lpB[0] == EOS) { // end of string but not pattern
	if (lpA[0] == _T('?') || lpA[0] == _T('*')) { // if pattern ? or *
	    return RegMatch(lpA + 1, lpB);    // regmatch next patt char
	} else {                 // pattern str normal char, str end, false
	    return FALSE;
	}
    }

    // neither have ended
    if (lpA[0] == _T('?')) {
	return (RegMatch(lpA + 1, lpB) ||      // ? represent 0 char
		RegMatch(lpA + 1, lpB + 1));   // ? represent 1 char
    } else if (lpA[0] == _T('*')) {
	while (!RegMatch(lpA + 1, lpB + i)) {  // while still not match
	    if (lpB[i] == EOS)                // if reached end, false
		return FALSE;
	    i++;                               // check next one
	}
	return TRUE;
    } else { // both normal char, just compare it
	if (_totupper(lpA[0]) == _totupper(lpB[0])) {
	    return RegMatch(lpA + 1, lpB + 1);
	} else {
	    return FALSE;
	}
    }

}

// see if anything match the alias list
void FindAliasMatch(LPCTSTR lpFile)
{
    INT i;
    TCHAR szAlias[1024];

    // %-*s : aliased to `%s'\n
    MyLoadString(IDS_ALIAS_MATCH);

    for (i = 0; i < nAlias; i++) {
	if (RegMatch(lpFile, lpAlias[i])) {
	    GetPrivateProfileString(_T("alias"), // section name
				    lpAlias[i], // keyname
				    _T(""),
				    szAlias,
				    1024,
				    szAliasFile);
	    _tprintf(szTmp1, nMaxKey, lpAlias[i], szAlias);
	    bFound = TRUE;
	}
    }
}

void print_help(LPCTSTR szMsg = NULL)
{

    // seed the random number generator
    srand((unsigned) time(NULL));


    // loads a random string from the string table
    if (szMsg == NULL) {
	// if szMsg is not null, then it is szTmp, hence, we can safely load
	// into szTmp
	MyLoadString(IDS_RAND1 + (rand() % rand_size));
	_stprintf(szTmp, szTmp1, pUser);
	szMsg = szTmp;
    }

    // loads the help screen
    // to modify the help screen, change the helpscreen.txt and copy it into
    // string table editor
    MyLoadString(IDS_HELP);

    // print the help screen
    _tprintf(szTmp1,
	     WHICH_VERSION,              // version
	     _T(__DATE__), _T(__TIME__), // build date/time
	     fname, ext,                 // comspec filename
	     pEXE,                       // exe name
	     szAliasFile,                // alias file
	     szMsg);

}

// returns the number of dirs in path
int GetNumDirInPath(LPCTSTR pVal)
{
    INT i,
	nCount = 1;               // start with 1
    for (i = 0; pVal[i] != EOS; i++) {
	if (pVal[i] == PATH_SEP)
	    nCount++;
    }
    return nCount;
}

// list all the jokes
void ListJokes()
{
    for (int i = 0; i < rand_size; i++) {
	MyLoadString(IDS_RAND1 + i);
	_tprintf(szTmp1, pUser);
	_tprintf(_T("\n"));
    }
}

INT GetDTSize(void)
{
    time_t long_time;        // current time
    struct tm * newtime;     // converted to tm
    time(&long_time);
    newtime = localtime(&long_time);
    _tcsftime(szFileTime, FILEINFO_SIZE, _T("%x %H:%M:%S"), newtime);
    return lstrlen(szFileTime);
}

void SetupUNC()
{

    INT i;

    TCHAR szDrive[_MAX_DRIVE];
    TCHAR szDir[_MAX_DIR];
    TCHAR szFname[_MAX_FNAME];
    TCHAR szExt[_MAX_EXT];

    // for each thing in the path array
    for (i = 0; i < p_size; i++) {

	sep_path[i].expanded[0] = EOS;           // nuke the exp string

	if (sep_path[i].bValid &&
	    sep_path[i].orig[0] != EOS &&        // has something
	    !(sep_path[i].type & DIR_NOEXIST)) { // and exist

	    // if duplicated and original entry is a network dir
	    if ((sep_path[i].type & DIR_DUP) &&
		(sep_path[sep_path[i].value].type & DIR_NET)) {
		sep_path[i].type |= DIR_NET;   // mark network bit
		lstrcpyn(sep_path[i].expanded, // copy net path
			 sep_path[sep_path[i].value].expanded,
			 _MAX_PATH);
		continue;
	    }

	    // get the drive letter
	    _tsplitpath(sep_path[i].orig,
			szDrive,
			szDir,
			szFname,
			szExt);

	    // if has a drive letter, then
	    if (szDrive[0] != EOS) {
		if (WNetGetUniversalName(szDrive, // original name
					 UNIVERSAL_NAME_INFO_LEVEL,
					 cbTmp,
					 &dwSize) == NO_ERROR) {
		    lstrcpyn(sep_path[i].expanded,
			     uName->lpUniversalName,
			     _MAX_PATH);
		    sep_path[i].type |= DIR_NET;
		}
	    } else { // cannot extract out drive letter, so UNC?
		sep_path[i].type |= DIR_NET;
	    }

	}
    }

}

void ListDriveMapping()
{

    // used with splitpat()
    TCHAR szDrives[_MAX_DRIVE];
    TCHAR szDir[_MAX_DIR];
    TCHAR szFname[_MAX_FNAME];
    TCHAR szExt[_MAX_EXT];

    // type of drive
    TCHAR szType[7][256];

    // maximum length of drive desc and share name, so output looks nice
    INT nType = 0;
    INT nShare = 0;
    INT nLen;        // tmp var used to calc above 2

    // load the type of drives from string table, and figure out
    // max length
    INT i;
    for (i = 0; i < 7; i++) {
	nLen = MyLoadString(IDS_REMOVABLE + i, szType[i]);
	if (nLen > nType)
	    nType = nLen;
    }
    // add padding after the drive type, 2 space
    nType += 2;

    // the current drive integer, 1 = A, etc
    INT nMaxDrive = 26,
	drive;
    DriveMap * Drives = new DriveMap[nMaxDrive];

    // bit array of available drives
    DWORD dwDrives = GetLogicalDrives();
    TCHAR szBuffer[_MAX_PATH];

    for (drive = 0, i = 1; drive < nMaxDrive; drive++, i *= 2) {

	if (dwDrives & i) { // if it is a valid drive

	    // initialize the struct
	    Drives[drive].bValid = TRUE;
	    Drives[drive].id = drive + 1;
	    Drives[drive].szName[0] = EOS;
	    Drives[drive].szShare[0] = EOS;
	    Drives[drive].szCwd[0] = EOS;

	    // format the drive string
	    _stprintf(Drives[drive].szName, _T("%c:"), drive + 'A');

	    // get the type
	    Drives[drive].uType = GetDriveType(Drives[drive].szName);

	    // get the current working dir on that drive
	    // skips the first 2, floppy disk
	    if (Drives[drive].id > 2) {
		_tgetdcwd(Drives[drive].id,
			  szBuffer,
			  _MAX_PATH);
		_tsplitpath(szBuffer,
			    szDrives,
			    szDir,
			    szFname,
			    szExt);
		_stprintf(Drives[drive].szCwd,
			  _T("%s%s%s"), szDir, szFname, szExt);
	    }

	    switch (Drives[drive].uType) {

	      case DRIVE_REMOVABLE:
		  Drives[drive].value = 0;
		  break;
	      case DRIVE_FIXED:
		  Drives[drive].value = 1;
		  break;
	      case DRIVE_REMOTE:
		  Drives[drive].value = 2;
		  // get the UNC name if it is a remote drive
		  if (Drives[drive].uType == DRIVE_REMOTE) {
		      if (WNetGetUniversalName(Drives[drive].szName,
					       UNIVERSAL_NAME_INFO_LEVEL,
					       cbTmp,
					       &dwSize) == NO_ERROR) {
			  _stprintf(Drives[drive].szShare,
				    _T("%s"),
				    uName->lpUniversalName);
			  nLen = lstrlen(Drives[drive].szShare);
			  if (nLen > nShare)
			      nShare = nLen;
		      }
		  }
		  break;
	      case DRIVE_CDROM:
		  Drives[drive].value = 3;
		  break;
	      case DRIVE_RAMDISK:
		  Drives[drive].value = 4;
		  break;
	      case DRIVE_NO_ROOT_DIR:
		  Drives[drive].value = 5;
		  break;
	      case DRIVE_UNKNOWN:
	      default:
		  Drives[drive].value = 6;
		  break;

	    }

	} else {
	    Drives[drive].bValid = FALSE;
	}

    }

    if (nShare > 0)
	nShare += 1;

    for (i = 0; i < nMaxDrive; i++) {

	if (Drives[i].bValid) {

	    _tprintf(_T("(%s) = %-*s%-*s%s\n"),
		     Drives[i].szName,
		     nType,
		     szType[Drives[i].value],
		     nShare,
		     Drives[i].szShare,
		     Drives[i].szCwd);

	}

    }

    delete [] Drives;

}

// the extern "C" is required for a unicode wmain console app to link
// correctly because this is a c++ app and the compiler adds random
// char after function name to support overloading, wow. Thanks go to
// Paul-Henri for solving this problem.
extern "C" int _tmain(int argc, TCHAR *argv[], TCHAR *env[])
{

    LPCTSTR pEnv = NULL;   // what env variable to look for
    pEXE = argv[0];        // the EXE name

    INT i,                 // tmp var
	* nSearchArray,    // points to argv[] that needs to ne searched
	nSearch = 0;       // how many needs to be searched

    // at maximum it can be this
    nSearchArray = new INT[argc];

    // get the name of the current user
    pUser = _tgetenv(_T("NAME"));
    if (!pUser) {
	pUser = _tgetenv(_T("USERNAME"));
	if (!pUser) {
	    // Someone
	    MyLoadString(IDS_USER, szUser);
	    pUser = szUser;
	}
    }

    // detect if 4nt or 4dos is running
    if (!(bIs4NT = Is4NT())) {
	order = order2;
	order_len = 4;
    }

    // figures out the path to the alias file
    AliasFile();

    // then read in the random string size
    MyLoadString(IDS_RAND_SIZE);
    rand_size = _ttoi(szTmp1);

    // parse the command line
    for (i = 1; i < argc; i++) {

	// if its an parameter
	if (argv[i][0] == _T('-') || argv[i][0] == _T('/')) {

	    if (lstrcmpi(argv[i] + 1, _T("h")) == 0 || // if help requested
		lstrcmpi(argv[i] + 1, _T("?")) == 0) {
		print_help();
		return 0;
	    } else if (argv[i][1] == _T('i') ||
		       argv[i][1] == _T('I')) {
		if (argv[i][2] == EOS) {
		    // Argument missing for parameter: `%s'
		    MyLoadString(IDS_ARG_MISSING);
		    _stprintf(szTmp, szTmp1, argv[i] + 1);
		    print_help(szTmp);
		    return 1;
		} else if (pEnv != NULL) {
		    // Environment variable already set to `%s': `%s'
		    MyLoadString(IDS_DUP_ENV);
		    _stprintf(szTmp, szTmp1, pEnv, argv[i] + 2);
		    print_help(szTmp);
		    return 1;
		} else {
		    pEnv = argv[i] + 2; // use this env var
		}
	    } else if (lstrcmpi(argv[i] + 1, _T("d")) == 0) {
		bIs4NT = FALSE; // alias search disabled
	    } else if (lstrcmpi(argv[i] + 1, _T("f")) == 0) {
		bIs4NT = TRUE; // alias search forced
	    } else if (lstrcmpi(argv[i] + 1, _T("v")) == 0) {
		bVersion = TRUE; // display version
	    } else if (lstrcmpi(argv[i] + 1, _T("t")) == 0) {
		bTime = TRUE; // display time
	    } else if (lstrcmpi(argv[i] + 1, _T("c")) == 0) {
		bCurDir = TRUE; // current directory only
	    } else if (lstrcmpi(argv[i] + 1, _T("s")) == 0) {
		bSize = TRUE; // display filesize
	    } else if (lstrcmpi(argv[i] + 1, _T("a")) == 0) {
		bAliasOnly = TRUE; // search only alias
	    } else if (lstrcmpi(argv[i] + 1, _T("w")) == 0) {
		bUpdateAlias = TRUE; // update alias file
	    } else if (lstrcmpi(argv[i] + 1, _T("j")) == 0) {
		ListJokes();
		return 0;
	    } else if (lstrcmpi(argv[i] + 1, _T("m")) == 0) {
		bMapping = TRUE;
	    } else {
		// Invalid parameter: `%s'
		MyLoadString(IDS_INVALID_PARM);
		_stprintf(szTmp, szTmp1, argv[i] + 1);
		print_help(szTmp);
		return 1;
	    }
	} else {
	    // need to add this to the search list
	    nSearchArray[nSearch++] = i;
	}
    }

    if (bMapping) {
	_tprintf(_T("\n"));
	ListDriveMapping();
	_tprintf(_T("\n"));
	// return 0;
    }

    // if user did not specify a env var, set it to path
    if (pEnv == NULL) {
	pEnv = _T("Path"); // the default environment var to use
	bPath = TRUE;
    } else {  // some features enabled if we are parsing path
	if (lstrcmpi(pEnv, _T("Path")) == 0)
	    bPath = TRUE;
    }

    if (bIs4NT && bPath) { // if in 4nt mode and searching path
	// if alias file does not exist, or forced mode, then update it
	if (!exist_path(szAliasFile) || bUpdateAlias) {
	    MakeAliasFile();
	}
    }

    // first get the current directory
    if (_tgetcwd(cwd, _MAX_PATH) == NULL) {
	// %s: _getcwd() error.\n
	MyLoadString(IDS_BAD_CWD);
	_ftprintf(stderr, szTmp1, pEXE);
	return 1;
    }

    // now all set, do the important stuff

    INT nDirs;     // number of directories in path
    LPCTSTR pVal;  // value of env var

    // get the environment variable pointed by pEnv
    pVal = _tgetenv(pEnv);
    if (!pVal && !bPath) { // if env not defined and not searching path
	// %s: not in environment: `%s'\n
	MyLoadString(IDS_NOT_IN_ENV);
	_ftprintf(stderr, szTmp1, pEXE, pEnv);
	delete [] nSearchArray;
	exit(1);
    }

    if (pVal) { // if env var found
	nDirs = GetNumDirInPath(pVal) + 1;
    } else { // no PATH env defined, so just current dir
	nDirs = 1;
    }
    sep_path = new dir[nDirs]; // might insert current dir

    if (bIs4NT || !bPath) {   // if is 4nt, just reserve space
	sep_path[0].bValid = FALSE;
    } else {        // if not 4nt, then first is always current dir
	sep_path[0].bValid = TRUE;   // tag it valid
	if (bAliasOnly)
	    bAliasOnly = FALSE; // alias only search not applicable
    }
    sep_path[0].type = DIR_CWD;  // first dir, can't be dup or invalid
    lstrcpyn(sep_path[0].orig, cwd, _MAX_PATH);

    p_size = 1; // reserve space for the curr dir if need insert

    // setup the sep_path array
    if (!bCurDir) {         // if not only current dir
	setup_path(pVal);
    } else if (!sep_path[0].bValid) { // only if first pos is still not valid
	sep_path[0].bValid = TRUE;   // tag it valid
    }

    // if no arg, then just print the path
    if (nSearch == 0) {

	// expand any path to UNC if applicable
	SetupUNC();

	print_path();
	return 0;

    }

    // need to do a search

    // set the locale to the current system default
    _tsetlocale(LC_ALL, _T(""));
    // figure out how long a date/time string is
    nDTsize = GetDTSize();

    // read in the alias list if running under 4nt
    if (bIs4NT && bPath) {
	ReadAliasList();
    }

    LPCTSTR pSearch;

    // the search array contains integer corresponding to the
    // actual argv position of the file specified
    for (i = 0; i < nSearch; i++) {
	bFound = FALSE;
	pSearch = argv[nSearchArray[i]]; // file to look for
	if (bIs4NT && bPath) {
	    FindAliasMatch(pSearch);
	}
	if (!bAliasOnly) {
	    path_find(pSearch);
	}
	if (!bFound) {
	    if (bAliasOnly) {
		// %s not found in alias list.\n
		MyLoadString(IDS_NOTFOUND_ALIAS);
		_tprintf(szTmp1, pSearch);
	    } else if (bCurDir) {
		// then print not found
		if (has_extension(pSearch)) {
		    // %s not found in %s.\n
		    MyLoadString(IDS_NOTFOUND4);
		    _tprintf(szTmp1, pSearch, cwd);
		} else {
		    if (bIs4NT) {
			// %s{.com|.exe|.btm|.bat|.cmd} not found in %s.\n
			MyLoadString(IDS_NOTFOUND5);
		    } else {
			// %s{.com|.exe|.bat|.cmd} not found in %s.\n
			MyLoadString(IDS_NOTFOUND6);
		    }
		    _tprintf(szTmp1, pSearch, cwd);
		}
	    } else {
		// then print not found
		if (has_extension(pSearch)) {
		    // %s not found in %%%s.\n
		    MyLoadString(IDS_NOTFOUND1);
		    _tprintf(szTmp1, pSearch, pEnv);
		} else {
		    if (bIs4NT) {
			// %s{.com|.exe|.btm|.bat|.cmd} not found in %%%s.\n
			MyLoadString(IDS_NOTFOUND2);
		    } else {
			// %s{.com|.exe|.bat|.cmd} not found in %%%s.\n
			MyLoadString(IDS_NOTFOUND3);
		    }
		    _tprintf(szTmp1, pSearch, pEnv);
		}
	    }
	}
    }

    delete [] sep_path;
    delete [] nSearchArray;

    return 0;
}
