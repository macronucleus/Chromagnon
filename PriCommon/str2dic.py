SEP=' '
WSP=':'

def str2dic(ss, sep=SEP, wsep=WSP):
    """
    ss: wave:value wave:value (careful with space)
    func: int or float or eval
    """
    if isinstance(ss, basestring):
        ss = ss.strip()
        if wsep in ss:
            dic = []
            for s in ss.split(sep):
                dic.append([eval(wd) for wd in s.split(wsep)])
            dic = dict(dic)
        else:
            try:
                dic = eval(ss)
            except:
                dic = {}
    else:
        dic = ss
    return dic

def dic2str(dic, sep=SEP, wsep=WSP):
    """
    return wave:value wave:value
    """
    ss = []
    for wave, value in dic.iteritems():
        ss.append('%i%s%.4f' % (wave, wsep, value))
    return sep.join(ss)

def dic2val(dic, key):
    """
    return value
    """
    if type(dic) == dict:
        return dic[key]
    else:
        return dic

SEP=[',', ' ']
RANGE='-'
def numberSeq(vstr, removeOverlap=True):
    """
    vstr: '29,39,40-48'
    return [29, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48]
    """
    if not vstr:
        return None
    slist = [s.strip() for s in vstr.split(SEP[0])]
    for sep in SEP[1:]:
        slist2 = []
        for s in slist:
            slist2 += s.split(sep)
        slist = slist2
    slist2 = []
    for s in slist:
        if RANGE in s:
            start, stop = s.split(RANGE)
            slist2 += range(eval(start), eval(stop)+1)
        else:
            slist2 += [s]
    slist = [int(s) for s in slist2]
    if removeOverlap:
        slist = list(set(slist))
    slist.sort()
    return slist
