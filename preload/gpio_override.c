#include <stdio.h>
#include <dlfcn.h>
#include <stdlib.h>
#include <glib.h>
#include <string.h>
#include <unistd.h>

/* Keep a single global list of open GPIO fds for the running application */
static GList *open_files = NULL;

/* Pointers to the real library functions, set once the first time we need them */
static int (*real_open)(const char *pathname, int flags) = NULL;
static int (*real_close)(int fd) = NULL;
static ssize_t (*real_read)(int fd, void *buf, size_t count) = NULL;

/* Data type keeping track of all GPIO files opened by the current app */
typedef struct _open_file
{
    int descriptor; /* fd */
    int gpio;       /* corresponding GPIO pin */
} open_file;

/* Search list to find out what GPIO pin is open on a given descriptor */
int get_pin_for_descriptor(int descriptor)
{
    GList *l;
    for (l = open_files; l != NULL; l = l->next)
    {
	open_file *file = l->data;
	if (file->descriptor == descriptor)
	{
	    return file->gpio;
	}
    }
    return -1;
}

/* Remember (by reassignment or appending) that a given fd has a given GPIO pin open */
void assign_pin_for_descriptor(int descriptor, int pin)
{
    GList *l;
    int set = 0;
    for (l = open_files; l != NULL; l = l->next)
    {
	open_file *file = l->data;
	if (file->descriptor == descriptor)
	{
	    file->gpio = pin;
	    set = 1;
	}
    }
    if (!set)
    {
	open_file *file = malloc(sizeof(open_file));
	if (!file)
	{
	    exit(1);
	}
	file->descriptor = descriptor;
	file->gpio = pin;
	open_files = g_list_append(open_files, file);
    }
}

/* Clear entry for closed descriptor */
void close_descriptor(int descriptor)
{
    GList *l;
    for (l = open_files; l != NULL; l = l->next)
    {
	open_file *file = l->data;
	if (file->descriptor == descriptor)
	{
	    open_files = g_list_remove(open_files, file);
	    return;
	}
    }
}

/* Helper func to obtain the real code. Loads functions from library specified in
 * environment variable LIBC_SO. With thanks to Greg KH https://www.linuxjournal.com/article/7795 */
void* get_real_func(const char *name)
{
    char *error;
    char *libc = getenv("LIBC_SO");
    if (libc == NULL)
    {
	printf("ERROR: Preloader requires LIBC_SO to be set\n");
	exit(1);
    }
    void *handle = dlopen(libc, RTLD_LAZY);
    if (!handle)
    {
	fputs(dlerror(), stderr);
	exit(1);
    }
    void *result = dlsym(handle, name);
    if ((error = dlerror()) != NULL)
    {
	fprintf(stderr, "%s\n", error);
	exit(1);
    }
    return result;
}

/* Open a file, keeping track of it if needed */
int open(const char *pathname, int flags)
{
    if (!real_open)
    {
	real_open = get_real_func("open");
    }
    char *gpio_part = strstr(pathname, "gpio/gpio");
    int pin = -1;
    if (gpio_part != NULL)
    {
	sscanf(gpio_part, "gpio/gpio%d", &pin);
    }
    int fileno = real_open(pathname, flags);
    if (pin >= 0)
    {
	assign_pin_for_descriptor(fileno, pin);
    }
    return fileno;
}

/* Read from a file, possibly substituting a response */
ssize_t read(int fd, void *buf, size_t count)
{
    if (!real_read)
    {
	real_read = get_real_func("read");
    }

    int gpio = get_pin_for_descriptor(fd);
    if (gpio != -1)
    {
	/* This is the fun part where we do something different */

	/* First see if the environment variable is set */
	char *web_tx_env = getenv("WEB_TX_OVERRIDE");
	if (web_tx_env != NULL && count > 0) /* make sure the buffer has room for one char in it */
	{
	    /* If the file exists, pretend that somebody (who's not us) is transmitting */
	    /* COS = GPIO10 = 1 when clear, 0 when channel occupied */
	    /* PTT = GPIO17 = 1 when transmitting, 0 when not transmitting */
	    /* So in override state, COS = 0, PTT = 0. Otherwise perform real read. */
	    if (access(web_tx_env, F_OK) != -1)
	    {
		char *char_buf = (char*)buf;
		/* file exists => override */
		if (gpio == 10) /* COS */
		{
		    char_buf[0] = '0';
		    return 1;
		}
		if (gpio == 17) /* PTT */
		{
		    char_buf[0] = '0';
		    return 1;
		}
	    }
	}
    }
    
    /* Otherwise fall back to a normal read */
    return real_read(fd, buf, count);
}

/* Close a file, removing our stored entry if required */
int close(int fd)
{
    if (!real_close)
    {
	real_close = get_real_func("close");
    }

    close_descriptor(fd);

    return real_close(fd);
}
