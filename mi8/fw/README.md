Put the touch controller firmware here as `st_fts_e1.ftb` (the file the stock driver loads: the Mi 8 log says
`Read FW from BIN file st_fts_e1.ftb`, FW 0x51, config 0x21, 94376 + 2656 bytes). `mi8/build-mi8.sh` embeds it in the shim and the
touch probe then burns it into the chip when its firmware version differs (the stock ROM does the same on every boot).
Keep it out of public repos if you are not sure about its license; a private fork is fine.
