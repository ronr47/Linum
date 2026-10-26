#ifndef _SYS_CDEFS_H
#define _SYS_CDEFS_H
#if defined(__cplusplus)
  #define __BEGIN_DECLS extern "C" {
  #define __END_DECLS }
#else
  #define __BEGIN_DECLS
  #define __END_DECLS
#endif
#define __attribute_pure__  __attribute__((__pure__))
#define __attribute_const__ __attribute__((__const__))
#endif
