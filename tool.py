#!/usr/bin/python

import dspmsg
from dspwidgets import dspPcmWidget, dspTrainWidget, dspAncWidget, dspMscohWidget, dspwidget

import signal
import random

import guidata

from guidata.qt.QtGui import QWidget, QPushButton, QVBoxLayout, QCheckBox, QLabel
from guidata.qt.QtCore import QTimer, QCoreApplication, SIGNAL

signal.signal(signal.SIGINT, signal.SIG_DFL)

activeWidgets = []

displayWidgets = [ 
   { 'name':'sin', 'widget':dspPcmWidget, 'dataFunc':dspmsg.getSine },
   { 'name':'nse', 'widget':dspPcmWidget, 'dataFunc':dspmsg.getNoise },
   { 'name':'dcb', 'widget':dspPcmWidget, 'dataFunc':dspmsg.getDcb },
   { 'name':'bpf', 'widget':dspPcmWidget, 'dataFunc':dspmsg.getBpf },
   { 'name':'ths', 'widget':dspPcmWidget, 'dataFunc':dspmsg.getThs },
   { 'name':'anc', 'widget':dspAncWidget, 'dataFunc':dspmsg.getAnc },
   { 'name':'trn', 'widget':dspTrainWidget, 'dataFunc':dspmsg.getTrain },
   { 'name':'snk', 'widget':dspPcmWidget, 'dataFunc':dspmsg.getSnk },
#   { 'name':'anc', 'widget':dspMscohWidget, 'dataFunc':dspmsg.getAnc },
]

class controlWidget(QWidget):    
   def __init__(self, parent):
      super(controlWidget, self).__init__()

      self.widgetTimer = QTimer()
      self.widgetTimer.start(100)
      self.widgetTimer.timeout.connect(self.createNewDspWidgets)
      self.value =0
      self.flag = True
      
      self.mainApp = parent
      self.inactivityTimeout = True

      self.setWindowTitle('Live Telemetry Visualizer')

      self.qbtn = QPushButton('Quit', self)
      self.qbtn.clicked.connect(self.mainApp.quit)
      self.qbtn.resize(self.qbtn.sizeHint())
      self.qbtn.hide()

      qbtn1 = QPushButton('Check Performance status')
      qbtn1.clicked.connect(self.ButtonPressed)
      qbtn1.resize(qbtn1.sizeHint())

      self.performance_status = QLabel("If Performance Curve at Monitor Mic is On turn it Off")
      self.performance_status.hide()

      
      icheck = QCheckBox('Inactivity Timeout')
      icheck.stateChanged.connect(self.toggleInactivity)
      icheck.setChecked(self.inactivityTimeout)

      layout = QVBoxLayout()
      self.setLayout(layout)
      layout.addWidget(self.qbtn)
      layout.addWidget(self.performance_status)
      layout.addWidget(qbtn1)
      layout.addWidget(icheck)
      layout.addWidget(QWidget())

      self.resize(180, 100)
      self.show()
         
   def toggleInactivity(self, state):
      self.inactivityTimeout = (state != 0)
   
   def ButtonPressed(self):
       self.performance_status.setStyleSheet("background-color: red")
       self.performance_status.show()
       self.qbtn.show()
      
   def placeWidget(self, desktop, widget, placedwidget):
      screenNum = desktop.screenNumber(self)
      screen = desktop.screenGeometry(screenNum)
      size = widget.geometry()
      left = screen.width()-size.width()     
      if left < 0:
         left = 0
      top = screen.height()-size.height()
      if top < 0:
         top = 0;
      #left = random.randint(0, left) + screen.left()
      #top = random.randint(0, left) + screen.top()
      if placedwidget=='anc' or 'trn':
         left = 2
         top = 2
         widget.move(left, top)
      if placedwidget=='snk':
         left = 920
         top = 900
         widget.move(left, top)
      return
   
   def createNewDspWidgets(self):
      for displayWidget in displayWidgets:
         instances = dspmsg.getInstances(displayWidget['name'])
         for instance in instances['instances']:
            found = False
            for widget in activeWidgets:
               if widget.getInstanceId() == instance:
                  found = True
                  break         
            if found == False:
               widget = displayWidget['widget'](
                  displayWidget['name'],
                  instance, 
                  activeWidgets,
                  displayWidget['dataFunc'],
                  inactivityTimeout = self.inactivityTimeout
               )
               placedwidget=displayWidget['name']
               #if self.flag:
                #  self.value = instance
                 # self.flag = False
               self.placeWidget(self.mainApp.desktop(), widget, placedwidget)
               widget.show()



def main():
   global app
   app = guidata.qapplication()
   app.control = controlWidget(app)
   app.exec_()


if __name__ == '__main__':
    main()
