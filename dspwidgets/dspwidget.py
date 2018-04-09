import guidata
import time, threading
import dspmsg
import numpy as np

import numpy
from numpy import log10, mean 
from scipy import signal


from guidata.dataset.datatypes import DataSet
from guidata.dataset.dataitems import FloatItem, BoolItem

from guidata.qt.QtGui import QWidget, QPushButton, QGridLayout, QVBoxLayout, QLineEdit, QLabel
from guidata.qt.QtCore import QTimer, QPoint, SIGNAL

from guiqwt.plot import CurveWidget
from guiqwt.curve import PanelWidget
from guiqwt.builder import make
from guidata.qt.QtGui import *

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from termcolor import colored
import scipy


#from matplotlib.pyplot import specgram


defaultUpdateTimeout = 100
defaultRescaleTimeout = 1000
defaultDeadTimeout = 2000

class dspWidget(QWidget):
   def __init__(self, name, instanceId, widgetList,inactivityTimeout):
      QWidget.__init__(self)

      self.instanceId = instanceId
      self.name = name+' (Instance '+`instanceId`+')' # name
      self.widgetList = widgetList

      self.setWindowTitle(self.name) 

      self.updateTimer = QTimer()
      self.updateTimer.timeout.connect(self.update)
      self.updateTimer.start(defaultUpdateTimeout)

      self.rescaleTimer = QTimer()
      self.rescaleTimer.timeout.connect(self.rescale)
      self.rescaleTimer.start(defaultRescaleTimeout)

      if inactivityTimeout:
         self.killTimer = QTimer()
         self.killTimer.timeout.connect(self.inactiveTimeout)
         self.killTimer.start(defaultDeadTimeout)
      else:
         self.killTimer = None

      widgetList.append(self)
      
      self.closeEvent = self.close
      self.wheelEvent = self.changeScale
      
      self.preferredSamples = 1024

   def changeScale(self, event):
      if event.delta() > 0:
         if self.preferredSamples > 16:
            self.preferredSamples = self.preferredSamples / 2
      else:
         self.preferredSamples = self.preferredSamples * 2
      return
   
   def close(self, event):
      self.kill()
   
   def inactiveTimeout(self):
      if dspmsg.instanceActive(self.instanceId) == 0:
         self.kill()
   
   def kill(self):
      dspmsg.removeInstance(self.instanceId)
      self.wheelEvent = None
      self.closeEvent = None
      if self.killTimer is not None:
         self.killTimer.stop()
      self.rescaleTimer.stop()
      self.updateTimer.stop()
      self.widgetList.remove(self)

   def getInstanceId(self):
      return self.instanceId

   def update(self):
      return

   def rescale(self):
      return
      
class triggerDialog(DataSet):
   """Trigger Setup"""
   enabled = BoolItem("Trigger Enable")
   level = FloatItem("Trigger Level", default=0.0)

class dspCurveWidget(CurveWidget):

   def __init__(self, title, mode="PCM", color=0, show_buttons=True, show_itemlist=True, show_legend=False):
      CurveWidget.__init__(self,title=title, show_itemlist=show_itemlist)

      self.mode = mode
      self.show_legend = show_legend

      
      self.modeButton = QPushButton()
      if self.mode != 'MSCoh':
         self.modeButton.labels = {'PCM':'Freq', 'Freq':'PCM'}
         self.modeButton.setText(self.modeButton.labels[self.mode])
         self.connect(self.modeButton, SIGNAL('clicked()'), self.modeButtonPressed)

      self.itemListButton = QPushButton("Item List");
      self.connect(self.itemListButton, SIGNAL('clicked()'), self.itemListButtonPressed)

      self.triggerButton = QPushButton("Trigger");
      self.connect(self.triggerButton, SIGNAL('clicked()'), self.triggerButtonPressed)

      self.snapshotButton = QPushButton("Snapshot");
      self.connect(self.snapshotButton, SIGNAL('clicked()'), self.snapshotButtonPressed)
      
      self.spectrogramButton = QPushButton("Spectrogram");    
      self.connect(self.spectrogramButton, SIGNAL('clicked()'), self.spectrogramButtonPressed)
      
      self.PSDButton = QPushButton("PSD");    
      self.connect(self.PSDButton, SIGNAL('clicked()'), self.PSDButtonPressed)
      
      self.samples_label =QLabel("Samples")
      

      if show_buttons:
         layout = QVBoxLayout()
         self.buttonPanel = QWidget()
         self.buttonPanel.setLayout(layout)
         layout.addWidget(self.modeButton)
         layout.addWidget(self.itemListButton)
         layout.addWidget(self.triggerButton)
         layout.addWidget(self.snapshotButton)
         layout.addWidget(self.spectrogramButton)
         layout.addWidget(self.PSDButton)
         self.update_box =QLineEdit(self.buttonPanel)
         layout.addWidget(self.update_box)
         self.update_box.setEnabled(False)
         self.update_box1 =QLineEdit(self.buttonPanel)
         layout.addWidget(self.update_box1)
         self.update_box1.setEnabled(False)
         self.BriefAnalysis = QPushButton("BriefAnalysis");    
         self.connect(self.BriefAnalysis, SIGNAL('clicked()'), self.BriefAnalysisPressed)
         self.BriefAnalysis.setEnabled(False)
         self.Performance_config = QPushButton("Performance Curve");    
         self.connect(self.Performance_config, SIGNAL('clicked()'), self.Performance_configPressed)
         self.Performance_config.hide()
         self.Performance_off = QPushButton("Performance Off");    
         self.connect(self.Performance_off, SIGNAL('clicked()'), self.Performance_offPressed)
         self.Performance_off.hide()
         layout.addWidget(self.BriefAnalysis)
         layout.addWidget(self.Performance_config) 
         layout.addWidget(self.Performance_off)
         layout.addWidget(self.samples_label)
         layout.addWidget(QWidget())
         self.addWidget(self.buttonPanel) 
      
      self.plot = self.get_plot()
      self.plot.curves = []
      self.plot.refresh = True
      self.plot.snapshot = None
      self.plot.crosshairs = None
      self.matplot = None

      self.channeldata=0
      self.Highpass_plot = None
      self.Bandpass_plot = None
      self.Lowpass_plot = None
      self.Bandpass_timedomainplot= None
      self.Performance_plot =None
      self.b, self.a = signal.ellip(6,0.01,125,0.125)
      self.pascal_constant=2*10**-5
      self.sound_level_1 =[]
      self.anc_performance_curve = []
      
      self.channels = 0
      self.blockSize = 0
      self.samples = 0
      self.Fs = 0
      self.colorBase = color
      self.customCurve = None
      self.triggerCursor = None
      self.triggerEnabled = False
      self.triggerLevel = 0.0

      self.flag = False
      self.flag1= False
      self.flag2= False
      self.flag3= False
      self.flag4= False
      self.filter_range = 500
      self.filter_range1= 200
      self.Higher_cutoff = 500
      self.Lower_cutoff= 200
      self.freq =0 
      self.freqy =0
      self.Low_pass =0
      self.High_pass =0
      self.Band_pass =0
      self.cut_off_signal=0

      
      self.plot.mouseDoubleClickEvent = self.setCrossHairs
      
   def setCrossHairs(self, event):      
      x = event.pos().x() - self.plot.canvas().geometry().x()
      y = event.pos().y() - self.plot.canvas().geometry().y()
      if self.plot.crosshairs is not None:
         self.plot.crosshairs.move_local_point_to(0, QPoint(x,y))
         self.plot.crosshairs.show()

   def onclick(event):
       print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f'%(
           event.button, event.x, event.y, event.xdata, event.ydata)

   def spectrogramButtonPressed(self):
      numPlots = 0
      for curve in self.plot.curves:
         if curve.isVisible():
            numPlots = numPlots + 1
            
      if numPlots == 0:
         return

      if self.matplot:
         self.matplot.figure.clear()
      else:
         self.matplot = QWidget()
         self.matplot.figure = Figure()
         self.matplot.canvas = FigureCanvas(self.matplot.figure)
         self.matplot.canvas.setParent(self.matplot)
         vbox = QVBoxLayout()
         vbox.addWidget(self.matplot.canvas)
         self.matplot.setLayout(vbox)
         self.matplot.figure.subplots_adjust(hspace = .75, top=0.85)
         
      title = self.parent().name + ' - ' + self.plot.get_title()
      self.matplot.figure.suptitle(title, fontsize = 'x-large', weight='bold')

      plotNum = 1
      for curve in self.plot.curves:
         if curve.isVisible():
            sound_info = curve.get_data()[1]
            subplot = self.matplot.figure.add_subplot(numPlots,1,plotNum, 
               title = curve.title().text(),
               xlabel = "Seconds",
               ylabel = "Hz",
            )
            subplot.specgram(sound_info,Fs=self.Fs)
            plotNum = plotNum + 1
      
      self.matplot.show()
      self.matplot.canvas.draw()


   def PSDButtonPressed(self):
      def nextpow2(n):
         m_f = numpy.log2(n)
         m_i = numpy.ceil(m_f)
         return 2**m_i
      
      numPlots = 0
      for curve in self.plot.curves:
         if curve.isVisible():
            numPlots = numPlots + 1
            
      if numPlots == 0:
         return

      if self.matplot:
         self.matplot.figure.clear()
      else:
         self.matplot = QWidget()
         self.matplot.figure = Figure()
         self.matplot.canvas = FigureCanvas(self.matplot.figure)
         self.matplot.canvas.setParent(self.matplot)
         vbox = QVBoxLayout()
         vbox.addWidget(self.matplot.canvas)
         self.matplot.setLayout(vbox)
         self.matplot.figure.subplots_adjust(hspace = .75, top=0.85)
         
      title = self.parent().name + ' - ' + self.plot.get_title()
      self.matplot.figure.suptitle(title, fontsize = 'x-large', weight='bold')

      plotNum = 1
      for curve in self.plot.curves:
         if curve.isVisible():
            sound_info = curve.get_data()[1]
            subplot = self.matplot.figure.add_subplot(numPlots,1,plotNum, 
               title = curve.title().text(),
               xlabel = "Hz",
               ylabel = "PSD [dB]",
            )
            subplot.plot(scipy.signal.welch(sound_info,fs=self.Fs, nperseg=nextpow2(self.Fs / 2))[0],
                         10*scipy.log10(scipy.signal.welch(sound_info,fs=self.Fs, 
                                                           nperseg=nextpow2(self.Fs / 2))[1]))
            ax = self.matplot.figure.gca()
            ax.set_xticks(numpy.arange(0, 500, 50))
            subplot.grid()
            subplot.axis(xmin=0, xmax=500)
            plotNum = plotNum + 1
      
      self.matplot.show()
      self.matplot.canvas.draw()


   def snapshotButtonPressed(self):
      xlen = len(self.plot.x)
      ylen = len(self.plot.curves)
      curveData = []
      empty = True
      for curve in self.plot.curves:
         if curve.isVisible():
            try:
               cdata = curve.get_data()[1]
               data = numpy.zeros(xlen)
               x = min(xlen, cdata.shape[0])
               data[0:x] = cdata[0:x]
               curveData.append(data)
               empty = False
            except:
               continue
      
      if empty:
         return
         
      average = numpy.average(curveData, axis=0)
      if self.plot.snapshot is None:
         self.plot.snapshot = make.curve([], [], 
            color='black', 
            title='Snapshot',
            linewidth=2
            )
         self.plot.add_item(self.plot.snapshot)
         
      self.plot.snapshot.set_data(self.plot.x, average)
      
   def itemListButtonPressed(self):
      panel = self.get_itemlist_panel()
      if panel.isVisible():
         panel.hide()
      else:
         panel.show()

   def triggerUpdateLabel(self, x, y):
      label = "Trigger = %.2f" % y
      return label

   def setCrosshairLabel(self, x, y):
      label = "Point = %.2f, %2f" % (x, y)
      return label
      
   def triggerButtonPressed(self):
      if self.mode == 'Freq':
         return
         
      trigger = triggerDialog()
      trigger.enabled = self.triggerEnabled
      trigger.level = self.triggerLevel
      trigger.edit()
      self.triggerEnabled = trigger.enabled
      self.triggerLevel = trigger.level
      
      if self.triggerEnabled:
         if self.triggerCursor is None:
            self.triggerCursor = make.marker(linewidth=2,markerstyle='-')
            self.triggerCursor.label_cb = self.triggerUpdateLabel
            self.plot.add_item(self.triggerCursor)
         self.triggerCursor.set_pos(y=self.triggerLevel)
      else:
         if self.triggerCursor is not None:
            self.plot.del_item(self.triggerCursor)
            self.triggerCursor = None


   def modeButtonPressed(self):
      if self.mode == 'PCM':
         self.mode = 'Freq'
         self.BriefAnalysis.setEnabled(True)
         self.update_box.setEnabled(True)
         self.update_box1.setEnabled(True)
         self.Performance_config.show()
         self.Performance_off.show()
         self.Performance_off.setEnabled(False)
      else:
         self.mode = 'PCM'
         self.BriefAnalysis.setEnabled(False)
         self.update_box.setEnabled(False)
         self.update_box1.setEnabled(False)
         self.Performance_config.hide()
         self.Performance_off.hide()
      self.modeButton.setText(self.modeButton.labels[self.mode])
      self.plot.refresh = True

   def performance_update(self):
       if self.flag2:
             cut_off = self.update_box.text()
             self.Lower_cutoff = float(cut_off)   
             cut_off1 = self.update_box1.text()
             self.Higher_cutoff = float(cut_off1)                    
             self.Performance_plot = QWidget()
             self.Performance_plot.figure = Figure()
             self.Performance_plot.canvas = FigureCanvas(self.Performance_plot.figure)
             self.Performance_plot.canvas.setParent(self.Performance_plot)
             vbox4 = QVBoxLayout()
             vbox4.addWidget(self.Performance_plot.canvas)
             self.Performance_plot.setLayout(vbox4)
             self.Performance_plot.figure.subplots_adjust(hspace = .75, top=0.85)
             self.Performance_plot.figure.suptitle("ANC Performance Curve("+" "+ str(self.Lower_cutoff)+" "+"to"+" "+ str(self.Higher_cutoff)+"Hz) \n X axis: Frames  Y axis: dB SPL", fontsize = 'x-large')
             self.ax5 = self.Performance_plot.figure.add_subplot(111, xlabel = "Frames", ylabel = "dB SPL")
             self.ax5.grid()
             self.flag2 = False
       if self.Lower_cutoff > self.Higher_cutoff or self.Lower_cutoff == self.Higher_cutoff:
          print colored("Entered Values are not correct \nFirst Input: Lower-Cutoff Frequency \nSecond Input: Higher-Cutoff Frequency \nStop the performance Curve and Give Inputs as mentioned above" , 'red')
       else:
          if self.flag3:
             Low_cutoff, High_cutoff, F_sample = self.Lower_cutoff, self.Higher_cutoff, self.Fs
             Spectrum, Filtered_spectrum, Filtered_signal, Low_point, High_point = self.bandpass_ifft(self.channelData, Low_cutoff, High_cutoff, F_sample)
             rms = self.ac_rms(Filtered_signal.real)
             #Filtered_signal = self.bandpass(self.channelData, self.Lower_cutoff, self.Higher_cutoff)
             #pcmmax =np.max(Filtered_signal)
             loss_factor = 1
             gain = 16
             dB = (self.dB(rms)+gain)*loss_factor
             self.sound_level_1.append(dB)
             if len(self.sound_level_1) >= 300:
                self.sound_level_1.pop(0)
             self.anc_performance_curve =signal.filtfilt(self.b, self.a, self.sound_level_1, padlen=0) #filter for performance curve
             if self.Performance_plot:           
                self.ax5.clear()
                self.ax5.grid()
                self.ax5.plot(self.anc_performance_curve ,'r-')
                self.Performance_plot.show()
                self.Performance_plot.canvas.draw()
             threading.Timer(1, self.performance_update).start() #calling performance function for every one second with irrespective of other functions



   def bandpass_ifft(self, X, Low_cutoff, High_cutoff, F_sample, M=None): #a band pass filter
       if M == None: 
          M = len(X)
       Spectrum = scipy.fft(X, n=M) 
       [Low_cutoff, High_cutoff, F_sample] = map(float, [Low_cutoff, High_cutoff, F_sample])
    
       [Low_point, High_point] = map(lambda F: F/F_sample * M , [Low_cutoff, High_cutoff]) 

       Filtered_spectrum = [Spectrum[i] if i >= Low_point and i <= High_point else 0.0 for i in xrange(M)] 
       Filtered_signal = scipy.ifft(Filtered_spectrum, n=M) 
       return  Spectrum, Filtered_spectrum, Filtered_signal, Low_point, High_point 

   def lowpass_ifft(self, X, Low_cutoff, F_sample, M=None): #a band pass filter
       if M == None: 
          M = len(X)
       Spectrum = scipy.fft(X, n=M) 
       [Low_cutoff, F_sample] = map(float, [Low_cutoff, F_sample])
    
       [Low_point] = map(lambda F: F/F_sample * M , [Low_cutoff]) 

       Filtered_spectrum = [Spectrum[i] if i <= Low_point else 0.0 for i in xrange(M)] 
       Filtered_signal = scipy.ifft(Filtered_spectrum, n=M) 
       return  Spectrum, Filtered_spectrum, Filtered_signal, Low_point 
 
   def butter_highpass(self, cutoff, fs, order=6):
       nyq = 0.5 * fs
       normal_cutoff = cutoff / nyq
       b, a = scipy.signal.butter(order, normal_cutoff, btype='high', analog=False)
       return b, a

   def butter_highpass_filter(self, data, cutoff, fs, order=6):
       b, a = self.butter_highpass(cutoff, fs, order=order)
       y = scipy.signal.filtfilt(b, a, data)
       return y


   def ac_rms(self, signal):

       return self.rms_flat(signal - mean(signal))

   def rms_flat(self, a):

       return np.sqrt(np.mean(np.absolute(a)**2))

   def dB(self, level):

       return 20 * log10(self.rms_flat(level)/self.pascal_constant)
       
   def BriefAnalysisPressed(self):       
      if self.BriefAnalysis.isVisible():
           cut_off = self.update_box.text()
           self.Low_cutoff1 = float(cut_off)
           if len(self.update_box.text())>0 and len(self.update_box1.text())>0:
             self.flag =True
             cut_off1 = self.update_box1.text()
             self.High_cutoff1 = float(cut_off1)
           else:
             self.flag1=True
           if self.flag:
             if self.Low_cutoff1 > self.High_cutoff1 or self.Low_cutoff1 == self.High_cutoff1 :
                print colored("Entered Values are not correct \nFirst Input: Lower-Cutoff Frequency \nSecond Input: Higher-Cutoff Frequency \nGive Inputs as mentioned above" , 'red')
             else:
                pascal_constant=2*10**-5
                Low_cutoff, High_cutoff, F_sample = self.Low_cutoff1, self.High_cutoff1, self.Fs
                Spectrum, Filtered_spectrum, Filtered_signal, Low_point, High_point  = self.bandpass_ifft(self.channelData, Low_cutoff, High_cutoff, F_sample)
                if self.Bandpass_plot:           
                   self.Bandpass_plot.figure.clear()            
                else:
                   self.Bandpass_plot = QWidget()
                   self.Bandpass_plot.figure = Figure()
                   self.Bandpass_plot.canvas = FigureCanvas(self.Bandpass_plot.figure)
                   self.Bandpass_plot.canvas.setParent(self.Bandpass_plot)
                   vbox = QVBoxLayout()
                   vbox.addWidget(self.Bandpass_plot.canvas)
                   self.Bandpass_plot.setLayout(vbox)
                   self.Bandpass_plot.figure.subplots_adjust(hspace = .75, top=0.85)

                #calculating dB's for both low and High pass filters
                SpectrumL, Filtered_spectrumL, Filtered_signalL, Low_point = self.lowpass_ifft(self.channelData, self.Low_cutoff1 , self.Fs) 
                rmsL = self.ac_rms(Filtered_signalL.real)
                loss_factorL = 1
                gainL = 16
                dBL = (self.dB(rmsL)+gainL)*loss_factorL 
                Filtered_signalH = self.butter_highpass_filter(self.channelData, self.High_cutoff1, self.Fs, 6)
                rmsH = self.ac_rms(Filtered_signalH)
                loss_factorH = 1
                gainH = 16
                dBH = (self.dB(rmsH)+gainH)*loss_factorH
                print colored('Value Entered is '+ str(self.Low_cutoff1)+' Hz'+ ' : LowPass Filter' ,'green')
                print colored(str(dBL)+ ' dB SPL', 'green')
                print colored('Value Entered is '+ str(self.High_cutoff1)+' Hz'+ ' : HighPass Filter','green')
                print colored(str(dBH)+ ' dB SPL', 'green')   
       
                self.Band_pass= self.cut_off_signal[np.logical_and(self.plot.x < self.High_cutoff1, self.plot.x > self.Low_cutoff1)] #bandpass Zoom with rectangular windowing in frequency  domain
                self.Bandpass_plot.figure.suptitle("Band-Pass-Filter Curve("+" "+ str(self.Low_cutoff1)+" "+"to"+" "+ str(self.High_cutoff1)+"Hz)" , fontsize = 'x-large')
                self.ax2 = self.Bandpass_plot.figure.add_subplot(111, xlabel = "Frequency", ylabel = "dB")
                self.ax2.grid()
                self.freq = numpy.linspace(self.Low_cutoff1, self.High_cutoff1 , len(self.Band_pass))
                self.ax2.plot(self.freq, self.Band_pass,'r-')
                self.Bandpass_plot.show()
                self.Bandpass_plot.canvas.draw()



                if self.Bandpass_timedomainplot:           
                   self.Bandpass_timedomainplot.figure.clear()            
                else:
                   self.Bandpass_timedomainplot = QWidget()
                   self.Bandpass_timedomainplot.figure = Figure()
                   self.Bandpass_timedomainplot.canvas = FigureCanvas(self.Bandpass_timedomainplot.figure)
                   self.Bandpass_timedomainplot.canvas.setParent(self.Bandpass_timedomainplot)
                   vbox3 = QVBoxLayout()
                   vbox3.addWidget(self.Bandpass_timedomainplot.canvas)
                   self.Bandpass_timedomainplot.setLayout(vbox3)
                   self.Bandpass_timedomainplot.figure.subplots_adjust(hspace = .75, top=0.85)
                self.ax4 = self.Bandpass_timedomainplot.figure.add_subplot(111,  xlabel= "samples", ylabel = "Amplitude")
                self.ax4.grid()
                self.ax4.plot(Filtered_signal.real) #grouping real values from the spectrum between assigned points
                rms1 = self.ac_rms(Filtered_signal.real)
                loss_factor1 = 1
                gain1 = 16
                dB1 = (self.dB(rms1)+gain1)*loss_factor1
                self.Bandpass_timedomainplot.figure.suptitle("Time-Domain-Signal("+" "+ str(self.Low_cutoff1)+" "+"to"+" "+ str(self.High_cutoff1)+"Hz) \n"+ str(dB1) +" "+"dB SPL", fontsize = 'x-large' )
                self.Bandpass_timedomainplot.show()
                self.Bandpass_timedomainplot.canvas.draw()
                self.flag=False


      if self.flag1:
         if self.Lowpass_plot:           
            self.Lowpass_plot.figure.clear()            
         else:
            self.Lowpass_plot = QWidget()
            self.Lowpass_plot.figure = Figure()
            self.Lowpass_plot.canvas = FigureCanvas(self.Lowpass_plot.figure)
            self.Lowpass_plot.canvas.setParent(self.Lowpass_plot)
            vbox2 = QVBoxLayout()
            vbox2.addWidget(self.Lowpass_plot.canvas)
            self.Lowpass_plot.setLayout(vbox2)
            self.Lowpass_plot.figure.subplots_adjust(hspace = .75, top=0.85)
         self.Low_pass = self.cut_off_signal[(self.plot.x<self.Low_cutoff1)]
         self.Lowpass_plot.figure.suptitle("Low-Pass-Filter Curve Information (less than"+" "+str(self.Low_cutoff1)+"Hz)", fontsize = 'x-large') #lowpass zoom
         self.ax3 = self.Lowpass_plot.figure.add_subplot(111, xlabel = "Frequency", ylabel = "dB")
         self.ax3.grid()
         self.freqy = numpy.linspace(0, self.Low_cutoff1 , len(self.Low_pass))
         self.ax3.plot(self.freqy, self.Low_pass,'r-')
         self.Lowpass_plot.show()
         self.Lowpass_plot.canvas.draw()
         SpectrumL1, Filtered_spectrumL1, Filtered_signalL1, Low_point1 = self.lowpass_ifft(self.channelData, self.Low_cutoff1 , self.Fs)
         rmsL1 = self.ac_rms(Filtered_signalL1.real)
         loss_factorL1 = 1
         gainL1 = 16
         dBL1 = (self.dB(rmsL1)+gainL1)*loss_factorL1
         print ('Value Entered is '+ str(self.Low_cutoff1)+' Hz'+ ' : LowPass Filter')
         print (str(dBL1)+ ' dB SPL')

         if self.Highpass_plot:           
            self.Highpass_plot.figure.clear()
         else:
            self.Highpass_plot = QWidget()
            self.Highpass_plot.figure = Figure()
            self.Highpass_plot.canvas = FigureCanvas(self.Highpass_plot.figure)
            self.Highpass_plot.canvas.setParent(self.Highpass_plot)
            vbox1 = QVBoxLayout()
            vbox1.addWidget(self.Highpass_plot.canvas)
            self.Highpass_plot.setLayout(vbox1)
            self.Highpass_plot.figure.subplots_adjust(hspace = .75, top=0.85)
         self.High_pass = self.cut_off_signal[(self.plot.x>self.Low_cutoff1)] #highpass zoom
         self.Highpass_plot.figure.suptitle("High-Pass-Filter Curve Information (greater than"+" "+str(self.Low_cutoff1)+"Hz)", fontsize = 'x-large')
         self.ax1 = self.Highpass_plot.figure.add_subplot(111, xlabel = "Frequency", ylabel = "dB")
         self.ax1.grid()
         self.freqy = numpy.linspace(self.Low_cutoff1, self.plot.maxHz , len(self.High_pass))
         self.ax1.plot(self.freqy, self.High_pass,'r-')
         self.Highpass_plot.show()
         self.Highpass_plot.canvas.draw()
         Filtered_signalH1 = self.butter_highpass_filter(self.channelData, self.Low_cutoff1, self.Fs, 6)
         rmsH1 = self.ac_rms(Filtered_signalH1)
         loss_factorH1 = 1
         gainH1 = 16
         dBH1 = (self.dB(rmsH1)+gainH1)*loss_factorH1
         print ('Value Entered is '+ str(self.Low_cutoff1)+' Hz'+ ' : HighPass Filter')
         print (str(dBH1)+ ' dB SPL') 
         self.flag1=False

   def Performance_configPressed(self):
      self.Performance_off.setEnabled(True)
      self.Performance_off.setStyleSheet("background-color: red")
      self.flag2= True
      self.flag3= True
      self.flag4= True
      self.Performance_config.hide()
      print colored('Filter Configured'+ ' '+(time.ctime()),'cyan')
      print colored('FFT Started', 'cyan')
      print colored('IFFT Started', 'cyan')
      print colored('Performance Calculation Started', 'cyan')

   def Performance_offPressed(self):
      self.Performance_off.setStyleSheet("background-color: None")
      self.Performance_off.setEnabled(False)
      self.flag3= False
      self.Performance_config.show()
      del self.sound_level_1[1:]
      print colored('Filter Re-Configured'+ ' '+(time.ctime()), 'red')
      print colored('FFT Stopped' , 'red')
      print colored('IFFT Stopped' , 'red')
      print colored('Performance Calculation Stopped' , 'red')
   
   def initPlot(self, Fs, channels, blockSize, samples):
      self.Fs = Fs
      self.channels = channels
      self.blockSize = blockSize
      self.samples = samples
      colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k','G']
      self.plot.del_all_items()
      
      self.plot.curves = []
      self.plot.snapshot = None

      self.plot.crosshairs = make.marker(label_cb=self.setCrosshairLabel,markerstyle='+')
      self.plot.add_item(self.plot.crosshairs) 
      self.plot.crosshairs.hide()

      if self.show_legend:
         self.plot.legend = make.legend("TR")
         self.plot.add_item(self.plot.legend)
         
      for channel in range (0, self.channels):
         curve = make.curve([], [], 
            color=colors[(self.colorBase + channel) % len(colors)], 
            title='Channel '+`channel`,
            )
         self.plot.add_item(curve)
         self.plot.curves.append(curve)
         
   def initPcmPlot(self):
      self.plot.maxy =  1
      self.plot.miny = -1
      self.plot.set_axis_limits("left", self.plot.miny, self.plot.maxy)
      self.plot.set_axis_limits("bottom", 0, self.samples)
      self.plot.set_titles(xlabel="Sample", ylabel="Level")
      self.plot.x = numpy.linspace(0, self.samples, self.samples)
      if self.triggerEnabled:
         self.triggerCursor.show()

   def initFreqPlot(self):
      self.plot.maxy = 10
      self.plot.miny = -80
      self.plot.minHz = 0
      self.plot.maxHz = self.Fs / 2
      self.plot.set_axis_limits("left", self.plot.miny, self.plot.maxy)
      self.plot.set_axis_limits("bottom", self.plot.minHz, self.plot.maxHz)
      self.plot.set_titles(xlabel="Frequency (Hz)", ylabel="Magnitude (dB)")
      self.plot.window = numpy.kaiser(self.samples, 5)
      self.plot.noise = 0.000001 * numpy.random.sample(size=self.samples)
      self.plot.x = numpy.linspace(self.plot.minHz, self.plot.maxHz, self.samples / 2)
      if self.triggerEnabled:
         self.triggerCursor.hide()

   def initMscohPlot(self):
      self.plot.maxy = 1
      self.plot.miny = 0
      self.plot.minHz = 0
      self.plot.maxHz = self.Fs / 2
      self.plot.set_axis_limits("left", self.plot.miny, self.plot.maxy)
      self.plot.set_axis_limits("bottom", self.plot.minHz, self.plot.maxHz)
      self.plot.set_titles(xlabel="Frequency (Hz)", ylabel="|Coherence|**2")
      self.plot.x = numpy.linspace(self.plot.minHz, self.plot.maxHz, self.samples / 2)
      if self.triggerEnabled:
         self.triggerCursor.hide()

   def rescalePcmPlot(self):
      maxy = 0.0
      for curve in self.plot.curves:
         x, y = curve.get_data()
         if len(y) > 0:
            ymax = numpy.max(numpy.abs(y))
            if ymax > maxy:
               maxy = ymax
      if abs(maxy - self.plot.maxy) > 0.10 * self.plot.maxy:
         if maxy < 0.01: maxy = 0.01
         self.plot.maxy = maxy
         self.plot.miny = -maxy
         self.plot.set_axis_limits("left", self.plot.miny, self.plot.maxy)

   def rescaleFreqPlot(self):
      #self.plot.do_autoscale(replot=False)
      return
  
   def rescaleMscohPlot(self):
      self.plot.do_autoscale(replot=False)
      self.plot.maxy = 1
      self.plot.miny = 0
      self.plot.minHz = 0
      self.plot.maxHz = self.Fs / 2 
      self.plot.set_axis_limits("left", self.plot.miny, self.plot.maxy)
      self.plot.set_axis_limits("bottom", self.plot.minHz, self.plot.maxHz)
      self.plot.x = numpy.linspace(self.plot.minHz, self.plot.maxHz, self.samples)
      return
      
   def rescale(self):
      if self.mode == 'PCM': 
         self.rescalePcmPlot()
      elif self.mode == 'MSCoh':
          self.rescaleMscohPlot()
      else: 
         self.rescaleFreqPlot()
   
   def findTrigger(self, data):
      sample = None
      for x in range(0, self.samples - 1):
         if data[x] < self.triggerLevel and data[x+1] >= self.triggerLevel:
            sample = x
            break
      return sample
   
   def update_samples_text(self, new_text):
       self.samples_label.setText(new_text)
      
   def update(self, Fs, channels, blockSize, samples, data):
      if blockSize == 0 or channels == 0:
         return 
    
      self.update_samples_text(str(samples)+'   Samples')

      if ( channels != self.channels or 
           blockSize != self.blockSize or 
           samples != self.samples or
           Fs != self.Fs or
           self.plot.refresh == True
         ):
            self.initPlot(Fs, channels, blockSize, samples)
            if self.mode == 'PCM':
               self.initPcmPlot()
            elif self.mode == 'MSCoh':
                self.initMscohPlot()
            else: 
               self.initFreqPlot()
            self.plot.refresh = False

      if self.mode == 'PCM':
         self.spectrogramButton.setEnabled(True)
         self.triggerButton.setEnabled(True)
         self.PSDButton.setEnabled(True)
      else:
         self.spectrogramButton.setEnabled(False)
         self.triggerButton.setEnabled(False)
         self.PSDButton.setEnabled(False)
         
      for channel in range (0, self.channels):
         if self.customCurve != None:
            self.customCurve(self.plot, channel, data)
         else:
            self.channelData = data[channels-channel-1:blockSize*samples*channels:channels]
            if self.mode == 'PCM':
               if self.triggerEnabled:
                  trigger = self.findTrigger(self.channelData)
                  if trigger == None:
                     trigger = 0
               else: 
                  trigger = 0
               self.plot.curves[channel].set_data(self.plot.x, self.channelData[trigger:trigger+self.samples])
            elif self.mode == 'MSCoh':
                self.plot.curves[channel].set_data(self.plot.x, data)
            else:
               if len(self.channelData) > 0:
                  y = numpy.fft.fft((self.channelData+self.plot.noise)*self.plot.window) / len(self.channelData)
                  y = 20*scipy.log10(numpy.abs(y))
                  self.cut_off_signal =y.copy()
                  self.plot.curves[channel].set_data(self.plot.x, y)
                  if self.flag4:
                     self.performance_update()
                     self.flag4=False


      self.plot.replot()




