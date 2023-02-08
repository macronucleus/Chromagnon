
import os
import numpy as N
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation

# not working for Mac 20210209
# use pythonw and do it on command line (not on priithon)
# 20210324 upgraded matplotlib and works on priithon with some error

def saveImage(arr3d, outfn='test.mp4', fps=10, cmap='afmhot', vmin=None, vmax=None, frame_txt='z = %i'):
    """
    install ffmpeg by homebrew for mp4
    save in mp4 or gif
    use prepColorImg() for color image, use cmap=None

    cmap: jet, gray, afmhot, gist_heat, magma, etc...
    raibow is hsv
    """
    arr3d = arr3d[:,::-1] # flip y

    fig, ax, img = prepareFig(arr3d, cmap, vmin, vmax)

    if frame_txt:
        txt = ax.text(3, 7, frame_txt % 0) #'z = {:.1f} $\mu m$'.format(z[64]))
    ax.spines['top'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Initialize the figure with an empty frame
    def init():
        img.set_data(np.zeros(arr3d.shape[1:3]))
        return img,

    # This function is called for each frame of the animation
    def animate(frame):   
        img.set_data(arr3d[frame])

        if frame_txt:
            txt.set_text(frame_txt % frame)
        return img,

    # Create the animation
    anim = animation.FuncAnimation(fig, animate, frames=len(arr3d),
                                   init_func=init, interval=20, blit=True)

    # Save the animation
    ext = os.path.splitext(outfn)[-1]
    if ext == '.mp4':
        myWriter = animation.FFMpegWriter(fps=fps, extra_args=['-vcodec', 'libx264'])
        anim.save(outfn, writer = myWriter)
    else:
        anim.save(outfn, writer = 'pillow', fps=fps)

    plt.close()

    return outfn

def prepareFig(arr3d, cmap='jet', vmin=None, vmax=None):
    ny, nx = arr3d.shape[1:3]
    ratio = 640 / nx
    
    fig, ax    = plt.subplots(nrows=1, ncols=1, figsize=(6.4, (ny*ratio)/100))

    ind = N.unravel_index(N.argmax(arr3d), arr3d.shape)
    z = ind[0]
    if vmax is None:
        vmax = arr3d.max()
    if vmin is None:
        vmin = arr3d.min()

    img = ax.imshow(arr3d[z], vmin=vmin, vmax=vmax, cmap=cmap)

    return fig, ax, img

def prepColorImg(arr, cmap='rg', colaxis=0, mis=(None,None), mas=(None,None)):
    assert arr.shape[colaxis] == len(cmap)
    if mis:
        assert arr.shape[colaxis] == len(mis)
    else:
        mis = [None for i in range(arr.shape[colaxis])]
    if mas:
        assert arr.shape[colaxis] == len(mas)
    else:
        mas = [None for i in range(arr.shape[colaxis])]
    assert arr.ndim <= 4

    if arr.ndim == 4:
        if colaxis == 1:
            brr = N.array([_prepColorImg(arr[:,i], mis[i], mas[i]) for i in range(arr.shape[1])])
        else:
            brr = N.array([_prepColorImg(a, mis[i], mas[i]) for i, a in enumerate(arr)])

    axisorder = 'rgb'
    rgb = N.zeros(brr[0].shape + (3,), dtype=N.uint8)
    for i, a in enumerate(brr):
        color = cmap[i].lower()
        axis = axisorder.index(color)
        rgb[...,axis] = a
    return rgb

def _prepColorImg(arr, mi=None, ma=None):
    if mi is None:
        mi = arr.min()
    if ma is None:
        ma = arr.max() - mi
    b = arr.astype(N.float32)
    b = N.clip(arr, mi, ma) - mi
    b /= b.max()
    b *= 255
    return b.astype(N.uint8)



##### plot ------
def savePlot(x, y, outfn='plot.mp4', fps=10):
    """
    outfn: extension should be mp4 or gif
    """
    fig = plt.figure()
    ax = fig.add_subplot(111)

    def update(f):
        ax.cla() # ax をクリア
        ax.grid()
        ax.plot(x, y, c="gray")
        ax.plot(x[f], y[f], "o", c="red")

    #interval = fps/60 * 1000
    anim = animation.FuncAnimation(fig, update, frames=list(range(len(x))), interval=20)

    ext = os.path.splitext(outfn)[-1]
    if ext == '.mp4':
        myWriter = animation.FFMpegWriter(fps=fps, extra_args=['-vcodec', 'libx264'])
        anim.save(outfn, writer = myWriter)
    else:
        myWriter = 'imagemagick'
        anim.save(outfn, writer="pillow", fps=fps)
        
    plt.close()


#### no matlab
# https://stackoverflow.com/questions/5585872/python-image-frames-to-video
def frame2movie(img, outfn='', fps=10):
    import os
    fns = 'test%03d.jpg'
    U.saveImg8_seq(img, fns)
    os.system("ffmpeg -f image2 -r %.2f -i %s -vcodec mpeg4 -y %s" % (fps, fns, outfn))
    #os.remove(fns)
    return outfn

def frame2movie_cv2(img, outfn='', fps=10):
    import cv2
    #https://stackoverflow.com/questions/44947505/how-to-make-a-movie-out-of-images-in-python
