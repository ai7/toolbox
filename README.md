# deltree

Fastest way to delete large directory trees on Windows

## Overview

MS-DOS 6.0 introduced deltree.exe as a convenient way to delete an
entire subtree. However this tool is missing on NT based systems such
as XP, Win7, etc.

On those systems, you can use "**rd /s**" to accomplish the same task.
However, it is significantly slower than deleting a tree from Windows
Explorer via shift-DELETE. This becomes really apparent if you are
deleting a large tree such as the build output directory.

Windows port of UNIX tools such as **rm** suffers the same performance
problem. They simply don't run as fast as deleting via Windows
Explorer.

This project implements a simple Windows command line deltree tool
that calls the same API that Windows Explorer uses to delete the
directory tree. You get the command line tool with the speed of the
shell delete.

## Usage

```
Usage: deltree <path> ...
```

```
c:\>deltree test
Delete directory "test" and all its subdirectories? [yN] y
Deleting test ... [done]
```

Similar to Explorer, if deletion will take more than a few seconds, a
progress dialog will be displayed.

## DOS DELTREE

Here are some screen grabs of deltree.exe on MS-DOS 6.22

![deltree1](https://github.com/ai7/deltree/raw/master/images/dos-deltree1.png)

![deltree2](https://github.com/ai7/deltree/raw/master/images/dos-deltree2.png)

## Notes

Customization options will be added.
