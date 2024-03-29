'''
MAVUE v0.1 (beta)
Graphical inspector for MAVLink enabled embedded systems.

Copyright (c) 2009-2014, Felix Schill
All rights reserved.
Refer to the file LICENSE.TXT which should be included in all distributions of this project.
'''


from PyQt5 import Qt, QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import *
import math
import sys
import traceback
from importlib import *
import json
from guifw.abstractparameters import  *
from PIL import Image
import numpy as np
import gc

class HorizontalBar(QWidget):
    def __init__(self,  parent=None):
        QWidget.__init__( self, parent=parent)
        self.items=[]
        self.layout=QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)


    def add(self,  widget,  signal,  action):
        self.layout.addWidget(widget)
        self.items.append(widget)
        getattr(widget, signal).connect(action)

class CommandButton(QtWidgets.QPushButton):
    def __init__(self, name="", width=None, height=None,  callback=None,  callback_argument=None):
        QtWidgets.QPushButton.__init__(self, name)
        if height is not None:
            self.setFixedHeight(height)
        if width is not None:
            self.setFixedWidth(width)
        self.clicked.connect(self.clickedHandler)
        self.callback=callback
        self.callback_argument=callback_argument
        self.setContentsMargins(0,0,0,0)

    def updateFromParameter(self, parameter):
        pass

    def clickedHandler(self):
        if self.callback is not None:
            self.callback(self.callback_argument)


class PlainComboField(QComboBox):
    def __init__(self, parent=None,  label="", value=None,  choices=None,  onOpenCallback=None):
        QtWidgets.QComboBox.__init__( self, parent=parent)
        self.choices = choices
        self.onOpenCallback = onOpenCallback
        if not value in choices:
            self.choices.append(value)
        for t in choices:
            self.addItem(str(t))
        if value!=None:
            self.setCurrentIndex(list(self.choices).index(value))
        self.combo=self

    def updateFromParameter(self, parameter):
        if parameter!=None:
            self.combo.setCurrentIndex(self.choices.index(parameter.getValue()))

    def updateValue(self,  value):
        if value!=None:
            self.combo.setCurrentIndex(self.choices.index(value))

    def showPopup(self):
        if self.onOpenCallback!=None:
            self.onOpenCallback()
        QtWidgets.QComboBox.showPopup(self)

    def updateChoices(self,  choices):
        changed=False
        for mc,nc in zip(self.choices,  choices):
            if mc != nc:
                changed=  True
        if not changed:
            return
        self.clear()

        self.choices = choices
        for t in choices:
            self.addItem(t)



class LabeledComboField(QWidget):
    def __init__(self, parent=None,  label="", value=None,  choices=None):
        QWidget.__init__( self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.label=QtWidgets.QLabel(parent=self, text=label)
        self.layout.addWidget(self.label)
        self.combo=QtWidgets.QComboBox(parent=self)
        self.choices = choices
        self.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)
        for t in choices:
            self.combo.addItem(t)
        if value!=None and value in choices:
            self.combo.setCurrentIndex(choices.index(value))
        self.layout.addWidget(self.combo)

    def updateFromParameter(self, parameter):
        if parameter!=None:
            self.updateChoices(parameter.getChoiceStrings())
            self.updateValue(parameter.getValueString())

    def updateValue(self,  value):
        if value!=None:
            self.combo.setCurrentIndex(self.choices.index(value))

    def updateChoices(self, choices):
        changed = False
        for mc, nc in zip(self.choices, choices):
            if mc != nc:
                changed = True
        if not changed:
            return

        self.choices = choices
        self.combo.clear()

        for t in choices:
            self.combo.addItem(t)

class LabeledTextField(QWidget):
    def __init__(self, parent=None, editable=True,  label="", value=None,  formatString="{:s}"):
        QWidget.__init__( self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.formatString=formatString
        self.editable=editable
        self.label=QtWidgets.QLabel(parent=self, text=label)
        self.layout.addWidget(self.label)
        self.text=QtWidgets.QLineEdit(parent=self)
        self.text.setReadOnly(not self.editable)
        self.text.returnPressed.connect(self.textEditedHandler)
        self.edited_callback=None
        self.edited_callback_argument=self

        self.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        if value!=None:
            self.text.setText(formatString.format(value))
        self.layout.addWidget(self.text)

    def updateFromParameter(self, parameter):
        if parameter!=None:
            self.updateValue(parameter.getValue())

    def updateValue(self,  value=None):
        if value!=None:
            # check if value is a multi-value object:
            if isinstance(value, (list,  frozenset,  tuple,  set,  bytearray)):
                self.text.setText(''.join(self.formatString.format(x) for x in value))
            else:
                self.text.setText(self.formatString.format(value))

    def textEditedHandler(self):
        if self.edited_callback is not None:
            self.edited_callback(self.edited_callback_argument)

    def closeEvent(self, ev):
        self.edited_callback=None
        self.label.close()
        self.text.close()


class LabeledProgressField(QWidget):
    def __init__(self, parent=None,  label="", value=None, min=None,  max=None,  step=1.0):
        QWidget.__init__( self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.label=QtWidgets.QLabel(parent=self, text=label)
        self.layout.addWidget(self.label)
        self.progress=QtWidgets.QProgressBar(parent=self)
        self.updateValue(value=value,  min=min,  max=max)
        self.layout.addWidget(self.progress)

    def updateFromParameter(self, parameter):
        if parameter!=None:
            self.updateValue(parameter.getValue(),  parameter.min,  parameter.max)

    def updateValue(self,  value,  min,  max):
        self.progress.setMinimum(min)
        self.progress.setMaximum(max)
        self.progress.setValue(value)


class LabeledCheckboxField(QWidget):
    def __init__(self, parent=None,  label="", value=False,  editable = True):
        QWidget.__init__( self, parent=parent)
        self.editable = editable
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.checkbox=QtWidgets.QCheckBox(parent=self, text = label)

        self.layout.addWidget(self.checkbox)
        self.updateValue(value=value)

    def updateFromParameter(self, parameter):
        if parameter!=None:
            self.updateValue(parameter.getValue())

    def updateValue(self,  value):
        self.checkbox.setChecked(value)

class LabeledFileField(QWidget):
    def __init__(self, parent=None, editable=True,  label="", value=None, type="open",  fileSelectionPattern="All files (*.*)"):
        QWidget.__init__( self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.type = type
        self.setLayout(self.layout)
        self.fileSelectionPattern=fileSelectionPattern
        self.editable=editable
        self.label=QtWidgets.QLabel(parent=self, text=label)
        self.layout.addWidget(self.label)
        self.text=QtWidgets.QLineEdit( parent=self)
        self.text.setReadOnly(not self.editable)
        if value!=None:
            self.text.setText(formatString.format(value))
        self.layout.addWidget(self.text)

        self.fileDialogButton=QtWidgets.QPushButton(parent=self, text= "Select...")
        self.fileDialogButton.clicked.connect(self.showDialog)
        self.layout.addWidget(self.fileDialogButton)

    def updateFromParameter(self, parameter):
        if parameter!=None:
            self.updateValue(parameter.getValue())

    def updateValue(self,  value):
        if value!=None:
            self.text.setText(value)

    def showDialog(self):
        filename = None
        if self.type == "open":
            filename=QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', '',  self.fileSelectionPattern)
        if self.type == "save":
            filename=QtWidgets.QFileDialog.getSaveFileName(self, 'Save file', '',  self.fileSelectionPattern)

        print (filename)
        if filename!=None and len(filename[0])>0:
            self.updateValue(filename[0])

class LabeledNumberField(QWidget):
    def __init__(self, parent=None,  label="", min=None,  max=None,  value=0,  step=0.001,  slider=False, editable = True):
        QWidget.__init__( self, parent=parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.editable = editable
        self.setLayout(self.layout)
        self.label=QtWidgets.QLabel(parent=self, text=label)
        self.layout.addWidget(self.label)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.step = step # used for slider scaling
        decimals = 1
        if self.step==0:
            self.step = 0.001 # set default if zero is given to avoid issues
        else:
            decimals = round(math.log(1.0 / step) / math.log(10.0))

        self.number = None
        
        if step==1.0:
            self.number = QtWidgets.QDoubleSpinBox(parent=self, decimals=decimals)
            #self.number = QtWidgets.QSpinBox(parent=self)
            if min != None:
                self.number.setMinimum(int(min))
            else:
                self.number.setMinimum(-10000000)
            if max!=None:
                self.number.setMaximum(int(max))
            else:
                self.number.setMaximum(10000000)
            self.number.setSingleStep(int(step));

        else:
            self.number = QtWidgets.QDoubleSpinBox(parent=self, decimals=decimals)
            if min != None:
                self.number.setMinimum(min)
            else:
                self.number.setMinimum(-10000000)
            if max!=None:
                self.number.setMaximum(max)
            else:
                self.number.setMaximum(10000000)
            
            self.number.setSingleStep(step);

        try:
            self.number.setValue(value)
        except:
            pass
        self.layout.addWidget(self.number)
        self.number.valueChanged.connect(self.spinboxChanged)
        self.number.setKeyboardTracking(False)
        self.number.setReadOnly(not self.editable)
        if slider:
            self.sliderLayout = QtWidgets.QVBoxLayout()
            self.sliderLayout.setSpacing(0)
            self.sliderLayout.setContentsMargins(0, 0, 0, 0)
            self.sliderWidget = QtWidgets.QWidget()
            self.slider = QtWidgets.QSlider(parent = self, orientation=QtCore.Qt.Horizontal)
            
            if step>=1.0:
                if min != None:
                    self.slider.setMinimum(int(min/self.step))
                if max != None:
                    self.slider.setMaximum(int(max/self.step))
                self.slider.setValue(int(value/self.step))
            else:
                if min != None:
                    self.slider.setMinimum(min/self.step)
                if max != None:
                    self.slider.setMaximum(max/self.step)
                self.slider.setValue(value/self.step)
            
            self.slider.valueChanged.connect(self.sliderChanged)
            labelednumber_widget = QtWidgets.QWidget(parent=self)
            labelednumber_widget.setLayout(self.layout)
            self.sliderLayout.addWidget(labelednumber_widget)
            self.sliderLayout.addWidget(self.slider)
            self.setLayout(self.sliderLayout)
            labelednumber_widget.setContentsMargins(0, 0, 0, 0)

        else:
            self.slider = None
            self.setLayout(self.layout)

    def closeEvent(self, ev):
        self.label.close()
        self.number.close()
        if self.slider is not None:
            self.slider.close()

    def sliderChanged(self):
        self.number.setValue(self.slider.value()*self.step)

    def spinboxChanged(self):
        if self.slider is not None:
            self.slider.blockSignals(True)
            self.slider.setValue(int(self.number.value()/self.step))
            self.slider.blockSignals(False)

    def updateFromParameter(self, parameter):
        if parameter != None:
            self.updateValue(parameter.getValue())

    def updateValue(self,  value):
        self.number.setValue(value)
        if self.slider is not None:
            self.slider.setValue(value/self.step)

class ClickableLabel(QLabel):
    clicked = QtCore.pyqtSignal()

    def __init__(self, **kwargs):
        QLabel.__init__(self, **kwargs)

    def mousePressEvent(self, ev):
        self.clicked.emit()


class ScrollImageView(QtWidgets.QGraphicsView):
    def __init__(self, parent=None, image=None, name=""):
        QtWidgets.QGraphicsView.__init__(self, parent=parent)
        self.image=image
        h, w, ch = self.image.shape
        bytesPerLine = ch * w
        qimage = QtGui.QImage(self.image.data, w, h, bytesPerLine, QtGui.QImage.Format_RGB888)
        self.pixmap = QtGui.QPixmap(qimage)

        self.scene = QGraphicsScene(parent=self)
        self.scene.addPixmap(self.pixmap)
        self.setScene(self.scene)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.zoom=1
        self.setWindowTitle(name)
        self.show()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom *= 1.25
        else:
            self.zoom *= 0.80
        h, w, ch = self.image.shape
        m = self.transform()
        m.reset()
        m.scale(self.zoom, self.zoom)
        self.setTransform(m)

class LabeledImageField(QWidget):
    def __init__(self, parent=None, label="", image = None, height = 100):
        QWidget.__init__(self, parent=parent)

        self.image = None
        self.labelText=label
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.image_label = ClickableLabel(parent=self, text="no image")
        self.image_label.setFixedHeight(height)
        self.image_label.clicked.connect(self.showLarge)
        self.layout.addWidget(self.image_label)
        self.label = QtWidgets.QLabel(parent=self, text=label)
        self.layout.addWidget(self.label)
        self.height = height
        self.image_label.resize(self.height, self.height)
        self.loadImage(image)


    def loadImage(self, image):
        if isinstance(image, str):
            print("loading ", image)
            try:
                self.image = np.asarray(Image.open(image))
            except:
                self.image = None
        else:
            self.image = image

        if self.image is not None:
            h, w, ch = self.image.shape
            bytesPerLine = ch * w
            qimage = QtGui.QImage(  self.image.data, w, h, bytesPerLine, QtGui.QImage.Format_RGB888)
            pixmap = QtGui.QPixmap(qimage)
            pixmap = pixmap.scaled(self.height*w/h, self.height, QtCore.Qt.KeepAspectRatio)
            self.image_label.setPixmap(pixmap)

    def showLarge(self):
        print("showLarge")
        if self.image is not None:
            self.scroll = ScrollImageView(parent=None, image=self.image, name=self.labelText)
            self.scroll.show()


    def updateFromParameter(self, parameter):
        self.labelText=parameter.name
        self.label.setText(self.labelText)
        self.loadImage(parameter.getValue())

    def updateValue(self,  value):
        self.loadImage(value)

    def closeEvent(self, ev):
        self.image = None
        self.image_label.close()
        self.image_label=None
        self.label.close()
        self.label=None

def parameterWidgetFactory(object, parent = None):
    w = None
    if object.__class__.__name__ == "TextParameter":
        w = LabeledTextField(parent=parent, label=object.name, editable=object.editable, formatString=object.formatString)

        w.updateValue(object.value)
        if object.editable:
            w.text.textChanged.connect(object.updateValueOnly)
            w.text.editingFinished.connect(object.commitValue)

    if object.__class__.__name__ == "FileParameter":
        w = LabeledFileField(parent=parent, label=object.name, editable=object.editable, type = object.type, fileSelectionPattern=object.fileSelectionPattern)
        w.updateValue(object.value)
        if object.editable:
            w.text.textChanged.connect(object.updateValue)

    if object.__class__.__name__ == "CheckboxParameter":
        w = LabeledCheckboxField(parent=parent, label=object.name, value=object.getValue(), editable=object.editable)
        w.checkbox.stateChanged.connect(object.updateValue)

    if object.__class__.__name__ == "NumericalParameter":
        w = LabeledNumberField(parent=parent, label=object.name, min=object.min, max=object.max, value=object.getValue(), step=object.step, slider = object.slider, editable=object.editable)

        if object.editable:
            w.number.valueChanged.connect(object.updateValueQT)

    if object.__class__.__name__ == "DateParameter":
        w = LabeledTextField(parent=parent, label=object.name, editable=object.editable, formatString="{:s}")
        w.updateValue(str(object.value))
        #if object.editable:
        #    w.text.textChanged.connect(object.updateValueOnly)
        #    w.text.editingFinished.connect(object.commitValue)

    if object.__class__.__name__ == "ProgressParameter":
        w = LabeledProgressField(parent=parent, label=object.name, min=object.min, max=object.max, value=object.getValue())

    if object.__class__.__name__ == "ChoiceParameter":
        w = LabeledComboField(parent=parent, label=object.name, value=object.getValueString(),
                              choices=object.getChoiceStrings())
        if object.editable:
            w.combo.currentIndexChanged.connect(
                object.updateValueByIndex)

    if object.__class__.__name__ == "ActionParameter":
        w = QtWidgets.QPushButton(parent = parent, text=object.name)
        w.clicked.connect(object.callback)
        w.updateFromParameter=None

    if object.__class__.__name__ == "ImageViewer":
        w = LabeledImageField(parent=parent, label = object.name, image = object.getValue(), height = object.height)

    object.viewRefresh = w.updateFromParameter
    return w

class ToolPropertyWidget(QWidget):
    def updateParameter(self,  object=None,  newValue=None):
        object.updateValue(newValue)

    def __init__(self, parent,  tool):
        QWidget.__init__( self, parent=parent)

        self.scroll = QtWidgets.QScrollArea(parent=self)

        self.scroll.setWidgetResizable(True)
        self.outer_layout = QtWidgets.QVBoxLayout(self)
        self.outer_layout.addWidget(self.scroll)

        self.scroll.setVerticalScrollBarPolicy(Qt.Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.Qt.ScrollBarAsNeeded)

        self.scrollcontent = QtWidgets.QWidget(self.scroll)
        self.layout = QtWidgets.QVBoxLayout(self.scrollcontent)
        self.scrollcontent.setLayout(self.layout)
        self.scroll.setWidget(self.scrollcontent)


        self.parameters=dict()
        self.addToolWidgets(self.layout,  tool.parameters)
        self.layout.addStretch()

    def addToolWidgets(self,  layout,  widgetlist):

        # get editable parameters
        for object in widgetlist:
            p=object

            w = None
            if isinstance(object, (list)):
                horizontal_widget = QWidget()
                horizontal_layout = QtWidgets.QHBoxLayout()
                horizontal_widget.setLayout(horizontal_layout)
                self.addToolWidgets(horizontal_layout, object)
                layout.addWidget(horizontal_widget)
            else:
                w = parameterWidgetFactory(object, parent = self)
                self.parameters[p] = w
                layout.addWidget(w)

            if w is not None:
                self.parameters[p] = w

        #layout.setMargin(0);
        layout.setSpacing(0);
        #layout.addStretch()

    def closeEvent(self, ev):
        for p in self.parameters.keys():
            p.viewRefresh = None
            self.parameters[p].close()
        self.parameters.clear()
        self.scroll.close()
        self.scroll = None
        self.scrollcontent.close()
        self.scrollcontent=None

class ItemListModel(QtCore.QAbstractListModel):
    def __init__(self, itemlist, parent=None, *args):

        QtCore.QAbstractListModel.__init__(self, parent, *args)
        self.listdata = itemlist

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.listdata)

    def data(self, index, role):
        if not (index.isValid()  and index.row()<len(self.listdata)):
            return None
        if self.listdata[index.row()] is None:
            return QtCore.QVariant()
        if role == QtCore.Qt.DisplayRole:
            return self.listdata[index.row()].name.value
        if role == QtCore.Qt.CheckStateRole:
            if len(self.listdata)>0 and self.listdata[index.row()].selected:
                return QtCore.Qt.Checked
            else:
                return QtCore.Qt.Unchecked
        return QtCore.QVariant()

    def isChecked(self,  index):
        if len(self.listdata)>0 and self.listdata[index].selected:
            return True
        else:
            return False

    def setData(self, index, value, role):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                eindex=-1
                for i in range(0,  len(self.listdata)):
                    if self.listdata[i] is not None and self.listdata[i].name.value==str(value):
                        eindex=i
                if eindex>=0:
                    self.listdata[index.row()] = self.listdata[eindex]
            if role == QtCore.Qt.CheckStateRole:
                if index.row()<len(self.listdata):
                    self.listdata[index.row()].selected=(not self.listdata[index.row()].selected)
                    self.dataChanged.emit(index, index)
                    return True
        return False

    def addItem(self,  newItem):
        self.beginInsertRows(QtCore.QModelIndex(),  self.rowCount(),
                             self.rowCount()+1)
        self.listdata.append(newItem)
        self.endInsertRows()
        return self.index(self.rowCount()-1)


    def removeRows(self,  row,  count,  parent):
        self.beginRemoveRows(QtCore.QModelIndex(),  self.rowCount(),  self.rowCount()+1)
        for i in reversed(range(row,  row+count)):
            if i<len(self.listdata):
                del self.listdata[i]
        self.endRemoveRows()
        return True

    def insertRows(self, row, count, parent=QtCore.QModelIndex()):
        if parent.isValid(): return False

        beginRow=max(0,row)
        endRow=min(row+count-1,len(self.listdata))

        self.beginInsertRows(parent, beginRow, endRow)

        for i in range(beginRow, endRow+1): self.listdata.insert(i,None)

        self.endInsertRows()
        return True

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | \
               QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsDragEnabled

        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | \
               QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsEnabled

    def supportedDragActions(self):
        return QtCore.Qt.MoveAction

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

class ListWidget(QSplitter):
    def __init__(self, parent=None,  title="",  itemlist=[],  itemclass=None,  on_select_cb=None, addItems=True,  removeItems=True, name_generator=None, forceUniqueNames = True,  **creationArgs):
        QSplitter.__init__( self, QtCore.Qt.Horizontal, parent=parent)
        self.creationArgs=creationArgs
        self.name_generator = name_generator
        self.forceUniqueNames = forceUniqueNames

        self.on_select_cb=on_select_cb
        ## Create a grid layout to manage the widgets size and position
        self.leftSide = QWidget()

        self.layout = QtWidgets.QGridLayout()
        self.leftSide.setLayout(self.layout)
        self.addWidget(self.leftSide)

        self.rightSide=QWidget()
        self.rightLayout = QtWidgets.QGridLayout()
        self.rightSide.setLayout(self.rightLayout)
        self.addWidget(self.rightSide)

        self.listmodel=ItemListModel(itemlist)
        self.itemclass=itemclass
        self.listw = QtWidgets.QListView()
        self.listw.setModel(self.listmodel)
        self.listw.setDragDropMode(self.listw.InternalMove)
        self.listw.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.listw.setDragDropOverwriteMode(False)
        self.listw.setDragEnabled(True);
        self.listw.setAcceptDrops(True);
        self.listw.setDropIndicatorShown(True);
        self.listw.clicked.connect(self.respondToSelect)
        self.listw.selectionModel().currentChanged.connect(self.respondToSelect)
        self.layout.addWidget(QtWidgets.QLabel(title), 0, 0)   # button goes in upper-left
        self.layout.addWidget(self.listw, 1, 0)  # list widget goes in bottom-left
        self.propertyWidget = None

        self.listw.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listw.customContextMenuRequested.connect(self.contextMenuEvent)

        if addItems or removeItems:
            buttonwidget=QWidget()
            buttonLayout=QtWidgets.QHBoxLayout()
            buttonwidget.setLayout(buttonLayout)

            if addItems:
                if isinstance(itemclass,  dict):
                    self.widgetSelect = PlainComboField(parent=self,  value = list(itemclass.keys())[0],
                                                                                   label='Widgets',  choices=itemclass.keys())
                    buttonLayout.addWidget(self.widgetSelect)
                self.addBtn = QtWidgets.QPushButton('+')
                self.addBtn.setFixedWidth(30)
                buttonLayout.addWidget(self.addBtn)
                self.addBtn.clicked.connect(self.addItem)
            if removeItems:
                self.removeBtn = QtWidgets.QPushButton('-')
                self.removeBtn.setFixedWidth(30)
                buttonLayout.addWidget(self.removeBtn)
                self.removeBtn.clicked.connect(self.removeItem)

            self.save_btn = QtWidgets.QPushButton("Sv")
            self.save_btn.clicked.connect(self.saveTasks)
            self.save_btn.setFixedWidth(30)
            self.load_btn = QtWidgets.QPushButton("Ld")
            self.load_btn.setFixedWidth(30)
            self.load_btn.clicked.connect(self.loadTasks)
            buttonLayout.addWidget(self.save_btn)
            buttonLayout.addWidget(self.load_btn)
            self.layout.addWidget(buttonwidget, 2, 0)  # button goes in upper-left

            self.searchField = QtWidgets.QLineEdit()
            self.searchField.returnPressed.connect(self.searchItem)
            buttonLayout.addWidget(self.searchField)

        if len(itemlist)>0:
            self.selectedTool=itemlist[0]
        else:
            self.selectedTool=None

        if self.selectedTool!=None:
            self.propertyWidget=ToolPropertyWidget(parent=self, tool=self.selectedTool)
            #self.layout.addWidget(self.propertyWidget, 0, 1,  3,  1)
            self.rightLayout.addWidget(self.propertyWidget, 0, 0)

        self.setStretchFactor(1, 1)
        self.setSizes([200, 4000])


    def searchItem(self):
        searchText = self.searchField.text()
        try: # see if it's just a number
            searchText = self.name_generator(list(self.itemclass.keys())[self.widgetSelect.currentIndex()], int(self.searchField.text()))
        except:
            pass

        print("searching for", searchText)
        foundItem = self.findItem( name = searchText)

        if foundItem is not None:
            foundIndex = self.getItems().index(foundItem)
            qmi = self.listmodel.createIndex(foundIndex, 0)
            self.listw.selectionModel().setCurrentIndex(qmi, QtCore.QItemSelectionModel.SelectCurrent)
            self.respondToSelect(foundIndex)
        else:
            newItem = self.addItem(name = searchText)

    def respondToSelect(self,  index):
        s_index=self.listw.currentIndex()
        self.selectedTool=self.listmodel.listdata[s_index.row()]
        print("selected ",s_index.row())
        if self.selectedTool!=None:
            if self.propertyWidget is not None:
                self.layout.removeWidget(self.propertyWidget)
                self.propertyWidget.close()
                gc.collect()

            self.propertyWidget=ToolPropertyWidget(parent=self, tool=self.selectedTool)
            self.rightLayout.addWidget(self.propertyWidget, 0, 0)
            if self.on_select_cb!=None:
                self.on_select_cb(self.selectedTool)

    def getCheckedItems(self):
        checkedItems = []
        for index in range(self.listw.model().rowCount()):
            if self.listw.model().isChecked(index):
                checkedItems.append(self.listmodel.listdata[index])
        return checkedItems

    def getItems(self):
        return [i for i in self.listmodel.listdata]


    ## context menu handlers
    def contextMenuEvent(self, pos):
        if self.listw.selectionModel().selection().indexes():
            for i in self.listw.selectionModel().selection().indexes():
                row, column = i.row(), i.column()
            menu = QtWidgets.QMenu()
            filterAction = menu.addAction("duplicate")
            clearAction = menu.addAction("delete")

            action = menu.exec_(self.mapToGlobal(pos))

            if action == filterAction:
                selectedTool = self.listmodel.listdata[row]
                print("duplicate", row, selectedTool)
                args = {i: self.creationArgs[i] for i in self.creationArgs if i != "name"}
                newItem = type(selectedTool)(name = selectedTool.name.getValue(), **args)
                counter = 1
                newName = newItem.name.value
                while newName in [i.name.value for i in self.listmodel.listdata]:
                    newName = "%s - %i" % (newItem.name.value, counter)
                    counter += 1
                newItem.name.updateValue(newName)
                newItem.restoreParametersFromDict(selectedTool.toDict()["parameters"])
                self.listmodel.addItem(newItem)

            if action == clearAction:
                print("delete")


    def addItem(self,  dummy=None, addExistingItems=True,  **creationArgs):
        if len(creationArgs) == 0:
            creationArgs = {key: value for key, value in self.creationArgs.items()}

        if isinstance(self.itemclass,  dict):
            index = self.widgetSelect.currentIndex()
            itemToCreate = list(self.itemclass.values())[index]
            print(creationArgs)
            if (not "name" in creationArgs) or creationArgs["name"] is None:
                creationArgs["name"] = list(self.itemclass.keys())[index]

        else:
            itemToCreate = self.itemclass

        print("reloading module ", itemToCreate.__module__)
        #reload(sys.modules[itemToCreate.__module__])
        itemToCreate = getattr(sys.modules[itemToCreate.__module__], itemToCreate.__name__)

        try:
            newItem=itemToCreate(name_generator = self.name_generator, **creationArgs)
            newName=newItem.name.value
            nameExists=False
            foundItem=None
            for item in self.listmodel.listdata:
                if item is not None and item.name.value==newName:
                    nameExists=True
                    foundItem=item
                    self.respondToSelect(foundItem)
                    print ("found" , newName, addExistingItems)
                    break

            if not nameExists or (nameExists and addExistingItems):
                counter=1
                while self.forceUniqueNames and (newName in [i.name.value for i in self.listmodel.listdata]):
                    newName="%s - %i"%(newItem.name.value,  counter)
                    counter+=1
                newItem.name.updateValue(newName)
                # add to list model
                addedItem=self.listmodel.addItem(newItem)
                self.listw.setCurrentIndex(addedItem)
                self.respondToSelect(addedItem)
                print (newName)
                return newItem
            else:
                return foundItem
        except Exception as e:
            print(e)
            traceback.print_exc()
        return None

    def findItem(self,  name):
        for item in self.listmodel.listdata:
            if name==item.name.value:
                return item
        return None

    def removeItem(self):
        if self.propertyWidget is not None:
            self.layout.removeWidget(self.propertyWidget)
            self.propertyWidget.close()

        itemindex=self.listw.selectedIndexes()
        if len(itemindex)==0:
            return
        self.listmodel.removeRows(itemindex[0].row(),  1,  itemindex[0])


    def saveTasks(self):
        filename, pattern = QtWidgets.QFileDialog.getSaveFileName(self, 'Save file', '', "*.json")
        if len(filename)==0:
            return

        print("saving File:", filename)

        items = self.getItems()
        exportedItems = [i.toDict() for i in items]
        print(exportedItems)
        jdata = json.dumps(exportedItems)
        with open(filename, "w") as file:
            file.write(jdata)

    def loadTasks(self):
        filename, pattern = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', '', "*.json")
        if len(filename)==0:
            return

        data = None
        with open(filename) as file:
            data = file.read()
        importedData = json.loads(data)

        classDict = {}
        for name, c in self.itemclass.items():
            print(name, str(c.__name__), c)
            classDict[str(c.__name__)] = c
        print(classDict)

        for i in importedData:
            args = {i:self.creationArgs[i] for i in self.creationArgs if i!="name"}
            item = buildItemFromDict(i, classDict) (name = i["name"], **args)
            item.restoreParametersFromDict(i["parameters"])
            print(item)

            
            originalName = item.name.value
            counter = 1
            while self.forceUniqueNames and self.findItem(item.name.value) is not None: 
                item.name.value = "%s - %i"%(originalName,  counter)
                counter+=1
                print("duplicate task name, changing to ", item.name.value)
            self.listmodel.addItem(item)
