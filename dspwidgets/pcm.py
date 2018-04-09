from dspwidget import dspWidget, dspCurveWidget
from guidata.qt.QtGui import QGridLayout
from guidata.qt.QtCore import SIGNAL
from guidata.qt.QtGui import *

import math
import numpy as np
from numpy import log10, pi, convolve, mean, polymul
import scipy
from scipy.signal.filter_design import bilinear
from scipy.signal import lfilter
from termcolor import colored


class dspPcmWidget(dspWidget):
   def __init__(self, name, instanceId, widgetList, dataFunc, inactivityTimeout = True):
      dspWidget.__init__(self, name, instanceId, widgetList, inactivityTimeout = inactivityTimeout)

      self.dataFunc = dataFunc
      self.Fs = 2000
      self.sample_rate = 5333
      self.pascal_constant=2*10**-5

      self.pcm =[]

      self.layout = QGridLayout()
      self.setLayout(self.layout) 
      
      self.pcmPlotW = dspCurveWidget(title="Monitor Mic Data", show_itemlist=False)
      self.layout.addWidget(self.pcmPlotW, 1, 0, 1, 1)

      self.resize(1000, 300)



      self.Button1 = QPushButton("Level")

      self.layout.addWidget(self.Button1, 1,1,1,1)

      self.connect(self.Button1, SIGNAL('clicked()'), self.Button1Pressed)



    

 
   def A_weighting(self, fs):

       f1 = 20.598997
       f2 = 107.65265
       f3 = 737.86223
       f4 = 12194.217
       A1000 = 1.9997

       NUMs = [(2*pi * f4)**2 * (10**(A1000/20)), 0, 0, 0, 0]
       DENs = polymul([1, 4*pi * f4, (2*pi * f4)**2],
                   [1, 4*pi * f1, (2*pi * f1)**2])
       DENs = polymul(polymul(DENs, [1, 2*pi * f3]),
                                 [1, 2*pi * f2])

       return bilinear(NUMs, DENs, fs)

   def C_weighting(self, fs):
      f1 = 20.598997 
      f4 = 12194.217
      C1000 = 0.0619

      NUMs = [(2*pi*f4)**2*(10**(C1000/20.0)),0,0]
      DENs = polymul([1,4*pi*f4,(2*pi*f4)**2.0],[1,4*pi*f1,(2*pi*f1)**2]) 

 
      return bilinear(NUMs,DENs,fs)
   
   def properties(self, signal, samplerate):
      signal_level = self.ac_rms(signal)
      weighted = self.A_weight(signal, samplerate)
      weighted1= self.C_weight(signal, samplerate)
      weighted_level = self.ac_rms(weighted)
      weighted_level1= self.ac_rms(weighted1)
    
      return [
    'RMS level: %.3f (%.3f dB SPL)' % (signal_level, self.dB(signal_level)+10),
    'A-weighted: %.3f (%.3f dB(A))' % (weighted_level, self.dB(weighted_level)+10),
    'C-weighted: %.3f (%.3f dB(C))' % (weighted_level1, self.dB(weighted_level1)+10)
    #'A-difference: %.3f dB' % self.dB(weighted_level/signal_level),
    #'-----------------',
]

   def ac_rms(self, signal):

       return self.rms_flat(signal - mean(signal))

   def rms_flat(self, a):

       return np.sqrt(np.mean(np.absolute(a)**2))

   def dB(self, level):

       return 20 * log10(self.rms_flat(level)/self.pascal_constant)

   def A_weight(self, signal, samplerate):
       B, A = self.A_weighting(samplerate)
       return lfilter(B, A, signal)

   def C_weight(self, signal, samplerate):
       B, A = self.C_weighting(samplerate)
       return lfilter(B, A, signal)

   def Button1Pressed(self):
       
       elements = np.asarray(self.pcm)
       rms_pcm = np.sqrt(np.mean(elements**2))
       dB = 20*scipy.log10(np.abs(rms_pcm/self.pascal_constant))
       #print (str(dB)+" "+'dB SPL')
       Sound_properties = self.properties(elements, self.sample_rate)
       print colored("Sound Properties:", 'yellow')
       print colored(Sound_properties[0], 'yellow')
       print colored(Sound_properties[1], 'yellow')
       print colored(Sound_properties[2], 'yellow')
       #print colored(Sound_properties[3], 'blue')
      

   def update(self):
      try:
         data = self.dataFunc(self.instanceId, self.preferredSamples)
      except RuntimeError:
         return
      
      channels = data.get('chn')
      blockSize = data.get('frm')
      self.pcm = data.get('pcm')
      #elements = np.asarray(pcm)


         
         #this will calculate the signal to noise ratio of monitor microphone placed in the point of interest(in between two micrphones)
         #snr = scipy.stats.signaltonoise(elements)


      #extracting list of pcm data into another list with two elements for taking first element and use for that finding rms value 
      #two_elements=[pcm[2*i:2*i+2] for i in range(int(0),int(math.ceil(len(pcm)/2.0)))]

      # Conditional to keep backwards compatibility with old SPI logs. 
      Fs = data.get('Fs') if (data.get('Fs') != 0) else self.Fs
      if Fs == 96:
          Fs = 96000
      self.sample_rate= Fs
      samples = len(self.pcm) / channels
      self.pcmPlotW.update(Fs, channels, blockSize, samples, self.pcm) 
      #self.updatesamples(str(samples))


   def rescale(self):
      self.pcmPlotW.rescale()
