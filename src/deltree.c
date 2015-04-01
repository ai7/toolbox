// My deltree program on windows that uses shell API for maximum speed
// and UI awesomness

#include <stdio.h>
#include <errno.h>
#include <io.h>
#include <assert.h>
#include <time.h>

#include <windows.h>
#include <conio.h>


#define DELTREE_VER    L"1.0.2"

#ifndef FALSE
#define FALSE          0
#endif

#ifndef TRUE
#define TRUE           1
#endif

typedef char           Bool;

/**
 * holding all the variables processed by cmd line options
 */
typedef struct AppInputs_ {
   Bool noPrompt;  // do not prompt for confirmation
   Bool silent;    // do not show progress dialog
   Bool simulate;  // simulate operation
   int *delList;   // index to argv that are not an option (- or /)
   int  delSize;   // number of items in deleteList
} AppInputs;


/**
 * Print the help screen.
 *
 * @param argv0 path to exe, argv[0]
 * @return None
 */
void
Usage(const wchar_t *argv0)  // IN
{
   wprintf_s(L"deltree v%ws [%hs, %hs] (gcc %hs)\n\n"
             L"Usage: %ws [options] <path> ...\n\n"
             L"Options:\n"
             L"  -y    yes, suppresses prompting for confirmation\n"
             L"  -s    silent, do not display any progress dialog\n"
             L"  -n    do nothing, simulate the operation\n"
             L"  -f    force, no prompting/silent (for rm compatibility)\n"
             L"  -r    ignored (for rm compatibility)\n"
             L"\nDelete directories and all the subdirectories and files in it.\n",
             DELTREE_VER, __DATE__, __TIME__, __VERSION__, argv0);
}


/**
 * Process command line options and fill in AppInputs
 *
 * @param argc argc from main()
 * @param argv argv from main()
 * @param args AppInputs struct to be filled
 * @return TRUE on success
 */
Bool
ParseArgs(int argc,         // IN
          wchar_t **argv,   // IN
          AppInputs *args)  // OUT
{
   int i, j;   // index for looping argv and individual options
   int k = 0;  // index for saving non option args

   assert(args);

   if (argc <= 1) {
      Usage(argv[0]);
      return FALSE;
   }

   // allocate memory for delete list
   args->delList = calloc(argc, sizeof(int));
   if (!args->delList) {
      fwprintf_s(stderr, L"%ws: calloc failed: %ws\n",
                 argv[0], strerror(errno));
      return FALSE;
   }

   // process the arguments. Didn't use <getopt.h> as we want to
   // handle both - and / for options, and we want to support mixing
   // options and path in any order.
   for (i = 1; i < argc; i++) {
      if (argv[i][0] == L'-' || argv[i][0] == L'/') {
         // support multiple options in one segment
         for (j = 1; argv[i][j] != L'\0'; j++) {
            switch (argv[i][j]) {
            case L'y':  // disable prompting
            case L'Y':
               args->noPrompt = TRUE;
               break;
            case L'f':  // force (no prompt/silent, for rm compatibility)
            case L'F':
               args->noPrompt = TRUE;
               args->silent = TRUE;
               break;
            case L's':
            case L'S':
               args->silent = TRUE;
               break;
            case L'n':
            case L'N':
               args->simulate = TRUE;
               break;
            case L'r':  // ignored (for rm compatibility)
            case L'R':
               break;
            case L'h':
            case L'H':
            case L'?':
               Usage(argv[0]);
               return FALSE;
            default:
               fwprintf_s(stderr, L"%ws: invalid option -- '%c'\n",
                          argv[0], argv[i][j]);
               return FALSE;
            }
         }
      } else {
         args->delList[k++] = i;  // save non option args to list
         assert(k < argc);
      }
   }

   args->delSize = k;

   /* Check for mandatory arguments */
   if (args->delSize == 0) {
      Usage(argv[0]);
      return FALSE;
   }

   return TRUE;
}


/**
 * Display a prompt and asks the user y/n.
 *
 * @param path path to show in the prompt
 * @return 0: no, 1: yes, 2: remaining, -1: quit
 */
int
PromptUser(const wchar_t *path)
{
   int rc = 0;

   // prompt like classic DOS deltree
   wprintf_s(L"Delete directory \"%ws\" and all its subdirectories? [yNrq] ", path);
   wchar_t x = _getch();
   wprintf_s(L"%c\n", x);

   switch (x) {
   case L'y':
   case L'Y':
      rc = 1;
      break;
   case 3:   // ctrl-c
   case L'q':
   case L'Q':
      rc = -1;
      break;
   case L'r':
   case L'R':
      rc = 2;
      break;
   }

   return rc;
}


/**
 * Run deltree on a particular directory
 *
 * @param path path to delete
 * @param args argument object
 * @param i index of current item in overall list
 * @return TRUE on success, FALSE otherwise.
 */
BOOL
DeleteItem(const wchar_t *path,    // IN
           const AppInputs *args,  // IN
           int i)                  // IN

{
   Bool rc = FALSE;
   int res;
   FILEOP_FLAGS fFlags = FOF_NOCONFIRMATION;
   clock_t begin, end;
   double timeSpent;

   if (!path || !path[0]) {
      return rc;
   }

   // double null terminate input path
   size_t dirLength = wcslen(path);
   wchar_t *removeDir = malloc(sizeof(wchar_t) * (dirLength + 2));
   if (!removeDir) {
      fwprintf_s(stderr, L"malloc failed: %ws\n", strerror(errno));
      return rc;
   }
   wcscpy_s(removeDir, dirLength + 2, path);
   removeDir[dirLength + 1] = L'\0';

   wprintf_s(L"[%d/%d] Deleting %ws ... ", i, args->delSize, path);
   fflush(stdout);

   // Populate the SHFILEOPSTRUCT and delete the folder
   if (args->silent) {
      fFlags = FOF_NO_UI;
   }
   SHFILEOPSTRUCT fileOp = {NULL, FO_DELETE, removeDir, NULL,
                            fFlags, FALSE, NULL, NULL};

   if (!args->simulate) {
      begin = clock(); // save start time
      res = SHFileOperation(&fileOp);
      end = clock();   // save end time
      timeSpent = (double) (end - begin) / CLOCKS_PER_SEC;
      if (fileOp.fAnyOperationsAborted == TRUE) {
         wprintf_s(L"[aborted] (%.3fs)\n", timeSpent);
      } else if (res != ERROR_SUCCESS) {
         wprintf_s(L"[failed/%d] (%.3fs)\n", res, timeSpent);
      } else {
         wprintf_s(L"[done] (%.3fs)\n", timeSpent);
         rc = TRUE;
      }
   } else {
      wprintf_s(L"[simulate]\n");
      rc = TRUE;
   }

   free(removeDir);

   return rc;
}


/**
 * entry point
 *
 * @param argc argv array length
 * @param argv command line parameter array
 * @param env environment block
 * @return integer return code
 */
int
wmain(int argc,
      wchar_t *argv[],
      wchar_t *env[])
{
   int i;
   int rc = 0;
   int success = 0;
   AppInputs args = {0};
   clock_t begin, end;
   double timeSpent;

   // process the command line arguments and fill the args struct
   if (!ParseArgs(argc, argv, &args)) {
      rc = 1;
      goto exit;
   }

   // run deltree on any argument that's not an option/switch
   begin = clock(); // save start time
   for (i = 0; i < args.delSize; i++) {
      const wchar_t *item = argv[args.delList[i]];
      // check if path exists
      if (_waccess(item, 0) != 0) {
         fwprintf_s(stderr, L"%ws: %ws\n", item, strerror(errno));
         continue;
      }
      // get confirmation if necessary
      if (!args.noPrompt) {
         int key = PromptUser(item);
         if (key == 0) {  // no
            continue;
         } else if (key == 2) {  // y and remaining
            args.noPrompt = TRUE;
         } else if (key == -1) {  // quit
            break;
         }
      }
      // now delete it
      if (DeleteItem(item, &args, i+1)) {
         success++;
      }
   }
   end = clock(); // save end
   timeSpent = (double) (end - begin) / CLOCKS_PER_SEC;
   // output overall status if silent mode and > 1 items
   if (args.delSize > 1 && args.noPrompt) {
      wprintf_s(L"\nTotal: %d item(s) deleted (%.3fs)\n", success, timeSpent);
   }

exit:
   if (args.delList) {
      free(args.delList);
   }
   return rc;
}
