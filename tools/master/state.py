"""Atomic state access for the TwinGuard session control system."""
import json, os, pathlib, tempfile, time
ROOT = pathlib.Path(__file__).resolve().parents[2]
STATE = ROOT / 'docs' / 'master' / 'STATE.json'
LOCK = STATE.with_suffix('.lock')

class StateError(RuntimeError): pass

def _locked():
    class Lock:
        def __enter__(self):
            self.fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(self.fd, str(os.getpid()).encode())
            return self
        def __exit__(self, *exc):
            os.close(self.fd)
            try: LOCK.unlink()
            except FileNotFoundError: pass
    return Lock()

def read_state():
    return json.loads(STATE.read_text(encoding='utf-8'))

def write_state(data):
    with _locked():
        fd, name = tempfile.mkstemp(prefix='STATE.', suffix='.tmp', dir=STATE.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(data, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
            os.replace(name, STATE)
        finally:
            if os.path.exists(name): os.unlink(name)

def append_log(message):
    path = ROOT / 'docs' / 'master' / 'CHANGELOG.md'
    with path.open('a', encoding='utf-8') as f: f.write(f"\n- {time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")

def output_conflicts(state, task):
    wanted = set(task.get('outputs', []))
    return [other['id'] for other in state['tasks']
            if other['id'] != task['id'] and other['status'] == 'running'
            and wanted.intersection(other.get('outputs', []))]

