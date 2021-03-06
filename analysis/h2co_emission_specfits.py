""" was vdisp.py """
import numpy as np
import pyspeckit 
import glob
from astropy.io import ascii
from astropy import table
from astropy import units as u
from astropy import log
from astropy.utils.console import ProgressBar
import paths
from astropy.table import Table, Column
from rounded import rounded
from latex_info import latexdict, format_float
import matplotlib
matplotlib.rc_file(paths.pcpath('pubfiguresrc'))
import pylab as pl
import copy

latexdict = copy.copy(latexdict)
assert '$r_{eff}$' in latexdict

sp = [pyspeckit.Spectrum(x) for x in
      ProgressBar(
          glob.glob(
              paths.dpath(
                  "spectra/emission/W51Ku_BD_h2co_v30to90_briggs0_contsub.image*.fits")))
      if '?' not in x
     ]
spectra = sp


tbl = Table(dtype=[(str, 20), float,   float,   float,   float,   float,
                   float,   float],
                   names=['Object Name',
                          'Amplitude',
                          '$E$(Amplitude)',
                          '$V_{LSR}$',
                          '$E(V_{LSR})$',
                          '$\sigma_V$',
                          '$E(\sigma_V)$',
                          #'$\Omega_{ap}$',
                          '$r_{eff}$',
                         ],
           )

# My manual inspection: which are detected?
# weakdetections are those that are not clearly believable
detections = ['e8mol', 'e2-e8 bridge', 'e10mol', 'NorthCore', 'e2_a', 'e2_b', 'e2_c']
weakdetections = ['e8mol_ext', 'e10mol_ext']

# conversion....
[s.xarr.convert_to_unit('km/s') for s in sp]

# setup
for s in sp:
    assert s.specname
    log.info(s.specname+" stats")
    noiseregion = (s.xarr < 40*u.km/u.s) | (s.xarr > 80*u.km/u.s)
    assert np.any(noiseregion)
    s.error[:] = s.data[noiseregion].std()

# fitting
for ii,thisspec in enumerate(sp):
    fig = pl.figure(1)
    fig.clf()
    thisspec.plotter(xmin=30,xmax=90, errstyle='fill', figure=fig)
    thisspec.specfit(fittype='gaussian',
                     guesses='moments',
                     negamp=False,
                     limited=[(True,False),(False,False),(True,False)])
    thisspec.baseline(excludefit=True, order=2, subtract=True)
    thisspec.specfit(fittype='gaussian',
                     guesses='moments',
                     negamp=False,
                     limited=[(True,False),(False,False),(True,False)])
    log.info(thisspec.specname+" fitting: {0}".format(thisspec.specfit.parinfo))
    thisspec.plotter.ymin -= 0.0005
    thisspec.specfit.plotresiduals(axis=thisspec.plotter.axis,clear=False,yoffset=-0.005,label=False)
    thisspec.plotter.savefig(paths.fpath('spectra/emission/'+thisspec.specname+"_h2co22emisson_fit.png"),
                                  bbox_inches='tight')

    thisspec.plotter(xmin=30,xmax=90, errstyle='fill')
    # Jy -> mJy
    thisspec.data *= 1e3
    thisspec.error *= 1e3
    #thisspec.unit = '$T_B$ (K)'
    thisspec.unit = 'mJy/beam'
    thisspec.plotter(errstyle='fill')
    ax2 = thisspec.plotter.axis.twinx()
    ax2.set_ylim(*(np.array(thisspec.plotter.axis.get_ylim()) * thisspec.header['JYTOK']/1e3))
    ax2.set_ylabel("$T_B$ (K)")
    thisspec.plotter.savefig(paths.fpath('spectra/emission/'+thisspec.specname+"_h2co22emisson_baselined.png"),
                                  bbox_inches='tight')

    omega_ap = thisspec.header['APAREA']*(np.pi/180.)**2 * u.sr
    r_eff = ((omega_ap/np.pi)**0.5).to(u.arcsec).value
    tbl.add_row([thisspec.specname,]+
                 list((rounded(thisspec.specfit.parinfo.AMPLITUDE0.value, thisspec.specfit.parinfo.AMPLITUDE0.error)*u.Jy).to(u.mJy))+
                 list(rounded(thisspec.specfit.parinfo.SHIFT0.value, thisspec.specfit.parinfo.SHIFT0.error))+
                 list(rounded(thisspec.specfit.parinfo.WIDTH0.value, thisspec.specfit.parinfo.WIDTH0.error))+
                [np.round(r_eff, 1)*u.arcsec]
                 #[np.round(thisspec.header['APAREA']*(np.pi/180.)**2, int(np.ceil(-np.log10(thisspec.header['APAREA']*(np.pi/180.)**2)))+1)],
               )

 
# sort such that e10 comes after e9
import natsort
tbl = tbl[natsort.index_natsorted(tbl['Object Name'])]

detection_note = ['-' if name in detections else
                  'weak' if name in weakdetections else
                  'none'
                  for name in tbl['Object Name']]
tbl.add_column(table.Column(data=detection_note, name='Detection Status'))

ok = np.array([row['Object Name'] in detections+weakdetections
               for row in tbl])

tbl[ok].write(paths.tpath('H2CO22_emission_spectral_fits.ecsv'), format='ascii.ecsv')

for row in tbl:
    if "_" in row['Object Name']:
        row['Object Name'] = row['Object Name'].replace("_","\_")
latexdict['header_start'] = '\label{tab:emission22}'
latexdict['caption'] = '\\formaldehyde \\twotwo emission line parameters'
latexdict['tablefoot'] = ('\par\nColumns with $E$ denote the errors on the measured parameters.'
                          '  $\sigma_{V}$ is the 1-dimensional gaussian velocity dispersion.  '
                          '$r_{eff}$ is the effective aperture radius.')
tbl[ok].write(paths.tpath('H2CO22_emission_spectral_fits.tex'), format='ascii.latex', latexdict=latexdict,
              #formats={'$\Omega_{ap}$': format_float}
             )
