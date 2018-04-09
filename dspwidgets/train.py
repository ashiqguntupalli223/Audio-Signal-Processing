from dspwidget import dspWidget, dspCurveWidget

import numpy
import scipy
import scipy.signal

from guidata.qt.QtGui import QGridLayout
from guidata.qt.QtGui import *
from guidata.qt.QtCore import SIGNAL

class dspTrainWidget(dspWidget):
   def __init__(self, name, instanceId, widgetList, dataFunc, inactivityTimeout = True):
      dspWidget.__init__(self, name, instanceId, widgetList, inactivityTimeout = inactivityTimeout)

      self.dataFunc = dataFunc

      self.Fs = 2000

      layout = QGridLayout()
      self.setLayout(layout)

      self.refPlotW = dspCurveWidget(title="Reference PCM", color=1, show_itemlist=False)
      layout.addWidget(self.refPlotW, 0, 0, 1, 1)
      
      self.micPlotW = dspCurveWidget(title="MIC PCM", color=2, show_itemlist=False)
      layout.addWidget(self.micPlotW, 0, 1, 1, 1)
      
      self.coefPlotW = dspCurveWidget(title="Secondary Path Response", mode="Freq", show_buttons=True, show_itemlist=False)
      self.coefPlotW.customCurve = self.updateFilterCurve
      self.coefPlotW.plotPoints = 512
      layout.addWidget(self.coefPlotW, 1, 0, 1, 2)

      self.numberofsamples =QLabel("samples")
      layout.addWidget(self.numberofsamples,2,2,1,1)
      self.samples = QLabel("samples")
      layout.addWidget(self.samples,2,3,1,1)

      self.Button = QPushButton("Phase (degrees)")
      layout.addWidget(self.Button, 1,2,1,1)
      self.connect(self.Button, SIGNAL('clicked()'), self.ButtonPressed)
      self.flag = False

      self.refPlotW.BriefAnalysis.hide()
      self.micPlotW.BriefAnalysis.hide()
      self.coefPlotW.BriefAnalysis.hide()
      self.refPlotW.update_box.hide()
      self.micPlotW.update_box.hide()
      self.coefPlotW.update_box.hide()
      self.refPlotW.update_box1.hide()
      self.micPlotW.update_box1.hide()
      self.coefPlotW.update_box1.hide()
      self.refPlotW.Performance_config.hide()
      self.micPlotW.Performance_config.hide()
      self.coefPlotW.Performance_config.hide()
      self.refPlotW.Performance_off.hide()
      self.micPlotW.Performance_off.hide()
      self.coefPlotW.Performance_off.hide()
      self.refPlotW.samples_label.hide()
      self.micPlotW.samples_label.hide()
      self.coefPlotW.samples_label.hide()

   def ButtonPressed(self):
      if self.flag :
         self.Button.setText("Phase (degrees)")
         self.flag = False
      else:         
         self.Button.setText("Magnitude(dB)")
         self.flag = True

 
   def updatesamples(self, new_text):
      self.numberofsamples.setText(new_text)

   def kill(self):
      super(dspTrainWidget, self).kill()
      self.coefPlotW.customCurve = None

   def update(self):
      try:
         train = self.dataFunc(self.instanceId)
      except RuntimeError:
         return

      micData = train.get('mic')
      refData = train.get('ref')
      coefs = train.get('cfs')
      # Conditional to keep backwards compatibility with old SPI logs. 
      Fs = train.get('Fs') if (train.get('Fs') != 0) else self.Fs

      self.refPlotW.update(Fs, 1, 1, len(refData), refData)
      self.micPlotW.update(Fs, 1, 1, len(micData), micData)
      self.coefPlotW.update(Fs, 1, 1, 2*self.coefPlotW.plotPoints, coefs)

      samples = len(coefs)  
      self.updatesamples(str(samples))

   def updateFilterCurve(self, plot, channel, data):
      if (len(data) > 0 and self.coefPlotW.mode == "Freq"):
         w, h = scipy.signal.freqz(data, worN=self.coefPlotW.plotPoints)
         if abs(max(h)) > 0.0:
            phase = numpy.angle(h, deg=True)           
            y = 20*scipy.log10(numpy.abs(h))
            if self.flag :
               plot.curves[channel].set_data(plot.x, phase)
            else:
               plot.curves[channel].set_data(plot.x, y)
      else:
         self.coefPlotW.plotPoints = len(data)/2
         plot.curves[channel].set_data(plot.x, data)
         self.coefPlotW.spectrogramButton.setEnabled(False)
         self.coefPlotW.triggerButton.setEnabled(False)
         self.coefPlotW.PSDButton.setEnabled(False)
         self.coefPlotW.BriefAnalysis.setEnabled(False)

   def rescale(self):
      self.micPlotW.rescale()
      self.refPlotW.rescale()
      self.coefPlotW.rescale()
