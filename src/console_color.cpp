// console_color.cpp
//
// Module that set console text color
//

#ifdef _WIN32
#include <windows.h>
#endif

#include "console_color.h"

#ifdef _WIN32


// constructor
ConsoleColorWin::ConsoleColorWin()
{
    uint16_t color;

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

    // extract out the foreground/background color
    separateColor(initialColor_, curForeground_, curBackground_);
}


// destructor
ConsoleColorWin::~ConsoleColorWin()
{
    // restore initial console color
    setColor(initialColor_);
}


// return the current console color
bool
ConsoleColorWin::getCurrentColor(uint16_t &color)  // OUT
{
    CONSOLE_SCREEN_BUFFER_INFO info;

    if (!GetConsoleScreenBufferInfo(hConsole_, &info)) {
        return false;
    }
    color = info.wAttributes;

    return true;
}


// break color into foreground and background
void
ConsoleColorWin::separateColor(uint16_t color,     // IN
                               Color &foreground,  // OUT
                               Color &background)  // OUT
{
    foreground = (Color) (color & 0xF);   // 4 LSB bits
    background = (Color) (color & 0xF0);  // next 4 bits
}


// set console text to specified color
bool
ConsoleColorWin::setColor(uint16_t color)  // IN
{
    if (!SetConsoleTextAttribute(hConsole_, color)) {
        return false;
    }
    
    return true;
}


// set text to specified foreground/background color
bool
ConsoleColorWin::setColor(Color foreground,  // IN
                          Color background)  // IN
{
    uint16_t c = foreground | (background << 4);
    return setColor(c);
}


// change foreground color to specified, leave background unchanged.
bool
ConsoleColorWin::setForeground(Color color)  // IN
{
    return setColor(color | curBackground_);
}


// change background color to specified, leave foreground unchanged.
bool
ConsoleColorWin::setBackground(Color color)  // IN
{
    return setColor((color << 4) | curForeground_);
}


#endif  // _WIN32
