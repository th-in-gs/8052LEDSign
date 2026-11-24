# This script is for mcs51 environments.
#
# If the environment sets 'custom_code_loc', pass it to the SDCC linker as
# --code-loc, so the program (including its reset and interrupt vectors) is
# linked to start at that address instead of 0x0000.

Import("env")

code_loc = env.GetProjectOption("custom_code_loc", "")
if code_loc:
    env.Append(LINKFLAGS=["--code-loc", code_loc])
