// console_color.h
//
// This module allows you to output colored text to the console.
//
// Using ConsoleColor object:
//   ConsoleColor cc;
//   cc.setColor(green);
//   printf("Hello world in green");
//
// Using stream directly:
//   cout << green << "green text" << gray << " normal text" << endl;
//
// ConsoleColorWin will restore the current console color on
// destruction.
//
// good console colors: gray, green, cyan, red, yellow, white.
// on powershell, color 5/6/7 is different from cmd.exe for some reason.


#pragma once

#include <ostream>
#include <windows.h>

namespace ConsoleColor {

    // list of standard console colors:
    //   cmd.exe        : color /?
    //   powershell.exe : [Enum]::GetValues([ConsoleColor])
    enum Color {
        // ***** foreground colors *****
        black           =  0,  // standard color, intensity bit off
        dark_blue       =  1,
        dark_green      =  2,
        dark_cyan       =  3,
        dark_red        =  4,
        dark_magenta    =  5,
        dark_yellow     =  6,
        gray            =  7,  // default text
        dark_gray       =  8,  // bright color, intensity bit on
        blue            =  9,
        green           = 10,
        cyan            = 11,
        red             = 12,
        magenta         = 13,
        yellow          = 14,
        white           = 15,
        // ***** background colors *****
        bg_black        = 16 << 4,  // so we can tell bg/fg black apart
        bg_dark_blue    =  1 << 4,
        bg_dark_green   =  2 << 4,
        bg_dark_cyan    =  3 << 4,
        bg_dark_red     =  4 << 4,
        bg_dark_magenta =  5 << 4,
        bg_dark_yellow  =  6 << 4,
        bg_gray         =  7 << 4,
        bg_dark_gray    =  8 << 4,
        bg_blue         =  9 << 4,
        bg_green        = 10 << 4,
        bg_cyan         = 11 << 4,
        bg_red          = 12 << 4,
        bg_magenta      = 13 << 4,
        bg_yellow       = 14 << 4,
        bg_white        = 15 << 4,
    };

    
    class ConsoleColor
    {
      public:
        ConsoleColor();
        virtual ~ConsoleColor();

        virtual bool setColor(WORD color);
        virtual bool setColor(Color color);

      private:
        HANDLE hConsole_;       // console handle
        WORD   initialColor_;   // saved initial console color
        WORD   curColor_;       // current console color
        
        bool getCurrentColor(WORD &color);
    };


    // alternative way to set color in << stream
    std::ostream & operator<<(std::ostream& os, Color color);

}
