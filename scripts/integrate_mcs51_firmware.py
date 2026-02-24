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

# Always try to update the local copy.  ``local_bin`` lives in the
# AVR build directory and is used by the ``XxdBin`` builder below.  We
# can't assume that it will persist between builds, so copy unconditionally
# when the source exists.  If the source doesn't exist yet, print a helpful
# warning instead of raising an exception; the build will normally generate
# the file later when the mcs51 environment is built.
if os.path.exists(mcs51_bin):
    shutil.copy2(mcs51_bin, local_bin)
else:
    # This can happen when someone runs the AVR target standalone or when
    # the nested invocation cleaned the mcs51 directory unexpectedly.  In
    # most cases the mcs51 environment will be built shortly afterwards,
    # so we just log a warning to avoid confusing stack traces.
    print(f"Warning: mcs51 firmware not found at {mcs51_bin}, "
          "AVR build may be out of date")

env.Append(PIOBUILDFILES=env.Object(env.XxdBin(local_bin)))