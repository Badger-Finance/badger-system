import time

from helpers.console_utils import console


def run_persistent(function, args, num_args=1, run_interval=10):
    while True:
        try:
            function(args[0], args[1])
        except Exception as e:
            console.print("[red]Error[/red]", e)
        finally:
            time.sleep(run_interval)
