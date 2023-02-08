

import numpy as N

def Rayleigh_resolution(NA=0.9, wave=515):
    return 0.61 * wave / NA

def Abbe_limit(NA=0.9, wave=515):
    return wave / (2 * NA)

def angleFromNA(NA=0.9, n=1.0):
    """
    return angle in degrees
    """
    # NA = n sin(theta)
    # sin(theta) = NA / n
    return N.degrees(N.arcsin(NA / float(n)))


def snellsLow(n1=1.0, theta1=64.158, n2=1.515):
    """
    n1 > n2
    return angle in degrees
    """
    # n1 sin(theta1) = n2 sin(theta2)
    # sin(theta2) = n1 sin(theta1) / n2
    return N.degrees(N.arcsin((n1 * N.sin(theta1)) / float(n2)))


def diameter4imaging(z=80, n=1.33, NA=1.2):
    """
    return diameter of the circle affected by the sample
    """
    # NA = n sin(theta)
    # sin(theta) = NA / n
    theta = N.arcsin(NA / float(n))
    # tan(theta) = r / z
    r = z * N.tan(theta)
    # diamter
    return 2 * r

def helz_at_back_focal(size=1.1, z=80, n=1.33, NA=1.2, pixelSize=0.088, npix=512):
    """
    size: target size in um
    z: imaging depth in um
    return helz in the back focal plane
    """
    field = float(pixelSize) * npix
    helz_cam = field / size
    d = diameter4imaging(z, n, NA)
    factor = d / field
    return helz_cam * factor

def laserM2(m2=1.05, wave=488, diam_mm=1, distance_mm=1000):
    """
    calculates the resulting beam diameter from laser
    
    return (divergence angle in degrees, resulting beam diameter)
    """
    wave /= 10.**6 # -> mm
    
    theta = 4 * m2 * wave / (N.pi * diam_mm)

    div = distance_mm * N.tan(theta) * 2 + diam_mm

    return N.degrees(theta), div




def rescan_resolution(fwhm_emi=250, fwhm_exc=250, mag=2):
    a = fwhm_emi / mag
    b = (mag - 1) * fwhm_exc / mag
    return (a**2 + b**2) ** 0.5

def rescan_optimum_mag(fwhm_emi=250, fwhm_exc=250):
    return 1 + (fwhm_emi**2) / (fwhm_exc**2)

def rescan_optimum_spot_width(fwhm_emi=250, fwhm_exc=250):
    a = fwhm_emi * fwhm_exc
    b = (fwhm_emi**2) + (fwhm_exc**2)
    return a / (b**0.5)

def opra_resolution(fwhm_emi=250, fwhm_exc=250):
    mag = (fwhm_exc**2) / (fwhm_exc**2 + fwhm_emi**2)
    return mag * ((fwhm_exc**2 + fwhm_emi**2)**0.5)

#------------ color LUT -----------------#

COLOR_TABLE=[(1,0,1),   (0,0,1), (0,1,1), (0,1,0), (1,1,0),  (1,0,0), (1,0,1), (1,1,1)]
COLOR_NAME =['purple', 'blue',  'cyan',  'green', 'yellow', 'red', 'purple', 'white']
#WAVE_CUTOFF=[400,       450,     500,     530,     560,      660,   800,     1100]
WAVE_CUTOFF=[420,       460,     500,     540,      580,     640,    700,   1100]

def LUT(wave):
    """
    return colorTuple (R,G,B)
    """
    col = None
    if wave > 350:
        for i, WAVE in enumerate(WAVE_CUTOFF):
            if wave < WAVE:
                col = COLOR_TABLE[i]
                break
    else: # imgio.generalIO makes channel names 0,1,2,3...
        i = int(wave) % (len(COLOR_TABLE) - 1)
        colors = COLOR_TABLE[::2][:-1] + COLOR_TABLE[1::2]
        col = colors[i]
    if not col:
        col = COLOR_TABLE[i+1]
    return col


def LUTname(colorTuple):
    """
    return colorname
    """
    if COLOR_TABLE.count(colorTuple):
        idx = COLOR_TABLE.index(colorTuple)
        return COLOR_NAME[idx]
    else:
        raise ValueError('colorTuple %s not found in COLOR_NAME list' % colorTuple)
        
