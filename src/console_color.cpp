// console_color.cpp
//
// Implementation for the ConsoleColor module.
//

#include "console_color.h"

namespace ConsoleColor {

    // retain foreground bits, clear background bits
    static const WORD fgMask ( FOREGROUND_BLUE      |
                               FOREGROUND_GREEN     |
                               FOREGROUND_RED       |
                               FOREGROUND_INTENSITY );

    // retain background bits, clear foreground bits
    static const WORD bgMask ( BACKGROUND_BLUE      |
                               BACKGROUND_GREEN     |
                               BACKGROUND_RED       |
                               BACKGROUND_INTENSITY );


    // constructor
    ConsoleColor::ConsoleColor()
    {
        WORD color;

        // get handle to console
        hConsole_ = GetStdHandle(STD_OUTPUT_HANDLE);

        // save current console color
        if (getCurrentColor(color)) {
            initialColor_ = color;
        } else {
            // cmd.exe default: 0x07 (gray on black)
            // powershell.exe default: 0x56 (yellow on magenta ?)
            //                         [(236,237,240) on (1,36,86)]
            initialColor_ = gray;
        }
        
        curColor_ = initialColor_;
    }


    // destructor
    ConsoleColor::~ConsoleColor()
    {
        // restore initial console color
        setColor(initialColor_);
    }


    // return the current console color
    bool
    ConsoleColor::getCurrentColor(WORD &color)  // OUT
    {
        CONSOLE_SCREEN_BUFFER_INFO info;

        if (!GetConsoleScreenBufferInfo(hConsole_, &info)) {
            return false;
        }
        color = info.wAttributes;

        return true;
    }


    // set console text to specified color (foreground + background)
    bool
    ConsoleColor::setColor(WORD color)  // IN
    {
        if (!SetConsoleTextAttribute(hConsole_, color)) {
            return false;
        }
        curColor_ = color;
    }


    // set console text to the specified enum color, which can be a
    // foreground or background color.
    bool
    ConsoleColor::setColor(Color color)  // IN
    {
        WORD c = curColor_;
        if (color > white) {
            // this is a background color, keep current foreground
            c &= fgMask;
        } else {
            // this is a foreground color, keep current background
            c &= bgMask;
        }
        c |= color;

        return setColor(c);
    }

    
    // alternative way to set color via << override
    std::ostream & operator<<(std::ostream& os, Color color)
    {
        WORD c;
        CONSOLE_SCREEN_BUFFER_INFO info;
        HANDLE hConsole;

        hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
        if (GetConsoleScreenBufferInfo(hConsole, &info)) {
            c  = info.wAttributes;
            if (color > white) {
                // background color, clear background bits
                // if color is bg_black, the 4 background bit is 0 so ok.
                c &= fgMask;
            } else {
                // foreground color, clear foreground bits
                c &= bgMask;
            }
            c |= color;   // set fg color
            SetConsoleTextAttribute(hConsole, c);
        }

        return os;
    }


}
