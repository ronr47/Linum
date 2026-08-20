#include <stdio.h>
#include <bpf/libbpf.h>

int main(void)
{
    libbpf_set_strict_mode(LIBBPF_STRICT_ALL);

    printf("libbpf version: %s\n", libbpf_version_string());

    return 0;
}
