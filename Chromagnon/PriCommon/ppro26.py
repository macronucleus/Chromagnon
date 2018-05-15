
import multiprocessing as mp, sys

#from Priithon.all import Y

if hasattr(sys,'app'): # runnging on Priithon
    NCPU = 1
else:
    NCPU=mp.cpu_count()
    #import multiprocessing.dummy as mp

def funcWrap(args):
    """
    return (i, result)
    """

    callable, i, kwds = args[:3]
    
    ret = callable(*args[3:], **kwds)
    return i, ret

def pmap(callable, sequence, limit=NCPU, *args, **kwds):
    """
    map function for parallel processing accepting args, kwds
    callable: the first arg must accept items of "sequence"
    limit: number of cpu to use, if None, uses all available CPU
    
    return list of results
    """
    if limit > 1:

        pool = mp.Pool(processes=limit)
        args0 = []
        for i, item in enumerate(sequence):
            args0.append([callable, i, kwds, item] + list(args))

        results = pool.map(funcWrap, args0)
        pool.terminate()
        # re-ordering
        # result contains sequential number
        results.sort()
        # remove number
        return [result[1] for result in results]
    else:

        return [callable(x, *args, **kwds) for x in sequence]

pmapLarge = pmap
 
def funcMrcFile2D(func, fn, lock, t, w, z, *args, **kwds):
    """
    wrpping function to read fn in process safe way using lock
    z: can be None for 3D stack
    
    return (t,w,z), result
    """
    h = O.mrcIO.mrcHandle(fn)
    lock.acquire()
    if z is None: # 3D
        a = h.get3DArr(t=t, w=w)
    else:
        a = h.getArr(t=t, w=w, z=z)
    lock.release()
    
    result = func(a, *args, **kwds)
    return (t,w,z), result


def pmapMrcFile(callable, fn, ts, ws, zs, limit=None, timeout=None, *args, **kwds):
    """
    map function that reads Mrc file accepting args, kwds
    callable: the first arg must accept 2D or 3D array at t, w, z
    fn: mrc file
    ts: list of time
    ws: list of wave
    zs: list of zpos, can be None for 3D stack
    limit: number of cpu to use, if None, uses all available CPU
    
    return list of results ordered by t,w,z
    """
    pool = mp.Pool(processes=limit)
    lock = mp.Lock()
    results = []
    if zs is None: # 3D
        zs = [None]
    for t in ts:
        for w in ws:
            for z in zs:
                args = [fn, lock, t, w, z] + list(args)
                results.append(pool.apply_async(funcMrcFile2D, *args, **kwds))

    results = [ret.get(timeout=None) for ret in results]
    results.sort() # sort by twz
    # remove number
    return [r[1] for r in results]
