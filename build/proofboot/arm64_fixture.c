typedef unsigned long long EFI_STATUS;

__attribute__((used))
EFI_STATUS efi_main(void *image_handle, void *system_table)
{
    (void)image_handle;
    (void)system_table;
    return 0; /* EFI_SUCCESS */
}
