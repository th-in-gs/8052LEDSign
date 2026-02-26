# This script is for the mcs51 environment.
#
# It sets up the 'upload' targe to build a binary for the mcs51 (in addition
# to the default Intel HEX file, and invokes the avr-host environment's upload
# target to upload the AVR host program and the mcs51 binary to the AVR at the
# end of the mcs51 upload target.

Import("env")
import subprocess
from pathlib import Path

# Teach SCons how to make a .bin from a .hex.
def make_binary(target, source, env):
    subprocess.check_call([
        env.subst("$OBJCOPY"),
        "-I", "ihex",
        "-O", "binary",
        str(source[0]),
        str(target[0]),
    ])
hex_to_bin = env.Builder(action=make_binary, suffix=".bin", src_suffix=".hex")
env.Append(BUILDERS={"HexToBin": hex_to_bin})

# Declare that we want firmware.bin, derived from firmware.hex.
bin_node = env.HexToBin("$BUILD_DIR/firmware.bin", "$BUILD_DIR/firmware.hex")

# Make the 'upload' target depend on the binary being created.
env.Depends("upload", bin_node)

# Set the upload to happen (via the avr-host target) after the 'upload' target
# is built.
def upload_avr(source, target, env):
    # Invoke the avr_host upload in a separate PIO invocation. By default
    # PlatformIO will auto-clean build directories for other environments
    # when a build starts. That means the mcs51 build folder (and its
    # firmware.bin) can disappear before the AVR pre-script has a chance to
    # copy it, leading to a FileNotFoundError on every other run. We disable
    # the auto-clean to keep the mcs51 artifacts intact.
    subprocess.check_call([
        "pio", "run", "-e", "avr_host", "-t", "upload",
        "--disable-auto-clean",
    ])
env.AddPostAction("upload", upload_avr)
