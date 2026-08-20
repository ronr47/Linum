import os, struct, subprocess

targets = [
    b"VORTEX",
    b"MONASTIC",
    b"monolight",
    b"mojo",
    b"Mojo",
    b"KOKORO",
    b"trinity",
    b"/developer/workspace",
    b"ext4"
]

devices = ["/dev/sda", "/dev/sdb"]

print("============================================================")
print(" 🔍 DEEP BARE-METAL SCAN FOR MISSING 200GB STORAGE PARTITION")
print("============================================================")

for dev in devices:
    print(f"\n[*] Scanning Drive {dev} for Partition Boundaries & Superblocks...")
    
    # 1. Check Backup GPT Header at the physical end of disk (LBA -33)
    try:
        with open(dev, "rb") as f:
            f.seek(0, os.SEEK_END)
            disk_size = f.tell()
            print(f"    ▶ Physical Disk Size: {disk_size / (1024**3):.2f} GB ({disk_size:,} bytes)")
            
            # Read Secondary GPT Header (last 33 sectors = 16896 bytes)
            f.seek(max(0, disk_size - (33 * 512)))
            tail_data = f.read()
            if b"EFI PART" in tail_data:
                print(f"    [★] FOUND BACKUP GPT HEADER AT DISK TAIL ON {dev}!")
                idx = tail_data.find(b"EFI PART")
                hdr = tail_data[idx:idx+92]
                rev, size, crc, _, cur_lba, backup_lba, first_lba, last_lba = struct.unpack("<IIIIQQQQ", hdr[8:56])
                print(f"        First Usable LBA : {first_lba} ({first_lba * 512 / (1024**3):.2f} GB)")
                print(f"        Last Usable LBA  : {last_lba} ({last_lba * 512 / (1024**3):.2f} GB)")
            
            # 2. Fast stride scan every 10 GB across disk to find 200GB Ext4 Superblocks (0xEF53)
            # Ext4 superblock is at offset 1024 inside the partition block
            print(f"\n    ▶ Scanning for Ext4 Filesystem Superblocks (Magic 0xEF53)...")
            STEP_MB = 256 # Sample every 256 MB
            for mb_off in range(0, int(disk_size / (1024*1024)), STEP_MB):
                f.seek(mb_off * 1024 * 1024 + 1024)
                sb = f.read(1024)
                if len(sb) >= 60 and sb[56:58] == b"\x53\xef":
                    s_inodes_count, s_blocks_count, s_r_blocks_count, s_free_blocks_count = struct.unpack("<IIII", sb[:16])
                    s_log_block_size = struct.unpack("<I", sb[24:28])[0]
                    block_size = 1024 << s_log_block_size
                    part_size_gb = (s_blocks_count * block_size) / (1024**3)
                    vol_name = sb[120:136].decode("latin1", errors="ignore").strip("\x00")
                    last_mount = sb[136:200].decode("latin1", errors="ignore").strip("\x00")
                    
                    print(f"    [★] EXT4 SUPERBLOCK FOUND at Offset: {mb_off} MB ({mb_off/1024:.2f} GB)")
                    print(f"        Partition Size : {part_size_gb:.2f} GB")
                    print(f"        Volume Label   : '{vol_name}' | Last Mounted: '{last_mount}'")
    except PermissionError:
        print("    [!] Root required.")
    except Exception as e:
        print(f"    [!] Error: {e}")
