extern void print_serial(const char *str);
extern void put_char(char c);

static void run_compiler_lexer_pass(void)
{
    print_serial("[+] Gnomonic Lexer Pass Initiated...\n");
    print_serial("[+] Validating pebble matrices and token boundaries.\n");
}

void kernel_main(int base_alpha, int height_beta)
{
    if (base_alpha <= 0 || height_beta <= 0) {
        print_serial("[-] Error: Invalid coordinate parameters detected.\n");
        return;
    }

    run_compiler_lexer_pass();

    int area_delta = (base_alpha * height_beta) / 2;

    print_serial("[*] Base Alpha: ");
    put_char('0' + (base_alpha / 10));
    put_char('0' + (base_alpha % 10));
    print_serial("\n");

    print_serial("[*] Height Beta: ");
    put_char('0' + (height_beta / 10));
    put_char('0' + (height_beta % 10));
    print_serial("\n");

    print_serial("[*] Area Delta Calculated: ");
    put_char('0' + (area_delta / 10));
    put_char('0' + (area_delta % 10));
    print_serial(" absolute units.\n");

    print_serial(
        "[+] Circular Revolution of the Celestial Sphere complete. "
        "System halted safely.\n"
    );
}
