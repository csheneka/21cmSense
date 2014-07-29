#! /usr/bin/env python
'''
Creates an array file for use by calc_sense.py.  The main product is the uv coverage produced by the array during the time it takes the sky to drift through the primary beam; other array parameters are also saved.  Array specific information comes from an aipy cal file.'''
import aipy as a, numpy as n, pylab as p
import optparse, sys

o = optparse.OptionParser()
a.scripting.add_standard_options(o,cal=True)

opts, args = o.parse_args(sys.argv[1:])

if array == 'hera':
    obs_duration = 40. # minutes
    dish_size_in_lambda = 7 #simple lambda/D
    SIZE = 600 #uv plane size in wavelengths
    sigma = 1/(2*n.pi*0.0643)

#============================SIMPLE GRIDDING FUNCTION=======================

def beamgridder(xcen,ycen,size):
    crds = n.mgrid[0:size,0:size]
    cen = size/2 - 0.5 # correction for centering
    xcen += cen
    ycen = -1*ycen + cen
    beam = n.zeros((size,size))
    if round(ycen) > size - 1 or round(xcen) > size - 1: 
        return beam
    else:
        beam[round(ycen),round(xcen)] = 1. #single pixel gridder
        return beam

#==========================FIDUCIAL OBSERVATION PARAMETERS===================

#while poor form to hard code these to arbitrary values, they have very little effect on the end result

#observing time
cen_jd = 2454600.90911
start_jd = cen_jd - (1./24)*((obs_duration/60)/2)
end_jd = cen_jd + (1./24)*(((obs_duration-1)/60)/2)
times = n.arange(start_jd,end_jd,(1./24/60))
print 'Observation duration:', start_jd, end_jd

fq = .150 #all calculations in calc_sense.py are relative to 150 MHz

#================================MAIN CODE===================================

#load array information
aa = a.cal.get_aa(opts.cal,n.array([.150]))
cat = a.src.get_catalog(opts.cal,'z') #create zenith source object
nants = len(aa)

cnt = 0
uvbins = {}
aa.set_jultime(cen_jd)
obs_lst = aa.sidereal_time()
obs_zen = a.phs.RadioFixedBody(obs_lst,aa.lat)
obs_zen.compute(aa) #observation is phased to zenith of the center time of the drift 

#find redundant baselines
for i in xrange(nants):
    print 'working on antenna %i of %i' % (i, len(aa))
    for j in xrange(nants):
        if i == j: continue #no autocorrelations
        u,v,w = aa.gen_uvw(i,j,src=obs_zen)
        uvbin = '%.1f,%.1f' % (u,v)
        cnt +=1
        if not uvbins.has_key(uvbin): uvbins[uvbin] = ['%i,%i' % (i,j)]
        else: uvbins[uvbin].append('%i,%i' % (i,j))
print 'There are %i baseline types' % len(uvbins.keys())

#grid each baseline type into uv plane
dim = n.round(lambda_max/dish_size_in_lambda/2)*2 - 1 # round to nearest odd
uvplane = {}
uvsum,quadsum = n.zeros((dim,dim)), n.zeros((dim,dim)) #quadsum adds all non-instantaneously-redundant baselines incoherently
for cnt, uvbin in enumerate(uvbins):
    print 'working on %i of %i uvbins' % (cnt+1, len(uvbins))
    uvplane[uvbin] = n.zeros((dim,dim))
    for t in times:
        aa.set_jultime(t)
        lst = aa.sidereal_time()
        obs_zen.compute(aa)
        bl = uvbins[uvbin][0]
        nbls = len(uvbins[uvbin])
        i, j = bl.split(',')
        i, j = int(i), int(j)
        u,v,w = aa.gen_uvw(i,j,src=obs_zen)
        _beam = beamgridder(sigma=sigma/dish_size_in_lambda,xcen=u/dish_size_in_lambda,ycen=v/dish_size_in_lambda,size=dim)
        uvplane[uvbin] += nbls*_beam
        uvsum += nbls*_beam
    quadsum += (uvplane[uvbin])**2

quadsum = quadsum**.5
uvplane['sum'] = uvsum
uvplane['quadsum'] = quadsum

n.savez('%s_arrayfile.npz' % name,sum=uvplane['sum'],quadsum=uvplane['quadsum'])