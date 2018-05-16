import six
SEP=' '
WSP=':'

def str2dic(ss, sep=SEP, wsep=WSP):
    """
    ss: wave:value wave:value (careful with space)
    func: int or float or eval
    """
    if isinstance(ss, six.string_types):
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

def dic2str(dic, sep=SEP, wsep=WSP, digit=None):
    """
    return wave:value wave:value
    """
    if digit is None:
        digit = 2
    if type(dic) == dict:
        ss = []
        for wave, value in dic.items():
            if value % 1:
                sformat = '%i%s%.' + str(digit) + 'f'
                ss.append(sformat % (wave, wsep, value))
            else:
                ss.append('%i%s%i' % (wave, wsep, value))
        return sep.join(ss)
    elif dic % 1:
        
        sformat = '%.' + str(digit) + 'f'
        return sformat % dic
    else:
        return str(dic)

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
        return []
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
            slist2 += list(range(eval(start), eval(stop)+1))
        else:
            slist2 += [s]
    slist = [int(s) for s in slist2 if s]
    if removeOverlap:
        slist = list(set(slist))
    slist.sort()
    return slist
