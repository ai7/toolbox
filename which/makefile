# the locations to be updated for workstation

SOURCE   = Release
TARGET   = which.exe

TARGET_A = which.new

TARGET1 = c:\bin
TARGET2 = p:\ray
TARGET3 = c:\winnt\system32
TARGET4 = r:\public\raychi\which

# what needs to be updated
all: "$(TARGET1)\$(TARGET)" \
     "$(TARGET2)\$(TARGET)" \
     "$(TARGET3)\$(TARGET)" \
     "$(TARGET4)\$(TARGET)" \
     "$(TARGET4)\$(TARGET_A)"

"$(TARGET1)\$(TARGET)": "$(SOURCE)\$(TARGET)"
        copy "$(SOURCE)\$(TARGET)" "$(TARGET1)"

"$(TARGET2)\$(TARGET)": "$(SOURCE)\$(TARGET)"
        copy "$(SOURCE)\$(TARGET)" "$(TARGET2)"

"$(TARGET3)\$(TARGET)": "$(SOURCE)\$(TARGET)"
        copy "$(SOURCE)\$(TARGET)" "$(TARGET3)"

"$(TARGET4)\$(TARGET)": "$(SOURCE)\$(TARGET)"
        copy "$(SOURCE)\$(TARGET)" "$(TARGET4)"

"$(TARGET4)\$(TARGET_A)": "$(TARGET_A)"
        copy "$(TARGET_A)" "$(TARGET4)"
