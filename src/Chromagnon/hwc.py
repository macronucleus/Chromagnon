
import importlib
from . import chromformat

MAG=60 * (200/180) #1.333
REFWAVE=1

STAGES = {0: ['optosigma', 'S'],
              2: ['optosigma', 'T'],
              3: ['thorlabsstage', 'U']}

def get_shift_amount_at_camera(zum_sample, mag=MAG):
    """
    zum_sample: z shift in um at sample
    mag: total magnification

    return shift_amount at camera in um
    """
    return (mag**2) * zum_sample


def get_move_amount_from_csv(csvfn, refwave=REFWAVE, t=0, mag=MAG):
    """
    csvfn: output from Chromagnon

    return {w: zum at camera}
    """
    creader = chromformat.ChromagnonReader(csvfn)
    creader.close()

    creader.setRefWave(refwave)

    ret = {}
    for w in creader.wave:
        if w != refwave:
            par = creader.alignParms[t,w]
            z = par[0]
            zum = z * creader.pxlsiz[0]

            zum = get_shift_amount_at_camera(-zum, mag)
            ret[w] = zum
    return ret

def format_dic(dic):
    dic2 = {}
    for w, zum in dic.items():
        module, axis = STAGES[w]

        dic2.setdefault(module, {}).setdefault(axis, zum)
    return dic2

def get_stage_(dic2):
    """
    dic: {w: zum at camera} output of get_move_amount_from_csv

    return {module: {axis: zum}}
    """
    stages = []
    for module, dd in dic2.items():
        module = importlib.import_module('mdevices.stage.' + module)
        stage = module.Stage(module.PAR)
        stages.append(stage)

    return stages


# ── stage cache ────────────────────────────────────────────────────────────────
# Keep stage connections open to avoid serial port open/close instability.
# Keys are module names (e.g. 'optosigma'), values are Stage instances.
_stage_cache = {}

def open_stages():
    """
    Open all stages defined in STAGES and cache them.
    Already-open stages are left unchanged.
    Returns {module_name: stage} for successfully opened stages.
    """
    # collect unique module names
    module_names = {mod for mod, _ in STAGES.values()}
    for module_name in module_names:
        if module_name in _stage_cache:
            continue  # already open
        try:
            module = importlib.import_module('mdevices.stage.' + module_name)
            stage = module.Stage(module.PAR)
            _stage_cache[module_name] = stage
            print(f'Opened stage: {module_name}')
        except Exception as e:
            print(f'WARNING: could not open {module_name}: {e}')
    return dict(_stage_cache)

def close_stages():
    """Close all cached stages."""
    for module_name, stage in list(_stage_cache.items()):
        try:
            stage.close()
            print(f'Closed stage: {module_name}')
        except Exception as e:
            print(f'WARNING: error closing {module_name}: {e}')
        del _stage_cache[module_name]

def _get_stage(module_name):
    """Return cached stage, opening it if necessary."""
    if module_name not in _stage_cache:
        try:
            module = importlib.import_module('mdevices.stage.' + module_name)
            stage = module.Stage(module.PAR)
            _stage_cache[module_name] = stage
            print(f'Opened stage: {module_name}')
        except Exception as e:
            raise RuntimeError(f'Could not open {module_name}: {e}') from e
    return _stage_cache[module_name]


def get_positions():
    """
    Return current positions of all stages defined in STAGES.
    Uses cached stage connections.

    return {w: zum_at_stage} for each wave index
    """
    # Build {module_name: [wave_indices]} to query each stage only once
    module_waves = {}
    for w, (module, axis) in STAGES.items():
        module_waves.setdefault(module, []).append(w)

    ret = {}
    for module_name, waves in module_waves.items():
        try:
            stage = _get_stage(module_name)
            pos = stage.get_position()  # {axis: µm}
            for w in waves:
                _, axis = STAGES[w]
                if axis in pos:
                    ret[w] = pos[axis]
        except Exception as e:
            print(f'WARNING: could not read position from {module_name}: {e}')
            # Invalidate cache so next call tries to reopen
            _stage_cache.pop(module_name, None)
    return ret


def move(dic):
    """
    dic: {w: zum at camera} output of get_move_amount_from_csv
    Uses cached stage connections.

    return {module: {axis: zum}}
    """
    dic2 = {}
    for w, zum in dic.items():
        module, axis = STAGES[w]
        dic2.setdefault(module, {}).setdefault(axis, zum)

    errors = {}
    for module_name, dd in dic2.items():
        try:
            stage = _get_stage(module_name)
            stage.move_relative(dd)
        except Exception as e:
            print(f'WARNING: could not move {module_name}: {e}')
            # Invalidate cache so next call tries to reopen
            _stage_cache.pop(module_name, None)
            errors[module_name] = str(e)

    if errors:
        raise RuntimeError('Some stages failed to move: ' +
                           '; '.join(f'{m}: {e}' for m, e in errors.items()))
    return dic2


def doAll(csvfn, refwave=REFWAVE, t=0, mag=MAG):
    """
    csvfn: output from Chromagnon

    return {module: {axis: zum}}
    """

    ret = get_move_amount_from_csv(csvfn, refwave=refwave, t=t, mag=mag)

    return move(ret)
