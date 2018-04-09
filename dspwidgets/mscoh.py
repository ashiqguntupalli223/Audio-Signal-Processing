from dspwidget import dspWidget, dspCurveWidget
from guidata.qt.QtGui import QGridLayout
import numpy
import scipy.signal

class dspMscohWidget(dspWidget):
   def __init__(self, name, instanceId, widgetList, dataFunc, inactivityTimeout = True):
      dspWidget.__init__(self, name, instanceId, widgetList, inactivityTimeout = inactivityTimeout)

      self.dataFunc = dataFunc
      
      self.Fs = 2000
      
      layout = QGridLayout()
      self.setLayout(layout)
      
      self.resize(1024, 800)
      
      self.refPlotW = dspCurveWidget(mode="PCM",title="Reference PCM", show_itemlist=False)
      layout.addWidget(self.refPlotW, 1, 0, 1, 1)

      self.errPlotW = dspCurveWidget(mode="PCM",title="Error Mic PCM", show_itemlist=False)
      layout.addWidget(self.errPlotW, 2, 0, 1, 1)

      self.mscohPlotW = dspCurveWidget(mode="MSCoh",title="Magnitude Squared Coherence", show_itemlist=False)
      layout.addWidget(self.mscohPlotW, 3, 0, 1, 2)


   def update(self):
      try:
         data = self.dataFunc(self.instanceId, self.preferredSamples)
      except RuntimeError:
         return
      
      refData = data.get("ref")
      refChannels = data.get("refChannels")
      refSamples = len(refData) / refChannels
      
      errData = data.get("err")
      errChannels = data.get("errChannels")
      errSamples = len(errData) / errChannels
      
      Fs = data.get('Fs', self.Fs)
      
      self.refPlotW.update(Fs, refChannels, 1, refSamples, refData)
      self.errPlotW.update(Fs, errChannels, 1, errSamples, errData)
      
      
      # Accumulate the data for all visible Error Signals
      errDataSum = numpy.zeros(errSamples)
      for curve in self.errPlotW.plot.curves:
        if curve.isVisible():
            try:
                errDataSum += curve.get_data()[1]# get data here
            except:
                continue
    
      # Accumulate the data for all visible Reference Signals
      refDataSum = numpy.zeros(refSamples)
      for curve in self.refPlotW.plot.curves:
        if curve.isVisible():
            try:
                refDataSum += curve.get_data()[1]# get data here
            except:
                continue
    
      
      mscohData = scipy.signal.coherence(refDataSum, errDataSum, window='hanning', fs = 2000, nperseg=2048)[1]
      mscohSamples = len(mscohData)
      
      self.mscohPlotW.update(Fs, 1, 1, mscohSamples, mscohData)
      
      
   def rescale(self):
      self.refPlotW.rescale()
      self.errPlotW.rescale()
      self.mscohPlotW.rescale()
