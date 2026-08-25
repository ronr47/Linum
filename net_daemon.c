/* Core Bare-Metal Execution Node */

// Low-level pointer interface to execute commands directly via the Android shell binary
int system(const char *cmd);
unsigned int sleep(unsigned int sec);

void _start(void) {
    while (1) {
        // Direct, non-blocking hardware settings table overrides
        system("settings put global network_selection_mode 0 > /dev/null 2>&1");
        system("settings delete global network_selection_name > /dev/null 2>&1");
        system("settings delete global network_selection_short > /dev/null 2>&1");
        system("am broadcast -a android.intent.action.ACTION_MANAGED_CONFIG_CHANGED > /dev/null 2>&1");
        
        sleep(10);
    }
}
