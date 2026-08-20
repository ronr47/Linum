#include <errno.h>
#include <stdio.h>
#include <string.h>

#include <bpf/libbpf.h>

int main(void)
{
    struct bpf_object *obj;
    struct bpf_program *prog;
    int err;

    libbpf_set_strict_mode(LIBBPF_STRICT_ALL);

    obj = bpf_object__open_file("xdp_prog.o", NULL);
    if (!obj) {
        fprintf(stderr, "bpf_object__open_file failed\n");
        return 1;
    }

    err = libbpf_get_error(obj);
    if (err) {
        fprintf(stderr, "bpf_object__open_file error: %d (%s)\n",
                err, strerror(-err));
        bpf_object__close(obj);
        return 1;
    }

    prog = bpf_object__find_program_by_name(obj, "xdp_prog");
    if (!prog) {
        fprintf(stderr, "xdp_prog not found\n");
        bpf_object__close(obj);
        return 1;
    }

    printf("object: OK\n");
    printf("program: %s\n", bpf_program__name(prog));

    err = bpf_object__load(obj);
    if (err) {
        fprintf(stderr, "bpf_object__load failed: %d (%s)\n",
                err, strerror(-err));
        bpf_object__close(obj);
        return 1;
    }

    printf("kernel load: OK\n");

    bpf_object__close(obj);
    return 0;
}
