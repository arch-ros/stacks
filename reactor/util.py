import subprocess

def run_proc(args, logger, cwd=None):
        with subprocess.Popen(args,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                cwd=cwd) as proc:
            with proc.stdout:
                for line in iter(proc.stdout.readline, b''):
                    logger.trace(line.decode('utf-8').strip())
            exitcode = proc.wait()
            if exitcode != 0:
                return False
            return True
        return False
