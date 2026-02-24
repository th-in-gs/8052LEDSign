Import("env")
import subprocess
from pathlib import Path

build_dir = Path(env.subst("$BUILD_DIR"))
hex_path = build_dir / "firmware.hex"
bin_path = build_dir / "firmware.bin"

def make_binary(target, source, env):
    subprocess.check_call([
        env.subst("$OBJCOPY"),
        "-I", "ihex",
        "-O", "binary",
        str(source[0]),
        str(target[0]),
    ])

bin_node = env.Command(
    str(bin_path),
    str(hex_path),
    make_binary,
)

env.Depends(bin_node, "$BUILD_DIR/${PROGNAME}.hex")
env.Default(bin_node)
