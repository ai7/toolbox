/*	lmputil.h	*/

/*	these are all the function declarations	*/

void display_help(void);
void process_ext(const char *, char *);
void calculate(void);
void display(const char *);
void display12(const char *);
void all_lower(const char *, char *);
void convert(const char *, const char *);
int init_info(FILE *, const char *);
int check(void);
int check12(void);
void tick_to_time(double, char *);
void cut_it(double, double, const char *, const char *);
void copy_tics(double, FILE *, FILE *);
void wild_change(void);
int ver_viewer(FILE *);
void record_player(FILE * ofp, int x);
void change_ver(FILE * ofp, int x);
void wait_it(double, const char *, const char *);
void chop_it(double, const char *, const char *);
void write_wait(double, FILE *);
int check_free(long);
int remove_pause(const char *, const char *);
int unpause(double, FILE *, FILE *);
int check_pauses(unsigned char [], int);
int check_save(unsigned char [], int);

#ifndef __MSDOS__
/*	the following 2 functions are used when compile under gcc/os2	*/
/*	from the K & R C-bible	*/
void reverse(char s[])
{
	int c, i, j;
	for (i = 0, j = strlen(s) - 1; i < j; i++, j--) {
		c = s[i];
		s[i] = s[j];
		s[j] = c;
	}
}

/*	from the K & R C-bible	*/
void itoa(int n, char s[], int stupid)
{
	int i, sign;
	if ((sign = n) < 0)
		n = -n;
	i = 0;
	do {
		s[i++] = n % 10 + '0';
	} while ((n /= 10) > 0);
	if (sign < 0)
		s[i++] = '-';
	s[i] = '\0';
	reverse(s);
}
#endif
