######################################################################
# simple makefile for deltree
######################################################################

# dependency specification

MAIN_TARGET = deltree.exe
SRC_DIR = src
BUILD_ROOT = build

# directories separated by space
INCLUDE_DIRS = include
LIB_DIRS = lib

ifeq ("$(TARGET)","debug")
    BUILD_DIR = $(BUILD_ROOT)/debug
else
    BUILD_DIR = $(BUILD_ROOT)/release
endif

SRC := $(foreach sdir,$(SRC_DIR),$(wildcard $(sdir)/*.c))
OBJ := $(patsubst $(SRC_DIR)/%.c,$(BUILD_DIR)/%.o,$(SRC))
VPATH = $(SRC_DIR)

all: checkdirs $(BUILD_DIR)/$(MAIN_TARGET)

$(BUILD_DIR)/$(MAIN_TARGET): $(OBJ)

######################################################################

# compiler settings

CC = gcc

CC_OPTS = -D_UNICODE -DUNICODE

ifeq ("$(TARGET)","debug")
    CFLAGS   = -Wall -g $(addprefix -I,$(INCLUDE_DIRS)) $(CC_OPTS)
    LDFLAGS  = -municode
else
    CFLAGS   = -Wall -O6 $(addprefix -I,$(INCLUDE_DIRS))  $(CC_OPTS)
    LDFLAGS  = -s -municode -lshlwapi
endif

LOADLIBES = $(addprefix -L,$(LIB_DIRS))

######################################################################

# additional useful target settings

# create the build directory
checkdirs: $(BUILD_DIR)
$(BUILD_DIR):
	mkdir -p $@

# calls self with debug option set
debug:
	$(MAKE) TARGET=debug

clean:
	rm -rf $(BUILD_ROOT)

######################################################################

# phony targets are unaffected by files with the same name
.PHONY : all clean debug

# implicit rule for compiling .c to .o in BUILD_DIR
#
# this rule is needed because the .o is not in the the .c location,
# even though the action is exactly the same as the implicit default.
$(BUILD_DIR)/%.o: %.c
	$(CC) $(CFLAGS) $(CPPFLAGS) -c -o $@ $<

# implicit rule for compiling to .exe files on windows
#
# this rule is needed because the default rule doesn't handle .exe
# even though the action is exactly the same as implicit default
%.exe: %.o
	$(CC)  $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@
