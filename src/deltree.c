// My deltree program on windows that uses shell API for maximum speed
// and UI awesomness

#include <stdio.h>
#include <errno.h>
#include <io.h>
#include <assert.h>
#include <time.h>

#include <windows.h>
#include <conio.h>


#define DELTREE_VER    "1.01"

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
Usage(const char *argv0)  // IN
{
   printf("deltree v%s [%s, %s] (gcc %s)\n\n"
          "Usage: %s [options] <path> ...\n\n"
          "Options:\n"
          "  -y    yes, suppresses prompting for confirmation\n"
          "  -s    silent, do not display any progress dialog\n"
          "  -n    do nothing, simulate the operation\n"
          "  -f    force, no prompting/silent (for rm compatibility)\n"
          "  -r    ignored (for rm compatibility)\n"
          "\nDelete directories and all the subdirectories and files in it.\n",
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
          char **argv,      // IN
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
      fprintf(stderr, "%s: calloc failed: %s\n",
              argv[0], strerror(errno));
      return FALSE;
   }

   // process the arguments. Didn't use <getopt.h> as we want to
   // handle both - and / for options, and we want to support mixing
   // options and path in any order.
   for (i = 1; i < argc; i++) {
      if (argv[i][0] == '-' || argv[i][0] == '/') {
         // support multiple options in one segment
         for (j = 1; argv[i][j] != '\0'; j++) {
            switch (argv[i][j]) {
            case 'y':  // disable prompting
            case 'Y':
               args->noPrompt = TRUE;
               break;
            case 'f':  // force (no prompt/silent, for rm compatibility)
            case 'F':
               args->noPrompt = TRUE;
               args->silent = TRUE;
               break;
            case 's':
            case 'S':
               args->silent = TRUE;
               break;
            case 'n':
            case 'N':
               args->simulate = TRUE;
               break;
            case 'r':  // ignored (for rm compatibility)
            case 'R':
               break;
            case 'h':
            case 'H':
            case '?':
               Usage(argv[0]);
               return FALSE;
            default:
               fprintf(stderr, "%s: invalid option -- '%c'\n",
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
PromptUser(const char *path)
{
   int rc = 0;

   // prompt like classic DOS deltree
   printf("Delete directory \"%s\" and all its subdirectories? [yNrq] ", path);
   char x = _getch();
   printf("%c\n", x);

   switch (x) {
   case 'y':
   case 'Y':
      rc = 1;
      break;
   case 3:   // ctrl-c
   case 'q':
   case 'Q':
      rc = -1;
      break;
   case 'r':
   case 'R':
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
DeleteItem(const char *path,       // IN
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
   size_t dirLength = strlen(path);
   char *removeDir = malloc(dirLength + 2);
   if (!removeDir) {
      fprintf(stderr, "malloc failed: %s\n", strerror(errno));
      return rc;
   }
   strcpy_s(removeDir, dirLength + 2, path);
   removeDir[dirLength + 1] = '\0';

   printf("[%d/%d] Deleting %s ... ", i, args->delSize, path);
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
         printf("[aborted] (%.3fs)\n", timeSpent);
      } else if (res != ERROR_SUCCESS) {
         printf("[failed/%d] (%.3fs)\n", res, timeSpent);
      } else {
         printf("[done] (%.3fs)\n", timeSpent);
         rc = TRUE;
      }
   } else {
      printf("[simulate]\n");
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
main(int argc,
     char *argv[],
     char *env[])
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
      const char *item = argv[args.delList[i]];
      // check if path exists
      if (_access(item, 0) != 0) {
         fprintf(stderr, "%s: %s\n", item, strerror(errno));
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
   if (args.delSize > 1) {
      printf("\nTotal: %d item(s) deleted (%.3fs)\n", success, timeSpent);
   }

exit:
   if (args.delList) {
      free(args.delList);
   }
   return rc;
}
