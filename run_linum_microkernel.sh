#!/usr/bin/env bash
# ==============================================================================
# LINUM QUANTUM HYPERVISOR COMPILER TOOLCHAIN SUITE
# Axioms: 64B Alignment • Self-Hosting Arena Substrate • Zero Heap Dependency
# ==============================================================================
set -euo pipefail

# 1. EMIT LOW-LEVEL ASSEMBLY BOOTSTRAP STRATACT
cat << 'ASM' > loader.s
.code32
.section .multiboot
.balign 64

.set MULTIBOOT_MAGIC,    0x1BADB002
.set MULTIBOOT_FLAGS,    0x00000003
.set MULTIBOOT_CHECKSUM, -(MULTIBOOT_MAGIC + MULTIBOOT_FLAGS)

.long MULTIBOOT_MAGIC
.long MULTIBOOT_FLAGS
.long MULTIBOOT_CHECKSUM

.section .text
.global _start
.extern kernel_main

_start:
    cli
    movl $0x90000, %esp
    pushl %ebx
    pushl %eax
    call kernel_main

.global hlt_loop
hlt_loop:
    cli
    hlt
    jmp hlt_loop
ASM

# 2. EMIT UNIFIED CORE SYSTEM STATE CONTAINER
cat << 'C' > kernel_main.c
typedef unsigned char uint8_t;
typedef unsigned short uint16_t;
typedef unsigned int uint32_t;

#define COM1_PORT 0x3F8

extern void hlt_loop(void) __attribute__((noreturn));
extern void microkernel_init(void);

static inline void outb(uint16_t port, uint8_t val) {
    __asm__ volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
}

static inline uint8_t inb(uint16_t port) {
    uint8_t ret;
    __asm__ volatile ("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}

static inline void init_serial(void) {
    outb(COM1_PORT + 1, 0x00);
    outb(COM1_PORT + 3, 0x80);
    outb(COM1_PORT + 0, 0x03);
    outb(COM1_PORT + 1, 0x00);
    outb(COM1_PORT + 3, 0x03);
    outb(COM1_PORT + 2, 0xC7);
    outb(COM1_PORT + 4, 0x0B);
}

__attribute__((noinline)) void put_char(char c) {
    while ((inb(COM1_PORT + 5) & 0x20) == 0);
    outb(COM1_PORT + 0, (uint8_t)c);
}

void print_serial(const char *str) {
    for (uint32_t i = 0; str[i] != '\0'; i++) {
        put_char(str[i]);
    }
}

void kernel_main(uint32_t magic, uint32_t multiboot_info_ptr) {
    (void)multiboot_info_ptr;
    init_serial();
    
    if (magic != 0x2BADB002) {
        print_serial("\r\n[-] LINUM BOOT FAILURE: INVALID MULTIBOOT MAGIC\r\n");
        hlt_loop();
    }

    print_serial("\r\n[+] LINUM QUANTUM SUBSTRATE COREPIN DEPLOYED SUCCESSFUL.\r\n");
    print_serial("[*] Custom Compiler Subsystem Initialized.\r\n");

    microkernel_init();

    print_serial("[+] System context steady. Entering nominal execution halt state.\r\n");
    hlt_loop();
}
C

# 3. EMIT ADVANCED PARSER AND ARENA NODE ALLOCATOR SUBSTRATE
cat << 'EOF' > microkernel.c
typedef unsigned char uint8_t;
typedef unsigned short uint16_t;
typedef unsigned int uint32_t;

#define COM1_PORT 0x3F8
#define MAX_TOKEN_LEN 32
#define ARENA_SIZE_BYTES 4096

/* Axiom: Explicit Enum serialization constraints */
typedef enum {
    NODE_TYPE_IDENTIFIER = 0,
    NODE_TYPE_INTEGER    = 1,
    NODE_TYPE_ADD        = 2,
    NODE_TYPE_ASSIGNMENT = 3
} ast_type_t;

/* Struct aligned to 64-byte structural bounds for predictable emission metadata */
typedef struct ast_node {
    uint32_t type;
    char value[MAX_TOKEN_LEN];
    struct ast_node *left;
    struct ast_node *right;
} __attribute__((aligned(64))) ast_node_t;

/* Static Arena Memory Frame allocation mapping */
static uint8_t linum_compiler_arena[ARENA_SIZE_BYTES] __attribute__((aligned(64)));
static uint32_t arena_offset = 0;

extern void print_serial(const char *str);
extern void put_char(char c);

static inline uint8_t inb(uint16_t port) {
    uint8_t ret;
    __asm__ volatile ("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}

static inline void outb(uint16_t port, uint8_t val) {
    __asm__ volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
}

static char serial_getc(void) {
    while ((inb(COM1_PORT + 5) & 0x01) == 0);
    return (char)inb(COM1_PORT);
}

/* Axiomatic 64-Byte Bump Allocator */
static ast_node_t *allocate_ast_node(uint32_t type) {
    uint32_t current = arena_offset;
    /* Enforce strict 64-byte block boundary checks */
    uint32_t next = (current + sizeof(ast_node_t) + 63) & ~63;
    
    if (next > ARENA_SIZE_BYTES) {
        print_serial("\r\n[-] CRITICAL: Compiler Arena Out of Memory.\r\n");
        return (ast_node_t*)0;
    }
    
    arena_offset = next;
    ast_node_t *node = (ast_node_t *)&linum_compiler_arena[current];
    node->type = type;
    node->left = (ast_node_t*)0;
    node->right = (ast_node_t*)0;
    node->value[0] = '\0';
    return node;
}

/* Rudimentary string copy implementation primitive */
static void inline_strcpy(char *dest, const char *src) {
    uint32_t i = 0;
    while (src[i] != '\0' && i < (MAX_TOKEN_LEN - 1)) {
        dest[i] = src[i];
        i++;
    }
    dest[i] = '\0';
}

/* Dynamic AST Node State Visualizer Tracker */
void print_ast_tree(ast_node_t *node, uint32_t depth) {
    if (!node) return;
    
    for (uint32_t i = 0; i < depth; i++) print_serial("  ");
    
    if (node->type == NODE_TYPE_ASSIGNMENT) print_serial("[ASSIGN =]\r\n");
    else if (node->type == NODE_TYPE_ADD) print_serial("[OP +]\r\n");
    else if (node->type == NODE_TYPE_IDENTIFIER) {
        print_serial("[IDENT: \"");
        print_serial(node->value);
        print_serial("\"]\r\n");
    }
    else if (node->type == NODE_TYPE_INTEGER) {
        print_serial("[INT: ");
        print_serial(node->value);
        print_serial("]\r\n");
    }
    
    print_ast_tree(node->left, depth + 1);
    print_ast_tree(node->right, depth + 1);
}

/* Multi-character stream compiler scanner engine pass */
void execute_isolated_parser_pipeline(void) {
    char token[MAX_TOKEN_LEN];
    uint32_t t_idx = 0;
    
    ast_node_t *root = (ast_node_t*)0;
    ast_node_t *current_op = (ast_node_t*)0;

    print_serial("[*] Linum Compiler Core Online. Stream instructions (End with semicolon ';'):\r\n\r\n> ");

    while (1) {
        char c = serial_getc();
        
        if (c == '`') {
            print_serial("\r\n[*] Shutdown trap tripped. Exiting virtual layer.\r\n");
            outb(0x604, 0x20);
            break;
        }

        put_char(c);

        /* Buffer validation and scanning fields mapping logic */
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')) {
            if (t_idx < (MAX_TOKEN_LEN - 1)) {
                token[t_idx++] = c;
            }
            continue;
        }

        /* Token segmentation condition detected */
        if (c == ' ' || c == '\t' || c == '=' || c == '+' || c == ';') {
            token[t_idx] = '\0';
            
            if (t_idx > 0) {
                /* Evaluate token type content safely */
                uint32_t node_type = (token[0] >= '0' && token[0] <= '9') ? NODE_TYPE_INTEGER : NODE_TYPE_IDENTIFIER;
                ast_node_t *new_node = allocate_ast_node(node_type);
                inline_strcpy(new_node->value, token);

                if (!root) {
                    root = new_node;
                } else if (current_op && !current_op->right) {
                    current_op->right = new_node;
                }
                t_idx = 0; /* Clear index array track pointer safely */
            }

            if (c == '=') {
                ast_node_t *assign_node = allocate_ast_node(NODE_TYPE_ASSIGNMENT);
                assign_node->left = root;
                root = assign_node;
                current_op = assign_node;
            }
            else if (c == '+') {
                ast_node_t *add_node = allocate_ast_node(NODE_TYPE_ADD);
                /* Push assignment structural right child values out dynamically */
                add_node->left = current_op->right;
                current_op->right = add_node;
                current_op = add_node;
            }
            else if (c == ';') {
                print_serial("\r\n\r\n[+] AST GENERATION COMPLETE. PARSE TREE GRAPH:\r\n");
                print_ast_tree(root, 1);
                
                /* Reset compiler memory space limits cleanly for subsequent instruction passes */
                root = (ast_node_t*)0;
                current_op = (ast_node_t*)0;
                arena_offset = 0;
                print_serial("\r\n> ");
            }
        }
    }
}

void microkernel_init(void) {
    execute_isolated_parser_pipeline();
}
