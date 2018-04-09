from dspwidget import dspWidget, dspCurveWidget

import numpy
import scipy
import scipy.signal

from guidata.qt.QtGui import QGridLayout, QPushButton, QVBoxLayout, QLabel
from guidata.qt.QtCore import SIGNAL
#from guidata.qt.QtGui import *



class dspAncWidget(dspWidget):
   def __init__(self, name, instanceId, widgetList, dataFunc, inactivityTimeout = True):
      dspWidget.__init__(self, name, instanceId, widgetList, inactivityTimeout = inactivityTimeout)

      self.dataFunc = dataFunc

      self.Fs = 2000

      layout = QGridLayout()
      self.setLayout(layout)

      self.resize(1024, 800)

      self.refPlotW = dspCurveWidget(mode="Freq",title="Reference PCM", show_itemlist=False)
      layout.addWidget(self.refPlotW, 1, 1, 1, 1)
      self.refExitButton = QPushButton("Hide")
      layout.addWidget(self.refExitButton, 1,0,1,1)
      self.connect(self.refExitButton, SIGNAL('clicked()'), self.refExitButtonPressed)

      self.errPlotW = dspCurveWidget(mode="Freq",title="Error Mic PCM", show_itemlist=False)
      layout.addWidget(self.errPlotW, 2, 1, 1, 1)
      self.errExitButton = QPushButton("Hide")
      layout.addWidget(self.errExitButton, 2,0,1,1)
      self.connect(self.errExitButton, SIGNAL('clicked()'), self.errExitButtonPressed)

      self.outPlotW = dspCurveWidget(mode="Freq",title="ANC Output", show_itemlist=False)
      layout.addWidget(self.outPlotW, 3, 1, 1, 1)
      self.outExitButton = QPushButton("Hide")
      layout.addWidget(self.outExitButton, 3,0,1,1)
      self.connect(self.outExitButton, SIGNAL('clicked()'), self.outExitButtonPressed)

      self.coefPlotW = dspCurveWidget(title="ANC Filter", mode="Freq", show_buttons=False, show_itemlist=True)
      self.coefPlotW.customCurve = self.updateFilterCurve
      self.coefPlotW.plotPoints = 1024
      layout.addWidget(self.coefPlotW, 4, 1, 1, 1)
      self.coefExitButton = QPushButton("Hide")
      layout.addWidget(self.coefExitButton, 4,0,1,1)
      self.connect(self.coefExitButton, SIGNAL('clicked()'), self.coefExitButtonPressed)

      #self.samples = QLabel("Samples ")
      #layout.addWidget(self.samples, 2,2)
      #self.samples_label =QLabel("Reference Mic Samples")
      #layout.addWidget(self.samples_label, 2,3,1,1)

            
   def kill(self):
      super(dspAncWidget, self).kill()
      self.coefPlotW.customCurve = None

   def refExitButtonPressed(self):
      if self.refPlotW.isVisible():
         self.refPlotW.hide()
         self.refExitButton.setText("Show")
      else:
         self.refPlotW.show()
         self.refExitButton.setText("Hide")
      
   def errExitButtonPressed(self):
      if self.errPlotW.isVisible():
         self.errPlotW.hide()
         self.errExitButton.setText("Show")
      else:
         self.errPlotW.show()
         self.errExitButton.setText("Hide")

   def outExitButtonPressed(self):
      if self.outPlotW.isVisible():
         self.outPlotW.hide()
         self.outExitButton.setText("Show")
      else:
         self.outPlotW.show()
         self.outExitButton.setText("Hide")

   def coefExitButtonPressed(self):
      if self.coefPlotW.isVisible():
         self.coefPlotW.hide()
         self.coefExitButton.setText("Show")
      else:
         self.coefPlotW.show()
         self.coefExitButton.setText("Hide")

   def update_samples_text(self, new_text):
       self.samples.setText(new_text)
        


   def update(self):
      try:
         anc = self.dataFunc(self.instanceId, self.preferredSamples)
      except RuntimeError:
         return
         
      refData = anc.get("ref")
      refChannels = anc.get("refChannels")
      refSamples = len(refData) / refChannels
      
      #self.update_samples_text(str(refSamples))

      errData = anc.get("err")
      errChannels = anc.get("errChannels")
      errSamples = len(errData) / errChannels

      outData = anc.get("out")
      outChannels = anc.get("outChannels")
      outSamples = len(outData) / outChannels


      wFilterData = anc.get("w")
      wChannels, wSamples = numpy.shape(wFilterData)

      # Conditional to keep backwards compatibility with old SPI logs. 
      Fs = anc.get('Fs') if (anc.get('Fs') != 0) else self.Fs

      self.refPlotW.update(Fs, refChannels, 1, refSamples, refData)
      self.errPlotW.update(Fs, errChannels, 1, errSamples, errData)
      self.outPlotW.update(Fs, outChannels, 1, outSamples, outData)
      self.coefPlotW.update(Fs,  wChannels, 1, 2*self.coefPlotW.plotPoints, wFilterData)
      self.refPlotW.BriefAnalysis.hide()
      self.errPlotW.BriefAnalysis.hide()
      self.outPlotW.BriefAnalysis.hide()
      #self.coefPlotW.BriefAnalysis.hide()
      self.refPlotW.update_box.hide()
      self.errPlotW.update_box.hide()
      self.outPlotW.update_box.hide()
      #self.coefPlotW.update_box.hide()
      self.refPlotW.update_box1.hide()
      self.errPlotW.update_box1.hide()
      self.outPlotW.update_box1.hide()
      #self.coefPlotW.update_box1.hide()
      self.refPlotW.Performance_config.hide()
      self.errPlotW.Performance_config.hide()
      self.outPlotW.Performance_config.hide()
      self.outPlotW.samples_label.hide()
      #self.coefPlotW.Performance_config.hide()
      self.refPlotW.Performance_off.hide()
      self.errPlotW.Performance_off.hide()
      self.outPlotW.Performance_off.hide()
      #self.coefPlotW.Performance_off.hide()



   def updateFilterCurve(self, plot, channel, data):
      channels, samples = numpy.shape(data)
      if (samples > 0 and self.coefPlotW.mode == "Freq"):
         self.coefPlotW.plotPoints = 1024
         w, h = scipy.signal.freqz(data[channel], 1, worN=self.coefPlotW.plotPoints)
         #y = numpy.unwrap(numpy.angle(h))
         y = 20*scipy.log10(numpy.abs(h))
         plot.curves[channel].set_data(plot.x, y)
      else:
         self.coefPlotW.plotPoints = samples/2
         plot.curves[channel].set_data(plot.x, 1000*data[channel])
         self.coefPlotW.spectrogramButton.setEnabled(False)
         self.coefPlotW.triggerButton.setEnabled(False)
         self.coefPlotW.PSDButton.setEnabled(False)
         

   def rescale(self):
      self.refPlotW.rescale()
      self.errPlotW.rescale()
      self.outPlotW.rescale()
      self.coefPlotW.rescale()

