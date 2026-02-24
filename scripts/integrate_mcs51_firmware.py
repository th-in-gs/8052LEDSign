Import("env")
import subprocess
import os
import shutil

def xxd_generator(target, source, env):
    src = str(source[0])
    tgt = str(target[0])
    var_name = os.path.splitext(os.path.basename(src))[0].replace("-", "_").replace(".", "_")

    result = subprocess.run(["xxd", "-i", "-n", var_name, src],
        capture_output=True, text=True, check=True)

    with open(tgt, "w") as f:
        f.write("#include <stdint.h>\n#include <avr/pgmspace.h>\n\n")
        f.write(result.stdout
            .replace("unsigned char ", "const uint8_t ")
            .replace("[] =", "[] PROGMEM =")
            .replace("unsigned int ", "const uint16_t "))

def xxd_emitter(target, source, env):
    build_dir = env.subst("$BUILD_DIR")
    return [f"{build_dir}/xxd_gen/{os.path.splitext(os.path.basename(str(s)))[0]}.c"
            for s in source], source

env.Append(BUILDERS={"XxdBin": env.Builder(
    action=xxd_generator,
    emitter=xxd_emitter,
    suffix=".c",
    src_suffix=".bin"
)})
env['BUILDERS']['Object'].add_src_builder('XxdBin')

build_dir = env.subst("$BUILD_DIR")
mcs51_bin = os.path.abspath(f"{build_dir}/../mcs51/firmware.bin")
local_bin = f"{build_dir}/xxd_gen/firmware.bin"

os.makedirs(f"{build_dir}/xxd_gen", exist_ok=True)
if os.path.exists(mcs51_bin):
    try:
        os.symlink(mcs51_bin, local_bin)
    except FileExistsError:
        pass

env.Append(PIOBUILDFILES=env.Object(env.XxdBin(local_bin)))