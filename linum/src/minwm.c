#include <X11/Xlib.h>
#include <X11/XKBlib.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    Display *dpy = XOpenDisplay(NULL);
    if (!dpy) {
        fprintf(stderr, "minwm: cannot open display\n");
        return 1;
    }

    Window root = DefaultRootWindow(dpy);
    XSelectInput(dpy, root, SubstructureRedirectMask | SubstructureNotifyMask);

    XEvent ev;
    while (1) {
        XNextEvent(dpy, &ev);
        if (ev.type == KeyPress) {
            KeySym keysym = XkbKeycodeToKeysym(dpy, ev.xkey.keycode, 0, 0);
            (void)keysym; // Silence unused warning for barebones skeleton
        }
    }

    XCloseDisplay(dpy);
    return 0;
}
