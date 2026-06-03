
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

            zum = get_shift_amount_at_camera(zum, mag)
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

def move(dic):
    """
    dic: {w: zum at camera} output of get_move_amount_from_csv

    return {module: {axis: zum}}
    """

    dic2 = {}
    for w, zum in dic.items():
        module, axis = STAGES[w]

        dic2.setdefault(module, {}).setdefault(axis, zum)

    errors = {}
    for module_name, dd in dic2.items():
        try:
            module = importlib.import_module('mdevices.stage.' + module_name)
            stage = module.Stage(module.PAR)
            stage.move_relative(dd)
            stage.close()
        except Exception as e:
            print(f'WARNING: could not move {module_name}: {e}')
            errors[module_name] = str(e)

    if errors:
        raise RuntimeError('Some stages failed to move: ' +
                           '; '.join(f'{m}: {e}' for m, e in errors.items()))
    return dic2


def get_positions():
    """
    Return current positions of all stages defined in STAGES.

    return {w: zum_at_stage} for each wave index
    """
    # Build {module_name: [wave_indices]} to open each stage only once
    module_waves = {}
    for w, (module, axis) in STAGES.items():
        module_waves.setdefault(module, []).append(w)

    ret = {}
    for module_name, waves in module_waves.items():
        try:
            module = importlib.import_module('mdevices.stage.' + module_name)
            stage = module.Stage(module.PAR)
            pos = stage.get_position()  # {axis: µm}
            stage.close()
            for w in waves:
                _, axis = STAGES[w]
                if axis in pos:
                    ret[w] = pos[axis]
        except Exception as e:
            print(f'WARNING: could not read position from {module_name}: {e}')
    return ret


def doAll(csvfn, refwave=REFWAVE, t=0, mag=MAG):
    """
    csvfn: output from Chromagnon

    return {module: {axis: zum}}
    """

    ret = get_move_amount_from_csv(csvfn, refwave=refwave, t=t, mag=mag)

    return move(ret)
        
