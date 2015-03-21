// My deltree program on windows that uses shell API for maximum speed
// and UI awesomness

// -y supress confirmation
// can operate on more than one folder

#include <stdio.h>
#include <errno.h>
#include <io.h>

#include <windows.h>
#include <conio.h>

#ifndef FALSE
#define FALSE          0
#endif

#ifndef TRUE
#define TRUE           1
#endif


/**
 * Print the help screen.
 *
 * @param argv0 path to exe, argv[0]
 * @return void
 */
void
PrintHelp(const char *argv0)
{
   printf("Usage: %s <path> ...\n", argv0);
}


/**
 * Display a prompt and asks the user y/n.
 *
 * @param path path to show in the prompt
 * @return whether user choose Yes
 */
BOOL
PromptUser(const char *path)
{
   // prompt like classic DOS deltree
   printf("Delete directory \"%s\" and all its subdirectories? [yN] ", path);
   char x = _getch();
   printf("%c\n", x);

   return (x == 'y' || x == 'Y');
}


/**
 * Run deltree on a particular directory
 *
 * @param path path to delete
 * @return TRUE on success, FALSE otherwise.
 */
BOOL
DelTree(const char *path)
{
   if (!path || !path[0]) {
      return FALSE;
   }

   // check if path exists
   if (_access(path, 0) != 0) {
      printf("%s: %s\n", path, strerror(errno));
      return FALSE;
   }

   if (!PromptUser(path)) {
      return FALSE;
   }

   // double null terminate input path
   size_t dirLength = strlen(path);
   char *removeDir = malloc(dirLength + 2);
   if (!removeDir) {
      printf("malloc failed: %s\n", strerror(errno));
      return FALSE;
   }
   strcpy_s(removeDir, dirLength + 2, path);
   removeDir[dirLength + 1] = '\0';

   printf("Deleting %s ... ", path);
   fflush(stdout);

   // Populate the SHFILEOPSTRUCT and delete the folder
   SHFILEOPSTRUCT fileOp = {NULL, FO_DELETE, removeDir, NULL,
                            FOF_NOCONFIRMATION,
                            FALSE, NULL, NULL};
   int res = SHFileOperation(&fileOp);

   if (fileOp.fAnyOperationsAborted == TRUE) {
      printf("[aborted]\n");
   } else if (res != ERROR_SUCCESS) {
      printf("[failed/%d]\n", res);
   } else {
      printf("[done]\n");
   }

   free(removeDir);

   return TRUE;
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

   if (argc < 2) {
      PrintHelp(argv[0]);
      return 0;
   }

   for (i = 1; i < argc; i++) {
      if (argv[i][0] == '-' || argv[i][0] == '/') {
         printf("%s: not implemented yet\n", argv[i]);
         continue;
      }
      DelTree(argv[i]);
   }

   return 0;
}
