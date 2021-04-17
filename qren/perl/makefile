######################################################################
# simple makefile to build zip for qren windows
######################################################################

# dependency specification

SRC_DIR = src
BUILD_DIR = build
STAGE_DIR = $(BUILD_DIR)/stage

REL_VERSION   = 7.5.1
REL_PHASE     = beta

# for getting exiftool
CURL_EXE      = c:/util/Linux/curl-win64-mingw/bin/curl.exe
GZIP_EXE      = c:/util/gnu/bin/gzip.exe
TAR_EXE       = c:/util/gnu/bin/tar.exe

EXIF_VER      = 12.24
EXIF_FILE     = Image-ExifTool-$(EXIF_VER)
EXIF_DOWNLOAD = https://exiftool.org/$(EXIF_FILE).tar.gz
EXIF_LIBS     = File Image

all: stage zip

stage: qren_src exiftool
	cp -p "readme.md" "$(STAGE_DIR)/qren"
	cp -p "history.txt" "$(STAGE_DIR)/qren"

######################################################################

# simple makefile rules that copies files to the correct folder
# location for easy install on target machine

qren_src:
	@echo "*** copying qren src ***"
	mkdir -p $(STAGE_DIR)/qren
	cp -p $(SRC_DIR)/* $(STAGE_DIR)/qren

exiftool:
	@echo "*** downloading ExifTool ***"
	mkdir -p $(BUILD_DIR)/exiftool
	$(CURL_EXE) $(EXIF_DOWNLOAD) -o $(BUILD_DIR)/exiftool/$(EXIF_FILE).tar.gz
	@echo "*** extracting ExifTool ***"
	$(GZIP_EXE) -d $(BUILD_DIR)/exiftool/$(EXIF_FILE).tar.gz
	$(TAR_EXE) xvf $(BUILD_DIR)/exiftool/$(EXIF_FILE).tar -C $(BUILD_DIR)/exiftool
	@echo "*** copying ExifTool libs ***"
	for f in $(EXIF_LIBS); do \
	  cp -pr "$(BUILD_DIR)/exiftool/$(EXIF_FILE)/lib/$$f" "$(STAGE_DIR)/qren"; \
        done

zip:
	@echo "*** producing zipfile ***"
	cd $(STAGE_DIR) && zip -9rX \
	  ../qren-v$(REL_VERSION)-$(REL_PHASE).zip .

clean:
	rm -rf $(BUILD_DIR)

######################################################################

# phony targets are unaffected by files with the same name
.PHONY : all clean qren_src exiftool zip
