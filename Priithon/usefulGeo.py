"""
a bunch of 2d geometry functions

points are always defined as y,x tuples or numpy arrays
segments are sequences of pairs-of-nodes
boxes are a sequence of two diagonal edge-points
"""

def geoPointsEq(yx0, yx1, eps=1e-2):
    """
    are two points equal 
      (within eps distance, x,y separately)
    """
    d0 = yx0[0] - yx1[0]
    d1 = yx0[1] - yx1[1]

    return abs(d0)<eps and abs(d1)<eps

def geoSegEqOpposite(s0,s1, eps=1e-2):
    """
    are two segments equals and oppositely directed
    """
    return geoPointsEq(s0[0],s1[1], eps) and geoPointsEq(s0[1],s1[0], eps)

def geoPointSeqSide(p, seg):
    """
    determine on which side of a segment a given point lies

    http://astronomy.swin.edu.au/~pbourke/geometry/insidepoly/
    
    Given a line segment between P0 (x0,y0) and P1 (x1,y1), another point P (x,y) has the following relationship to the line segment. 

    Compute 
     (y - y0) (x1 - x0) - (x - x0) (y1 - y0)

    if it is less than 0 then P is to the right of the line segment, if greater than 0 it is to the left, if equal to 0 then it lies on the line segment.
    """
    y,x = p
    (y0,x0),(y1,x1) = seg

    return (y - y0)*(x1 - x0) - (x - x0)*(y1 - y0)

#todo: U.mm([e.sidePointSeg(yx,seg) for seg in segs])
#   but need to take "inward corners" into account to tell if inside polygon IF not CONVEX

def geoBoxToSegs(edges):
    """
    return list of 4 seqments of box defined by its two edges
    """
    (y0,x0),(y1,x1) = edges
    if y0>y1:
        y0,y1 = y1,y0
    if x0>x1:
        x0,x1 = x1,x0

    return [((y0,x0),(y0,x1)),
            ((y0,x1),(y1,x1)),
            ((y1,x1),(y1,x0)),
            ((y1,x0),(y0,x0))]

def geoPointLineDist(p, seg, testSegmentEnds=False):
    """
    Minimum Distance between a Point and a Line
    Written by Paul Bourke,    October 1988
    http://astronomy.swin.edu.au/~pbourke/geometry/pointline/
    """
    from numpy import sqrt

    y3,x3 = p
    (y1,x1),(y2,x2) = seg

    dx21 = (x2-x1)
    dy21 = (y2-y1)
    
    lensq21 = dx21*dx21 + dy21*dy21
    if lensq21 == 0:
        #20080821 raise ValueError, "zero length line segment"
        dy = y3-y1 
        dx = x3-x1 
        return sqrt( dx*dx + dy*dy )  # return point to point distance

    u = (x3-x1)*dx21 + (y3-y1)*dy21
    u = u / float(lensq21)


    x = x1+ u * dx21
    y = y1+ u * dy21    

    if testSegmentEnds:
        if u < 0:
            x,y = x1,y1
        elif u >1:
            x,y = x2,y2
    

    dx30 = x3-x
    dy30 = y3-y

    return sqrt( dx30*dx30 + dy30*dy30 )

def geoPointSegsDist(p, segs):
    """
    smallest distance of a point to a sequence of line segments
    """
    return min([geoPointLineDist(p,seg, True) for seg in segs])

def geoPointInsideBox(p, edges):
    """
    returns True only if p lies inside or on the sides of box
    """
    y,x = p
    (y0,x0),(y1,x1) = edges
    if y0>y1:
        y0,y1 = y1,y0
    if x0>x1:
        x0,x1 = x1,x0

    return x0<=x<=x1 and y0<=y<=y1

def geoSeqsBoundingBox(segs):
    """
    return corners (LB+TR) of smallest box containing all segments in segs
    """
    yMin = 1e100
    yMax =-1e100
    xMin = 1e100
    xMax =-1e100
    for s in segs:
        (y0,x0),(y1,x1) = s

        yMax = max(yMax, y0)
        yMin = min(yMin, y0)            
        yMax = max(yMax, y1)
        yMin = min(yMin, y1)            

        xMax = max(xMax, x0)
        xMin = min(xMin, x0)            
        xMax = max(xMax, x1)
        xMin = min(xMin, x1)            

    from numpy import array
    return array((yMin,xMin)),array((yMax,xMax))

def geoPointsBoundingBox(points, intCoords=False):
    """
    return corners (LB+TR) of smallest box containing all points
    if intCoords:
        use int(...) for lower and int(...)+1 for upper bounds
    """
    yMin = 1e100
    yMax =-1e100
    xMin = 1e100
    xMax =-1e100
    for p in points:
        (y0,x0) = p

        yMax = max(yMax, y0)
        yMin = min(yMin, y0)            

        xMax = max(xMax, x0)
        xMin = min(xMin, x0)            

    if intCoords:
        yMax = int(yMax)+1
        xMax = int(xMax)+1
        yMin = int(yMin)
        xMin = int(xMin)
    from numpy import array
    return array((yMin,xMin)),array((yMax,xMax))
