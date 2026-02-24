Import("env")
import subprocess
from pathlib import Path

def make_binary(target, source, env):
    subprocess.check_call([
        env.subst("$OBJCOPY"),
        "-I", "ihex",
        "-O", "binary",
        str(source[0]),
        str(target[0]),
    ])

# 1. Teach SCons how to make a .bin from a .hex
hex_to_bin = env.Builder(action=make_binary, suffix=".bin", src_suffix=".hex")
env.Append(BUILDERS={"HexToBin": hex_to_bin})

# 2. Declare that we want firmware.bin, derived from firmware.hex
bin_node = env.HexToBin("$BUILD_DIR/firmware.bin", "$BUILD_DIR/firmware.hex")

env.Depends("upload", bin_node)

def upload_avr(source, target, env):
    # Invoke the avr_host upload in a separate PIO invocation.  By default
    # PlatformIO will auto-clean build directories for other environments
    # when a build starts.  That means the mcs51 build folder (and its
    # firmware.bin) can disappear before the AVR pre-script has a chance to
    # copy it, leading to a FileNotFoundError on every other run.  We disable
    # the auto-clean to keep the mcs51 artifacts intact.
    subprocess.check_call([
        "pio", "run", "-e", "avr_host", "-t", "upload",
        "--disable-auto-clean",
    ])

env.AddPostAction("upload", upload_avr)
