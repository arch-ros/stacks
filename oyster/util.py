import subprocess
import asyncio
import io

def run_proc(args, logger, cwd=None):
        with subprocess.Popen(args,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                cwd=cwd) as proc:
            with proc.stdout:
                for line in io.TextIOWrapper(proc.stdout, encoding='utf-8'):
                    logger.trace(line.rstrip())
            exitcode = proc.wait()
            if exitcode != 0:
                return False
            return True
        return False

async def run_proc_async(args, logger, cwd=None):
    proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE,
                  stderr=asyncio.subprocess.STDOUT, cwd=cwd)

    out = proc.stdout
    if logger:
        while True:
            line = await out.readline()
            if line == b'':
                break
            try:
                line = line.decode('utf-8').rstrip()
                logger.trace(line)
            except UnicodeDecodeError:
                continue
    exitcode = await proc.wait()
    if exitcode != 0:
        return False
    return True

