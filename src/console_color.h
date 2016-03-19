// console_color.h
//

#pragma once

#include <stdint.h>


// list of standard console colors:
//   cmd.exe        : color /?
//   powershell.exe : [Enum]::GetValues([ConsoleColor])
enum Color {
    black  = 0,    // standard color, 0 - 7, intensity bit off
    dark_blue,
    dark_green,
    dark_cyan,
    dark_red,
    dark_magenta,  
    dark_yellow,
    gray,          // default text
    dark_gray,     // bright color, 8 - F, intensity bit on
    blue,
    green,
    cyan,
    red,
    magenta,
    yellow, 
    white
};
// good console colors: gray, green, cyan, red, yellow, white
// on powershell, color 5/6/7 is different from cmd.exe for some reason.


// interface for setting colors
class IConsoleColor
{
  public:
    virtual bool setColor(uint16_t color) = 0;
    virtual bool setColor(Color foreground, Color background) = 0;
    virtual bool setForeground(Color color) = 0;
    virtual bool setBackground(Color color) = 0;
};


#ifdef _WIN32

// implementation for Windows
class ConsoleColorWin: public IConsoleColor
{
  public:
    ConsoleColorWin();
    virtual ~ConsoleColorWin();
    
    virtual bool setColor(uint16_t color);
    virtual bool setColor(Color foreground, Color background);
    virtual bool setForeground(Color color);
    virtual bool setBackground(Color color);

  private:
    HANDLE hConsole_;       // console handle
    WORD   initialColor_;   // saved initial console color
    Color  curForeground_;  // current forground color
    Color  curBackground_;  // current background color

    bool getCurrentColor(WORD &color);
    void separateColor(WORD color, Color &foreground, Color &background);
};

#endif
