/************************************************************************
	LmpUtil, a utility I wrote to handle Doom / Doom II / Heretic
	recorded games. This is the first program I release into the public
	Raymond Chi, chiry@cory.EECS.Berkeley.EDU
*************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <dos.h>
#include <dir.h>
#include <sys\stat.h>
#include <utime.h>

#include "lmputil.h"

#define NAME_SIZE 256
#define FREQ 35.003
#define GOTOCHAR 0xAF
#define LISTCHAR 0xFE
#define PSPECHAR 0x10

#define EXIT(x) if (!multi) { exit(x); } else { return x; }
#define WITHIN(v, l, u) ((int) v >= (int) l && (int) v <= (int) u)
#define NEED(x) if (check_free(x)) { printf("Not enough disk space, %ld byte(s) needed!\n", x); exit(3); }

/*
	the convention for error code returned to the operating system is
	the following:
	1 : an error was detected in main()
	2 : an error was detected while examining the LMP, mainly,
		init_info(), check(), check12()
	3 : other errors caused by run time conditions, like from
		convert(), cut_it(), etc
*/

/*	These are the global variables used through out the program	*/

int header_size = 13,	/* size of the LMP header */
	tic_size = 4,	/* how many bytes each game tick take */
	act_player,		/* number of active players in the LMP */
	option,			/* 1 if -viewer is used passed */
	tic_bytes,		/* size of each game tick, = tic_size * act_player */
	multi,          /* in multi mode, error returns, not (exit) */
	display_only,	/* set if is in displaying only mode */
	missing,		/* if incorrect file size, missing x byte */
	heretic,        /* set if heretic lmp is used */
	second;			/* set if -sec specified */

long filesize,		/* size of the input file */
	 need;			/* how many bytes needed for output */

double version,		/* req'd info for -ver parameter */
	   tick;		/* how many game tics there are in the LMP */

unsigned char header[13];	/* contains the lmp file header */

char in_lmp[NAME_SIZE],		/* source lmp file */
	 out_lmp[NAME_SIZE],	/* target lmp file */
	 lmp_length[9],	/* a char rep of the lmp's duration, like 02:23:45 */
	 active[26];	/* a string of the active player */

/*	these 2 are used to get file size and retain modification time */
struct stat statbuf;
struct utimbuf times;

/*	these are the information display strings stored in memory
	it is : array[] of pointers to char	*/

char

 * skill[2][5] = {{"I'm too young to die",
				   "Hey, not too rough",
				   "Hurt me plenty",
				   "Ultra-Violence",
				   "Nightmare!"},
				  {"Thou Needeth A Wet-Nurse",
				   "Yellowbellies-R-Us",
				   "Bringest Them Oneth",
				   "Thou Art Smite-Meister",
				   "Black Plague On Thee!"}},
	  * mode[3] = {"Cooperative", "Original DeathMatch", "DeathMatch 2.0"},
	* choice[2] = {"Yes", "No"},
	* player[4] = {"Green", "Indigo", "Brown", "Red"},
*episode[2][5] = {{"Hell on Earth", "Knee-Deep in the Dead",
				   "The Shores of Hell", "Inferno", "Thy Flesh Consumed"},
				  {"Cities of the Damned", "Hell's Maw", "The Domes of D'Sparil",
				   "4th Episode of Heretic", "5th Episode of Heretic"}},
   * lev[4][9] = {{"Hangar", "Nuclear Plant", "Toxin Refinery",
				   "Command Control", "Phobos Lab", "Central Processing",
				   "Computer Station", "Phobos Anomaly", "Military Base"},
				  {"Deimos Anomaly", "Containment Area", "Refinery",
				   "Deimos Lab", "Command Center", "Halls of the Damned",
				   "Spawning Vats", "Tower of Babel", "Fortress of Mystery"},
				  {"Hell Keep", "Slough of Despair", "Pandemonium",
				   "House of Pain", "Unholy Cathedral", "Mt. Erebus",
				   "Limbo", "Dis", "Warrens"},
				  {"Hell Beneath", "Perfect Hatred", "Sever The Wicked",
				   "Unruly Evil", "They Will Repent", "Against Thee Wickedly",
				   "And Hell Followed", "Unto The Cruel", "Fear"}},
	 * lev2[32] = {"Entryway", "Underhalls", "The Gantlet",
				   "The Focus", "The Waste Tunnels", "The Crusher",
				   "Dead Simple", "Tricks and Trap", "The Pit",
				   "Refueling Base", "'O' of Destruction", "The Factory",
				   "Downtown", "The Inmost Dens", "Industrial Zone",
				   "Suburbs", "Tenements", "The Courtyard",
				   "The Citadel", "Gotcha!", "Nirvana",
				   "The Catacombs", "Barrels O' Fun", "The Chasm",
				   "Bloodfalls", "The Abandoned Mines", "Monster Condo",
				   "The Spirit World", "The Living End", "Icon of Sin",
				   "Wolfenstein", "Grosse"},
  * lev3[5][9] = {{"The Docks", "The Dungeons", "The Gatehouse",
				   "The Guard Tower", "The Citadel", "The Cathedral",
				   "The Crypts", "Hell's Maw", "The Graveyard"},
				  {"The Crater", "The Lava Pits", "The River of Fire",
				   "The Ice Grotto", "The Catacombs", "The Labyrinth",
				   "The Great Hall", "The Portals of Chaos", "The Glacier"},
				  {"The Storehouse", "The Cesspool", "The Confluence",
				   "The Azure Fortress", "The Ophidian Lair", "The Halls of Fear",
				   "The Chasm", "D'Sparil's Keep", "The Aquifer"},
				  {"Catafalque", "Blockhouse", "Ambulatory",
				   "Sepulcher", "Great Stair", "Halls of The Apostate",
				   "Ramparts of Perdition", "Shattered Bridge", "Mausoleum"},
				  {"Ochre Cliffs", "Rapids", "Quay",
				   "Courtyard", "Hydratyr", "Colonnade",
				   "Foetid Manse", "Field of Judgement", "Skein of D'Sparil"}};

/*	main function, parameter check and load file	*/
int main(int argc, char *argv[])
{
	FILE * ifp = NULL;
	int argCount = 0, done, first_time = 1;
	char lower_file[NAME_SIZE];
	struct find_t ffblk;
	if (argc == 1) {	/*	if no argument is given, display help screen */
		display_help();
		exit(0);
	}	/*	now let's process the parameter, guided fron nachos	*/
	for (argc--, argv++; argc > 0; argc -= argCount, argv += argCount) {
		argCount = 1;
		if (argv[0][0] == '/' || argv[0][0] == '-') {	/*	if parameters */
			if (!strcmp(*argv + 1, "?") || !strcmp(*argv + 1, "h")
				|| !strcmp(*argv + 1, "help")) {
			display_help();	/* will not cause a seg fault when param */
			exit(0);		/* is - because *argv + 1 is the null char */
			}
			else if (!strcmp(*argv + 1, "viewer")) {
				option = 10;	/* change recording player requested */
				if (argc > 1 && strlen(*(argv + 1)) == 1) {
					option = atoi(*(argv + 1));
					if (!option)	/* if not a number */
						option = 10;	/* set back to xxx */
					else if (!WITHIN(option, 1, 4)) {
						printf("Invalid viewpoint - %s.\n", *(argv + 1));
						exit(1);
					}
					else	/* all succcess, so take the parm */
						argCount = 2;
				}
			}
			else if (!strcmp(*argv + 1, "heretic")) {
				heretic = 1;
			}
			else if (!strcmp(*argv + 1, "sec")) {
				second = 1;
			}
			else if (!strcmp(*argv + 1, "ver")) {
				if (argc < 2) {
					printf("LMP version required for %s.\n", *argv);
					exit(1);
				}
				version = (atof(*(argv + 1)) - 1) * 10;
				if (!WITHIN(version, 4, 9)) {
					printf("Invalid LMP version - \"%s\"\n", *(argv + 1));
					exit(1);
				}
				argCount = 2;
			}
			else if (!strcmp(*argv + 1, "convert")) {
				if (argc < 3) {
					printf("In.LMP and Out.LMP required for %s.\n", *argv);
					exit(1);
				}	/* must process before compare */
				process_ext(*(argv + 1), in_lmp);
				process_ext(*(argv + 2), out_lmp);
				if (!strcmp(in_lmp, out_lmp)) {
					printf("In.LMP and Out.LMP must be different files.\n");
					exit(1);
				}
				if (argc > 3) {		/*	then get the version number	*/
					version = (atof(*(argv + 3)) - 1) * 10;
					if (!WITHIN(version, 4, 9)) {
						printf("Invalid target version - \"%s\"\n", *(argv + 3));
						exit(1);
					}
				}
				convert(in_lmp, out_lmp);	/*	convert it	*/
				return 0;
			}
			else if (!strcmp(*argv + 1, "cut")) {
				if (argc < 5) {
					printf("%d more parameter(s) required for %s.\n", 5 - argc, *argv);
					exit(1);
				}
				process_ext(*(argv + 3), in_lmp);
				process_ext(*(argv + 4), out_lmp);
				if (!strcmp(in_lmp, out_lmp)) {
					printf("In.LMP and Out.LMP must be different files.\n");
					exit(1);
				}
				if (second)
					cut_it(atof(*(argv + 1)) * 35 - 34, atof(*(argv + 2)) * 35,
						   in_lmp, out_lmp);
				else
					cut_it(atof(*(argv + 1)), atof(*(argv + 2)),
						   in_lmp, out_lmp);
				return 0;
			}
			else if (!strcmp(*argv + 1, "chop")) {
				if (argc < 4) {
					printf("%d more parameter(s) required for %s.\n", 4 - argc, *argv);
					exit(1);
				}
				process_ext(*(argv + 2), in_lmp);
				process_ext(*(argv + 3), out_lmp);
				if (!strcmp(in_lmp, out_lmp)) {
					printf("In.LMP and Out.LMP must be different files.\n");
					exit(1);
				}
				if (second)
					chop_it(atof(*(argv + 1)) * 35, in_lmp, out_lmp);
				else
					chop_it(atof(*(argv + 1)), in_lmp, out_lmp);
				return 0;
			}
			else if (!strcmp(*argv + 1, "wait")) {
				if (argc < 4) {
					printf("%d more parameter(s) required for %s.\n", 4 - argc, *argv);
					exit(1);
				}
				process_ext(*(argv + 2), in_lmp);
				process_ext(*(argv + 3), out_lmp);
				if (!strcmp(in_lmp, out_lmp)) {
					printf("In.LMP and Out.LMP must be different files.\n");
					exit(1);
				}
				if (second)
					wait_it(atof(*(argv + 1)) * 35, in_lmp, out_lmp);
				else
					wait_it(atof(*(argv + 1)), in_lmp, out_lmp);
				return 0;
			}
			else if (!strcmp(*argv + 1, "rp")) {
				if (argc < 3) {
					printf("%d more parameter(s) required for %s.\n", 3 - argc, *argv);
					exit(1);
				}
				process_ext(*(argv + 1), in_lmp);
				process_ext(*(argv + 2), out_lmp);
				if (!strcmp(in_lmp, out_lmp)) {
					printf("In.LMP and Out.LMP must be different files.\n");
					exit(1);
				}
				remove_pause(in_lmp, out_lmp);
				return 0;
			}
			else {
				printf("Invalid parameter - \"%s\"\n", *argv);
				exit(1);	/*	if already have a file	*/
			}
		}
		else if (in_lmp[0] == 0)		/*	if this is first time	*/
			process_ext(*argv, in_lmp);
		else {
			printf("LMP file already specified - \"%s\"\n", in_lmp);
			exit(1);	/*	if already have a file	*/
		}
	}
	if (in_lmp[0] == 0 ) {
		printf("You must specify a LMP file.\n");
		exit(1);
	}
	if (option || version != 0.0) {
		multi = 1;		/*	indicating it's processing multiple files	*/
		wild_change();
		return 0;
	}
	done = _dos_findfirst(in_lmp, _A_NORMAL, &ffblk);
	if (done) {				/*	if cannot find anything	*/
		printf("File not found - \"%s\"\n", in_lmp);
		exit(1);
	}
	multi = 1;		/*	indicating it's processing multiple files	*/
	display_only = 1;
	while (!done) {			/* while there's file to process */
		ifp = fopen(ffblk.name, "rb");	/*	source file for reading	*/
		all_lower(ffblk.name, lower_file);
		if (ifp != NULL) {
			if (first_time)
				first_time = 0;
			else
				printf("\n");
			if (!init_info(ifp, ffblk.name)) {
				if (header_size == 13)	/*	if it is a valid lmp */
					display(lower_file);
				else				/*	it's a 1.2 LMP	*/
					display12(lower_file);
			}
			else
				printf("Not a valid LMP file - \"%s\"\n", lower_file);
			fclose(ifp);		/*	close file if get here.	*/
		}
		else {
			printf("Cannot open LMP file - \"%s\"\n", lower_file);
		}
		done = _dos_findnext(&ffblk);
	}
	return 0;
}

/*	help displayed when /? parameter is passed to program	*/
void display_help(void)
{
	printf("LmpUtil 2.30 01-12-96\n"
		   "(c) Copyright 1996 Raymond Chi (chiry@cory.EECS.Berkeley.EDU)\n\n"
		   "Usage : LmpUtil <File(s)[.LMP]> [options]\n"
//		   "Options can start with \'-\' or \'/\'.\n"
		   "-ver <version>\n"
		   "  Change LMP file version. Version can be 1.4 - 1.9\n"
		   "-viewer [player #]\n"
		   "  Cycle viewpoint, or, 1=Green, 2=Indigo, 3=Brown, 4=Red\n"
		   "-convert <In[.LMP]> <Out[.LMP]> [version]\n"
		   "  Converts 1.0 - 1.2 LMP to 1.4 - 1.9 LMP format\n"
		   "-heretic\n"
		   "  Must be used with Heretic LMP for -chop or -wait\n"
		   "-sec\n"
		   "  -cut, -chop & -wait's <tics> will be treated as <seconds>\n"
		   "-cut <start tic> <end tic> <In[.LMP]> <Out[.LMP]>\n"
		   "  Remove a section of tics, 35 gametics = 1 second\n"
		   "-chop <tics> <In[.LMP]> <Out[.LMP]>\n"
		   "  Remove some tics at the end of LMP\n"
		   "-wait <tics> <In[.LMP]> <Out[.LMP]>\n"
		   "  Append some idle tics at the end of LMP\n"
		   "-rp <In[.LMP]> <Out[.LMP]>\n"
		   "  Remove all pauses from the LMP\n");
}

/*	processes the file specification, if it does not contains a . then
	add the extension .lmp to it
	it searches the file specification backwards	*/
void process_ext(const char * source, char * target)
{
	int x = strlen(source);
	while (--x >= 0) {
		if (source[x] == '.') {	/* if file has extension */
			strncpy(target, source, NAME_SIZE - 1);
			return;
		}
	}	/* file does not have extension, so add it */
	strncpy(target, source, NAME_SIZE - 5);
	strcat(target, ".lmp");
	return;
}

/*	display information from header[], the LMP header	*/
void display(const char * filename)
{
	tick_to_time(tick, lmp_length);		/* calculate how long	*/
	printf("LMP file      : %s\n", filename);
	printf("Version       : 1.%d\n", header[0] - 100);
	if (header[3] > 9) {	/*	map > 9, so it's doom 2's lmp	*/
		printf("Skill Level   : %d, %s\n", header[1] + 1, skill[0][header[1]]);
		printf("Episode       : %d, %s\n", header[2], episode[0][0]);
		printf("Map           : %d, %s\n", header[3], lev2[header[3] - 1]);
	}
	else {	/* it's either doom/heretic */
		printf("Skill Level   : %d, %s\n", header[1] + 1, skill[heretic][header[1]]);
		if (heretic) {	/* if heretic, then display it */
			printf("Episode       : %d, %s\n", header[2], episode[1][header[2]]);
			printf("Map           : %d, %s\n", header[3], lev3[header[2] - 1][header[3] - 1]);
		}
		else if (header[2] > 1 ) {	/*	episode > 1, so it's doom's lmp	*/
			printf("Episode       : %d, %s\n", header[2], episode[0][header[2]]);
			printf("Map           : %d, %s\n", header[3], lev[header[2] - 1][header[3] - 1]);
		}
		else {						/*	can't tell, so display both	*/
			printf("Episode       : 1, %s / %s\n", episode[0][0], episode[0][1]);
			printf("Map           : %d, %s / %s\n", header[3], lev2[header[3] - 1], lev[0][header[3] - 1]);
		}
	}
	if (header[4] == 0 && act_player == 1)	/*	if single and coop	*/
		printf("Play Mode     : Single\n");
	else
		printf("Play Mode     : %s\n", mode[header[4]]);
	printf("-respawn      : %s\n", choice[!(header[5])]);
	printf("-fast         : %s\n", choice[!(header[6])]);
	printf("-nomonsters   : %s\n", choice[!(header[7])]);
	printf("Recorded by   : %s\n", player[header[8]]);
	printf("Active Player : %s\n", active);
	if (missing == 0)
		printf("Game Tics     : %.0f\n", tick);
	else
		printf("Game Tics     : %.2f <- file missing %d byte(s).\n", tick, missing);
	printf("Duration      : %s\n", lmp_length);
}

/*	process, and display information from header[], the LMP header
	this is used for display LMP file version prior to 1.4	*/
void display12(const char * filename)
{
	tick_to_time(tick, lmp_length);		/* calculate how long	*/
	printf("LMP file      : %s\n", filename);
	printf("Version       :\n");
	printf("Skill Level   : %d, %s\n", header[0] + 1, skill[heretic][header[0]]);
	printf("Episode       : %d, %s\n", header[1], episode[heretic][header[1]]);
	if (heretic)
		printf("Map           : %d, %s\n", header[2], lev3[header[1] - 1][header[2] - 1]);
	else
		printf("Map           : %d, %s\n", header[2], lev[header[1] - 1][header[2] - 1]);
	printf("Play Mode     :\n");
	printf("-respawn      :\n");
	printf("-fast         :\n");
	printf("-nomonsters   :\n");
	printf("Recorded by   :\n");
	printf("Active Player : %s\n", active);
	if (missing == 0)
		printf("Game Tics     : %.0f\n", tick);
	else
		printf("Game Tics     : %.2f <- file missing %d byte(s).\n", tick, missing);
	printf("Duration      : %s\n", lmp_length);
}

/*	converts the string to lower case	*/
void all_lower(const char * source, char * target)
{
	int x = strlen(source), y;
	for (y = 0; y < NAME_SIZE && y <= x; y++)
		target[y] = tolower(source[y]);
	target[y] = '\0';
}

/*	convert older lmp file (1.2 format) to newer format	*/
void convert(const char * source, const char * target)
{
	FILE * ifp = NULL, * ofp = NULL;
	int x = 0;
	if (version == 0)
		version = 9;			/*	default version is 1.9	*/
	ifp = fopen(source, "rb");	/*	source file for reading	*/
	if (ifp == NULL) {
		printf("Cannot open In.LMP - \"%s\"\n", source);
		exit(3);
	}
	init_info(ifp, source);
	if (header_size == 13) {		/*	if it's the newer lmp format	*/
		printf("LMP is already the newer format - \"%s\"\n", source);
		exit(3);
	}
	need = filesize + 6;	/* it's the old 7 byte header to the 13 byte */
	NEED(need);
	ofp = fopen(target, "wb");	/*	target file, must after all ifp error check	*/
	if (ofp == NULL) {
		printf("Cannot create Out.LMP - \"%s\"\n", target);
		exit(3);
	}
	printf("Converting \"%s\" %c \"%s\" v1.%d ", source, GOTOCHAR, target, (int)version);
	putc(100 + version, ofp);	/*	version byte, default is 1.9	*/
	for (x = 0; x < 3; x++)
		putc(header[x], ofp);		/*	skill, episode, map	*/
	for (x = 0; x < 5; x++)
		putc(0, ofp);			/*	coop, -resp, -fast, -nomon, green	*/
	for (x = 3; x < 7; x++)     /*	the rest 4 player byte	*/
		putc(header[x], ofp);   /*	only green should be active	*/
	printf(".");
	fseek(ifp, header_size, SEEK_SET);	/*	goto the recording player byte	*/
	copy_tics(tick, ifp, ofp);	/*	now, copy all the game tics */
	printf(".");
	putc(0x80, ofp);			/*	puts the quit byte, hex 80	*/
	printf(".");
	fclose(ifp);
	fclose(ofp);
	if (utime((char *)target, &times) != 0) {
		perror("Unable to set time of destination file");
		exit(3);
	}
	printf(". [done]\n");
}

/*	reads the preliminary information of the LMP and fills some
	of the global variables	*/
int init_info(FILE * ifp, const char * file_name)
{
	int x = 0, c = 0, start = 9, status = 0, first_time = 1;
	/*	initialize all global variables to default again, for multi	*/
	header_size = 13, act_player = 0, missing = 0, active[0] = '\0';
	while (x < header_size && (c = getc(ifp)) != EOF) {
		if (x == 0 && WITHIN(c, 0, 4)) {
			header_size = 7;	/*	if first byte is a skill level, then 1.2	*/
			start = 3;
		}
		header[x++] = c;
	}
	if (x < header_size) {
		printf("File must have at least %d bytes - \"%s\"\n", header_size, file_name);
		EXIT(2);
	}
	if (header_size == 13) {
		status = check();
		if (status)
			return 2;
	}
	else {
		status = check12();
		if (status)
			return 2;
	}
	if (fstat(fileno(ifp), &statbuf) != 0) {
		perror("Unable to get file stat");
		EXIT(2);
	}
	filesize = statbuf.st_size;
	times.modtime = times.actime = statbuf.st_mtime; /* save file d & t */
	for (x = 0; x < 4; x++) {	/*	get the active player list	*/
		if (header[start + x] == 1) {
			act_player++;
			if (display_only) {	/* only if necessary */
				if (first_time)
					first_time = 0;
				else
					strcat(active, ", ");
				strcat(active, player[x]);
			}
		}
	}
	if (heretic && !(header[3] > 9))	/* if not a doom2 lmp for sure */
		tic_size = 6;					/*	different with heretic	*/
	tic_bytes = tic_size * act_player;	/*	how long a tick is	*/
	tick = (double) (filesize - header_size - 1) / tic_bytes;
	x = (int) ((filesize - header_size - 1) % tic_bytes);
	if (x != 0)
		missing = tic_bytes - x;
	return 0;
}

/*	check if the header contains valid information	*/
int check(void)
{
	int x;
	if (!WITHIN(header[0], 104, 109)) {	/*	support version 1.4 to 1.9	*/
		printf("Invalid LMP version number, offset 0 - \"%d\"\n", header[0]);
		EXIT(2);
	}
	if (!WITHIN(header[1], 0, 4)) {		/*	support skill 0 to 4	*/
		printf("Invalid skill level, offset 1 - \"%d\"\n", header[1]);
		EXIT(2);
	}
	if (!WITHIN(header[2], 1, 4)) {		/*	support episode 1 to 3	*/
		printf("Invalid episode, offset 2 - \"%d\"\n", header[2]);
		EXIT(2);
	}
	if (header[2] < 2) {	/*	if for episode 1, then from 1 to 32	*/
		if (!WITHIN(header[3], 1, 32)) {		/*	support map 1 to 32	*/
			printf("Invalid map for episode %d, offset 3 - \"%d\"\n", header[2], header[3]);
			EXIT(2);
		}
	}
	else {	/*	it's a doom1 map	*/
		if (!WITHIN(header[3], 1, 9)) {		/*	support map 1 to 9	*/
			printf("Invalid map for episode %d, offset 3 - \"%d\"\n", header[2], header[3]);
			EXIT(2);
		}
	}
	if (!WITHIN(header[4], 0, 2)) {		/*	support play mode 0 to 2	*/
		printf("Invalid play mode, offset 4 - \"%d\"\n", header[4]);
		EXIT(2);
	}
	if (!WITHIN(header[8], 0, 3)) { 	/*	support player 0 to 3	*/
		printf("Invalid recording player, offset 8 - \"%d\"\n", header[8]);
		EXIT(2);
	}
	for (x = 9; x < 13; x++) {
		if (!WITHIN(header[x], 0, 1)) { 	/*	support no or yes	*/
			printf("Invalid %s player indicator, offset %d - \"%d\"\n",
				   player[x - 9], x, header[x]);
			EXIT(2);
		}
	}
	if (header[9] == 0 && header[10] == 0 && header[11] == 0 && header[12] == 0) {
		printf("No active player found! Offset 9, 10, 11, 12.\n");
		EXIT(2);
	}
	if (header[header[8] + 9] == 0) {
		printf("Recording player not active, offset 8 - \"%d\"\n", header[8]);
		EXIT(2);
	}
	return 0;
}

/*	check for lmp file for version up to 1.2	*/
int check12(void)
{
	int x;
	if (!WITHIN(header[0], 0, 4)) {	/*	support skill 0 to 4	*/
		printf("Invalid skill level, offset 0 - \"%d\"\n", header[0]);
		EXIT(2);
	}
	if (!WITHIN(header[1], 1, 3)) {	/*	support episode 1 to 3	*/
		printf("Invalid episode, offset 1 - \"%d\"\n", header[1]);
		EXIT(2);
	}
	if (!WITHIN(header[2], 1, 9)) {	/*	support map 1 to 9	*/
		printf("Invalid map, offset 2 - \"%d\"\n", header[2]);
		EXIT(2);
	}
	for (x = 3; x < 7; x++) {
		if (!WITHIN(header[x], 0, 1)) { 	/*	support no or yes	*/
			printf("Invalid %s player indicator, offset %d - \"%d\"\n",
				   player[x - 3], x, header[x]);
			EXIT(2);
		}
	}
	if (header[3] == 0 && header[4] == 0 && header[5] == 0 && header[6] == 0) {
		printf("No active player found! Offset 3, 4, 5, 6.\n");
		EXIT(2);
	}
	return 0;
}

/*	converts a game tick to a time string
	tick needs to be double because it may be large	*/
void tick_to_time(double tick, char * time_string)
{
	char tmp[3] = {0};			/*	string holder for digits < 60	*/
	int x, time_digit[3];
	long sec = tick / FREQ;				/* 	must be a long for large */
	time_string[0] = '\0';				/*	make sure a empty st	*/
	if (sec != tick / FREQ)				/*	if has fraction left	*/
		sec++;							/*	so it rounds up, seconds	*/
	if (sec > 356400l) {
		printf("Cannot process more than 99 hours - %ld seconds = %.2f hours\n", sec, sec / 3600.0);
		exit(3);
	}
	time_digit[0] = (int) (sec / 3600);	/* 	how many hours, round down	*/
	sec = sec % 3600;					/*  remainder seconds	*/
	time_digit[1] = (int) (sec / 60);   /*	minutes, round down	*/
	time_digit[2] = (int) (sec % 60);   /*	remaining seconds	*/
	for (x = 0; x < 3; x++) {
		if (x)
			strcat(time_string, ":");
		if (time_digit[x] < 10)
			strcat(time_string, "0");
		itoa(time_digit[x], tmp, 10);
		strcat(time_string, tmp);
	}
}

/*	remove the section of lmp and write output to target	*/
void cut_it(double start_tick, double end_tick, const char * source, const char * target)
{
	FILE * ifp = NULL, * ofp = NULL;
	char tic_length1[9] = {0}, tic_length2[9] = {0};
	ifp = fopen(source, "rb");	/*	source file for reading only	*/
	if (ifp == NULL) {
		printf("Cannot open In.LMP - \"%s\"\n", source);
		exit(3);
	}
	init_info(ifp, source);
	if (start_tick < 1) {
		printf("Start Tics must be greater than 0 - %.2f.\n", start_tick);
		exit(3);
	}
	if (end_tick < 1) {
		printf("End Tics must be greater than 0 - %.2f.\n", end_tick);
		exit(3);
	}
	if (end_tick > tick) {
		printf("End Tics cannot be greater than %.2f - %.2f.\n", tick, end_tick);
		exit(3);
	}
	if (start_tick > end_tick) {
		printf("Start Tics cannot be greater than %.2f - %.2f.\n", tick, start_tick);
		exit(3);
	}
	need = filesize - (end_tick - start_tick + 1) * tic_bytes;
	NEED(need);
	fseek(ifp, header_size, SEEK_SET);	/*	goto tick byte	*/
	ofp = fopen(target, "wb");	/*	target file, must after all ifp error check	*/
	if (ofp == NULL) {
		printf("Cannot create Out.LMP - \"%s\"\n", target);
		exit(3);
	}
	tick_to_time(start_tick, tic_length1);
	tick_to_time(end_tick, tic_length2);
	printf("%c \"%s\" %c \"%s\" : %s to %s ",
			LISTCHAR, source, GOTOCHAR, target, tic_length1, tic_length2);
	fwrite(header, sizeof(header[0]), header_size, ofp);
	printf(".");
	copy_tics(start_tick - 1, ifp, ofp);	/*	copy up to...	*/
	printf(".");
	fseek(ifp, tic_bytes * (end_tick - start_tick + 1), SEEK_CUR);
	printf(".");
	copy_tics(tick - end_tick, ifp, ofp);	/*	copy til end of file	*/
	printf(".");
	putc(0x80, ofp);	/*	puts the quit byte, hex 80	*/
	printf(".");
	fclose(ifp);
	fclose(ofp);
	if (utime((char *)target, &times) != 0) {
		perror("Unable to set time of destination file");
		exit(3);
	}
	printf(". [done]\n");
}

/*	copies this many tics, assuming that the file pointers are
	already right position and files are valid range
	this uses fread to copy a while gametic at a time, depends
	on how many players and how big a tick is, this can mean 24 bytes
	of data each read	*/
void copy_tics(double tics, FILE * ifp, FILE * ofp)
{
	unsigned char holder[4 * 6] = {0};	/*	defaults to the biggest size	*/
	int buffer_size = 0, write_status = 0;
	if (tics <= 0)	/* if nothing to copy, then return	*/
		return;
	while (tics-- > 0) {
		buffer_size = fread(holder, sizeof(holder[0]), tic_bytes, ifp);
		write_status = fwrite(holder, sizeof(holder[0]), buffer_size, ofp);
		if (buffer_size != write_status) {
			printf("\n\nError: copy_tics() fwrite failed, %d out of %d byte(s) copied.\n", write_status, buffer_size);
			exit(3);
		}
	}
	if (buffer_size != 0) {	/* if last byte read is 'quit', back up */
		if (holder[buffer_size - 1] == 0x80)
			fseek(ofp, -1, SEEK_CUR);	/*	backup 1 byte	*/
	}
}

/*
	search throught the directory and process all files matching
	the in.lmp file specification. Skip any that are invalid lmpfiles
*/
void wild_change(void)
{
	struct find_t ffblk;
	int done, status, count = 0, bad = 0, changed = 0;
	char lower_file[NAME_SIZE];
	FILE * ifp = NULL;
	done = _dos_findfirst(in_lmp, _A_NORMAL, &ffblk);
	if (done) {				/*	if cannot find anything	*/
		printf("File not found - \"%s\"\n", in_lmp);
		exit(3);
	}
	while (!done) {			/* while there's file to process */
		ifp = fopen(ffblk.name, "rb+");	/* open it in binary update mode */
		all_lower(ffblk.name, lower_file);
		printf("%c %s : ", LISTCHAR, lower_file);
		if (ifp != NULL) {		/* if file open is successful */
			status = init_info(ifp, ffblk.name);
			if (!status && header_size == 13) {	/*	if it is a valid lmp */
				changed = ver_viewer(ifp);
				printf("[done]\n");
				count++;
			}	/* no need to put a \n since if error mess does it */
			else {
				if (header_size != 13 && !status)
					printf("Old LMP format, use /convert.\n");
				bad++;
			}
			fclose(ifp);
			if (changed && utime(ffblk.name, &times) != 0) {
				perror("Unable to set time of destination file");
			}
			changed = 0;	/*	reset it back to 0 again */
		}
		else {
			bad++;
			printf("Cannot open LMP file - \"%s\"\n", lower_file);
		}
		done = _dos_findnext(&ffblk);
	}
	printf("     %d file(s) processed, %d file(s) skipped.\n", count, bad);
}

/*
	update the ver & player byte if necessary
	assuming the header is already initilized, and
	at least one of the parameter is specified.
*/
int ver_viewer(FILE * ifp)
{
	int x = 0, who;	/*	used to see if the | need output or not	*/
	if (version != 0 && header[0] - 100 != version) {
		printf("1.%d %c ", header[0] - 100, GOTOCHAR);
		change_ver(ifp, version);
		x = 1;	/*	indicates version changed	*/
	}
	if (option) {
		if (x)	/*	if version changed, put that | char out	*/
			printf(" %c ", 0xB3);
		if (option == 10) {		/* if cycle, then set next available */
			who = (header[8] + 1) % 4;
			while (!header[who + 9])	/* guaranteed to success */
				who = (who + 1) % 4;
		}
		else				/* else setdirect player */
			who = option - 1;		/* it's from 0 - 3 */
		if (who == header[8]) {		/* if same person */
			if (x)	/* if there's a extra white space, delete it */
				printf("\b");
			goto jump_out;	/* get the hell out */
		}
		if (header[who + 9] == 0) {
			printf("Viewpoint not active - %d ", option);
			return x;
		}
		printf("%s %c ", player[header[8]], GOTOCHAR);
		record_player(ifp, who);
		x = 1;
	}
  jump_out:
	if (x)
		printf(" ");
	return x;	/*	indicating whether file is modified or not */
}

/*	change the recording player byte in the lmp to indicate the next
	available player	*/
void record_player(FILE * ofp, int x)
{
	fseek(ofp, 8L, SEEK_SET);	/*	goto the recording player byte	*/
	putc(x, ofp);				/*	update the file	*/
	printf("%s", player[x]);
}

/*	change the version byte in the lmp to 10x, where
	it indicates version 1.x	*/
void change_ver(FILE * ofp, int x)
{
	fseek(ofp, 0L, SEEK_SET);	/*	go to beginning again.	*/
	putc(x + 100, ofp);			/*	update the file	*/
	printf("1.%d", x);
}

/*	remove some tics from the 'end of file' and write output to target	*/
void chop_it(double tics, const char * source, const char * target)
{
	FILE * ifp = NULL, * ofp = NULL;
	char tic_length1[9] = {0}, tic_length2[9] = {0};
	ifp = fopen(source, "rb");	/*	source file for reading only	*/
	if (ifp == NULL) {
		printf("Cannot open In.LMP - \"%s\"\n", source);
		exit(3);
	}
	init_info(ifp, source);
	if (tics < 0) {
		printf("Tics must be greater than 0 - %.2f.\n", tics);
		exit(3);
	}
	if (tics > tick) {
		printf("Tics cannot be greater than %.2f - %.2f.\n", tick, tics);
		exit(3);
	}
	need = filesize - tics * tic_bytes;	/* how many, if all complete tics */
	if (missing)	/* if missing, then 'missing' are not chopped, so add */
		need += missing;
	NEED(need);
	fseek(ifp, header_size, SEEK_SET);	/*	goto tick byte	*/
	ofp = fopen(target, "wb");	/*	target file, must after all ifp error check	*/
	if (ofp == NULL) {
		printf("Cannot create Out.LMP - \"%s\"\n", target);
		exit(3);
	}
	tick_to_time(tick - tics, tic_length1);
	tick_to_time(tick, tic_length2);
	printf("%c \"%s\" %c \"%s\" : %s to %s ",
			LISTCHAR, source, GOTOCHAR, target, tic_length1, tic_length2);
	fwrite(header, sizeof(header[0]), header_size, ofp);
	printf(".");
	copy_tics(tick - tics, ifp, ofp);	/*	copy up to...	*/
	printf(".");
	putc(0x80, ofp);	/*	puts the quit byte, hex 80	*/
	printf(".");
	fclose(ifp);
	fclose(ofp);
	if (utime((char *)target, &times) != 0) {
		perror("Unable to set time of destination file");
		exit(3);
	}
	printf(". [done]\n");
}

/*	add some waiting tics at the end of the lmp, similar to cut_it	*/
void wait_it(double how_long, const char * source, const char * target)
{
	FILE * ifp = NULL, * ofp = NULL;
	char tic_length[9] = {0};
	ifp = fopen(source, "rb");	/*	source file for reading only	*/
	if (ifp == NULL) {
		printf("Cannot open In.LMP - \"%s\"\n", source);
		exit(3);
	}
	init_info(ifp, source);
	if (how_long < 1) {
		printf("Tics must be greater than 0 - %.2f.\n", how_long);
		exit(3);
	}
	else if (how_long > 2147483647l) {
		printf("Tics must be less than 2,147,483,647 - %.2lf.\n", how_long);
		exit(3);
	}
	need = filesize + how_long * tic_bytes;	/* how many, if all complete */
	if (missing)	/* if missing, then the last gametics is counted extra */
		need -= tic_bytes - missing;	/* minus last gametic */
	NEED(need);
	fseek(ifp, header_size, SEEK_SET);	/*	goto tick byte	*/
	ofp = fopen(target, "wb");	/*	target file, must after all ifp error check	*/
	if (ofp == NULL) {
		printf("Cannot create Out.LMP - \"%s\"\n", target);
		exit(3);
	}
	tick_to_time(how_long, tic_length);
	printf("%c \"%s\" %c \"%s\" : adding %s ",
			LISTCHAR, source, GOTOCHAR, target, tic_length);
	fwrite(header, sizeof(header[0]), header_size, ofp);
	printf(".");
	copy_tics(tick, ifp, ofp);	/*	copy entire data area...	*/
	printf(".");
	write_wait(how_long, ofp);	/*	write out the wait tics	*/
	printf(".");
	putc(0x80, ofp);	/*	puts the quit byte, hex 80	*/
	printf(".");
	fclose(ifp);
	fclose(ofp);
	if (utime((char *)target, &times) != 0) {
		perror("Unable to set time of destination file");
		exit(3);
	}
	printf(". [done]\n");
}

/*	write this many wait tics to the file	*/
void write_wait(double how_long, FILE * ofp)
{
	unsigned char holder[4 * 6] = {0};	/*	defaults to the biggest size	*/
	int write_status = 0;
	if (missing > 0) {	/*	if file is incorrect size */
		write_status = fwrite(holder, sizeof(holder[0]), missing, ofp);
		if (missing != write_status) {
			printf("\n\nError: write_wait() fwrite_1 failed, %d out of %d byte(s) copied.\n", write_status, missing);
			exit(3);
		}
		how_long--;
	}
	while (how_long-- > 0) {
		write_status = fwrite(holder, sizeof(holder[0]), tic_bytes, ofp);
		if (tic_bytes != write_status) {
			printf("\n\nError: write_wait() fwrite_2 failed, %d out of %d byte(s) copied.\n", write_status, tic_bytes);
			exit(3);
		}
	}
}

/*	this program returns true if there are enough disk space left
	to write a file of need_bytes	*/
int check_free(long need_bytes)
{
	struct dfree free;
	long avail;
	int drive;
	drive = getdisk();	/* get's the current drive letter */
	getdfree(drive + 1, &free);
	if (free.df_sclus == 0xFFFF) {
		printf("\nError in getdfree() call.\n");
		exit(3);
	}
	avail =  (long) free.df_avail * (long) free.df_bsec * (long) free.df_sclus;
	if (need_bytes > avail) /* if not enough space */
		return 1;
	else
		return 0;
}

/*
	removes the pauses of source, and write to target.
*/
int remove_pause(const char * source, const char * target)
{
	int changed = 0;
	FILE * ifp = NULL, * ofp = NULL;
	ifp = fopen(source, "rb");	/* open it in binary mode */
	if (ifp == NULL) {
		printf("Cannot open In.LMP file - \"%s\"\n", source);
		exit(3);
	}
	init_info(ifp, source);	/* if fail, won't return */
	NEED(filesize);
	ofp = fopen(target, "wb");	/*	target file, must after all ifp error check	*/
	if (ofp == NULL) {
		printf("Cannot create Out.LMP - \"%s\"\n", target);
		exit(3);
	}
	printf("%c \"%s\" %c \"%s\" : ",
			LISTCHAR, source, GOTOCHAR, target);
	changed = unpause(tick, ifp, ofp);
	fclose(ifp);
	fclose(ofp);
	if (changed) {	/* if the tmp file is different */
		if (utime((char *)target, &times)) {	/* set file time */
			perror("Unable to set time of Out.LMP");
			return 1;
		}
	}
	else {
		if (remove(target))
			perror("Unable to remove Out.LMP");
	}
	return 0;
}

/*
	removes the ticks between pauses for the file passed
	returns the number of modified pauses.
*/
int unpause(double tics, FILE * ifp, FILE * ofp)
{
	char tic_length[9] = {0};
	unsigned char holder[4 * 6] = {0};	/* defaults to the biggest size */
	int buffer_size = 0, write_status = 0, flag = 0, pause_count = 0,
		inter = 0, breakout;
	double tic_count = 0, tic_removed, total = 0;

	/* puts the in.lmp file's pointer on data, and flush header on out.lmp */
	fseek(ifp, (long) header_size, SEEK_SET);	/* goto data byte */
	fwrite(header, sizeof(header[0]), header_size, ofp); /* write header */

	while (tic_count++ < tics) { /* check the entire data area */
		buffer_size = fread(holder, sizeof(holder[0]), tic_bytes, ifp);
		write_status = fwrite(holder, sizeof(holder[0]), buffer_size, ofp);
		if (buffer_size != write_status) {
			printf("\n\nError: unpause() fwrite failed, %d out of %d byte(s) copied.\n", write_status, buffer_size);
			exit(3);
		}
		flag = check_pauses(holder, buffer_size);
		if (flag % 2) {	/* if unbalanced ps/pe encountered */
			printf("\n      %c PS at tic %.0f", PSPECHAR, tic_count);
			tic_removed = 0;
			breakout = 0;
			while (tic_count++ < tics) {
				buffer_size = fread(holder, sizeof(holder[0]), tic_bytes, ifp);
				flag = check_pauses(holder, buffer_size);
				if (flag) {	/* if any pause if found, flush it */
					write_status = fwrite(holder, sizeof(holder[0]), buffer_size, ofp);
					if (flag % 2) {	/* if odd # of pause, pe is detected */
						if (inter)
							printf("\n\t");
						else
							printf(", ");
						printf("PE at tic %.0f, %.0f tics removed.", tic_count, tic_removed);
						total += tic_removed;
						if (tic_removed)
							pause_count++;
						breakout = 1;
						break;	/* otherwize, pe and ps cancels, so stay */
					}
					else {
						printf("\n\t   Balanced PE-PS at tic %.0f, tic copied.", tic_count);
						inter = 1;
					}
				}
				else if (check_save(holder, buffer_size)) {
					write_status = fwrite(holder, sizeof(holder[0]), buffer_size, ofp);
					if (buffer_size != write_status) {
						printf("\n\nError: unpause() fwrite failed, %d out of %d byte(s) copied.\n", write_status, buffer_size);
						exit(3);
					}
					printf("\n\t   Save at tic %.0f, tic copied.", tic_count);
					inter = 1;
				}
				else {	/* all not true, so skipped */
					tic_removed++;
					buffer_size = 0;	/* indicate that it's skipped */
				}
			}
			if (!breakout && tic_count >= tics) {
				if (inter)
					printf("\n\t");
				else
					printf(", ");
				printf("EOF after tic %.0f, %.0f tics removed.", tic_count - 1, tic_removed);
				total += tic_removed;
				if (tic_removed)
					pause_count++;
			}
			inter = 0;
		}
		else if (flag) {
			printf("\n      %c Balanced PS-PE at tic %.0f.", PSPECHAR, tic_count);
		}
	}
	if (buffer_size != 0) {	/* if not skipped and last byte read is 'quit' */
		if (holder[buffer_size - 1] == 0x80)
			fseek(ofp, -1, SEEK_CUR);	/*	backup 1 byte	*/
	}
	putc(0x80, ofp);	/*	puts the quit byte, hex 80	*/
	tick_to_time(total, tic_length);
	printf("\n   Total : %d pause(s) modified, %s removed.\n", pause_count, tic_length);
	return pause_count;
}

/*
	check the while game tic and returns the number of pauses found.
	if the game is multiplayer, it is therotically possible for more than
	one player to press the pause key during one game tick.

	the way to check pause is (i & 0x83) == 129
	the way to check save is  (i & 0x83) == 130
*/
int check_pauses(unsigned char data_array[], int n)
{
	int i, result = 0;
	for (i = 3; i <= n; i += tic_size) {
		if ((data_array[i] & 0x83) == 129) {
			result++;
		}
	}
	return result;
}

/*
	check the while game tic to see if there are saves.
	as soon as a save is detected, return true. return false only
	when on save detected in whole gametic.
*/
int check_save(unsigned char data_array[], int n)
{
	int i;
	for (i = 3; i <= n; i += tic_size) {
		if ((data_array[i] & 0x83) == 130)
			return 1;
	}
	return 0;
}

