# -*- coding: utf-8 -*-
import sys
from PyQt5.QtWidgets import QPushButton,QGraphicsScene,QShortcut,QMainWindow,QVBoxLayout,QApplication,QAction,QWidget,QGraphicsView,QGraphicsPixmapItem
from PyQt5.QtGui import QIcon
from PyQt5 import QtPrintSupport
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5 import QtCore
from tkinter import *
from tkinter.filedialog import askopenfilename
from skimage.filters import threshold_local
from skimage import io as iio
import cv2
import numpy as np
import imutils
from process import FourCornerExtraction,four_point_transform

class SDialog(QWidget):
    def __init__(self, parent = None):
        super(SDialog, self).__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Convert Done!")
        self.setGeometry(500,500,300,200)
        #设定窗口标题和窗口的大小和位置。
        fontL = QtWidgets.QLabel(" Done!\n Check your photo directory")
        forma=QtGui.QFont( "Arial", 30, QtGui.QFont.Bold)
        fontL.setFont(forma)
        inputButton = QPushButton(self.tr("OK"))

        inputButton.clicked.connect(self.openInput)
        inputButton.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)
        grid = QtWidgets.QGridLayout()
        grid.addWidget(inputButton, 2, 0)
        grid.addWidget(fontL,1,0)
        self.setLayout(grid)
        #把四个按钮控件的clicked（）信号和槽连接

    def openInput(self):
        self.close()


class GripItem(QtWidgets.QGraphicsPathItem):
    circle = QtGui.QPainterPath()
    circle.addEllipse(QtCore.QRectF(-10, -10, 20, 20))
    square = QtGui.QPainterPath()
    square.addRect(QtCore.QRectF(-15, -15, 30, 30))

    def __init__(self, annotation_item, index):
        super(GripItem, self).__init__()
        self.m_annotation_item = annotation_item
        self.m_index = index

        self.setPath(GripItem.circle)
        self.setBrush(QtGui.QColor("green"))
        self.setPen(QtGui.QPen(QtGui.QColor("green"), 2))
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(11)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

    def hoverEnterEvent(self, event):
        self.setPath(GripItem.square)
        self.setBrush(QtGui.QColor("red"))
        super(GripItem, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPath(GripItem.circle)
        self.setBrush(QtGui.QColor("green"))
        super(GripItem, self).hoverLeaveEvent(event)

    def mouseReleaseEvent(self, event):
        self.setSelected(False)
        super(GripItem, self).mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange and self.isEnabled():
            self.m_annotation_item.movePoint(self.m_index, value)
        return super(GripItem, self).itemChange(change, value)


class PolygonAnnotation(QtWidgets.QGraphicsPolygonItem):
    def __init__(self, parent=None):
        super(PolygonAnnotation, self).__init__(parent)
        self.m_points = []
        self.setZValue(10)
        self.setPen(QtGui.QPen(QtGui.QColor("green"), 2))
        self.setAcceptHoverEvents(True)
        self.setBrush(QtGui.QColor(255, 0, 0, 100))
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)

        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        self.m_items = []

    def number_of_points(self):
        return len(self.m_items)

    def addPoint(self, p):
        self.m_points.append(p)
        self.setPolygon(QtGui.QPolygonF(self.m_points))
        item = GripItem(self, len(self.m_points) - 1)
        self.scene().addItem(item)
        self.m_items.append(item)
        item.setPos(p)

    def removeLastPoint(self):
        if self.m_points:
            self.m_points.pop()
            self.setPolygon(QtGui.QPolygonF(self.m_points))
            it = self.m_items.pop()
            self.scene().removeItem(it)
            del it

    def movePoint(self, i, p):
        if 0 <= i < len(self.m_points):
            self.m_points[i] = self.mapFromScene(p)
            self.setPolygon(QtGui.QPolygonF(self.m_points))

    def move_item(self, index, pos):
        if 0 <= index < len(self.m_items):
            item = self.m_items[index]
            item.setEnabled(False)
            item.setPos(pos)
            item.setEnabled(True)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            for i, point in enumerate(self.m_points):
                self.move_item(i, self.mapToScene(point))
        return super(PolygonAnnotation, self).itemChange(change, value)

    def hoverEnterEvent(self, event):
        self.setBrush(QtGui.QColor(255, 0, 0, 100))
        super(PolygonAnnotation, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        super(PolygonAnnotation, self).hoverLeaveEvent(event)

class AnnotationScene(QGraphicsScene):
    def __init__(self, parent=None):
        super(AnnotationScene, self).__init__(parent)
        self.image_item = QGraphicsPixmapItem()
        self.image_item.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
        self.image_item.setZValue(9)
        self.addItem(self.image_item)
        self.polygon_item=None


    def load_image(self, pixmap):
        self.image_item.setPixmap(pixmap)
        self.setSceneRect(self.image_item.boundingRect())

    def setCurrentInstruction(self ):
        self.polygon_item = PolygonAnnotation()
        self.addItem(self.polygon_item)


class AnnotationView(QGraphicsView):
    factor = 2.0

    def __init__(self, parent=None):
        super(AnnotationView, self).__init__(parent)
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.setMouseTracking(True)
        QShortcut(QtGui.QKeySequence.ZoomIn, self, activated=self.zoomIn)
        QShortcut(QtGui.QKeySequence.ZoomOut, self, activated=self.zoomOut)

    @QtCore.pyqtSlot()
    def zoomIn(self):
        self.zoom(AnnotationView.factor)

    @QtCore.pyqtSlot()
    def zoomOut(self):
        self.zoom(1 / AnnotationView.factor)

    def zoom(self, f):
        self.scale(f, f)
        if self.scene() is not None:
            self.centerOn(self.scene().image_item)
class App(QMainWindow):

    def __init__(self):
        super().__init__()
        self.title = 'PhotoPDF Scan !'
        self.initUI()
    def buttonevent(self):
        if self.m_scene.polygon_item is None:return
        mat=np.zeros((4,2),dtype=np.uint)
        for idx,poi in enumerate(self.m_scene.polygon_item.m_points):
            x,y=poi.x(),poi.y()
            mat[idx][0]=np.int(x)
            mat[idx][1]=np.int(y)
        warped = four_point_transform(self.orig, mat * self.ratio)
        warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        T = threshold_local(warped, 11, offset = 10, method = "gaussian")
        warped = (warped > T).astype("uint8") * 255

        from PIL import Image
        pilimg=Image.fromarray(warped)
        ls=self.file_name.split(".")
        ls.pop()
        ls.append("pdf")
        str="."
        str=str.join(ls)
        pilimg.save(str)
        pilimg.close()
        dig=SDialog()
        dig.show()
        qe = QtCore.QEventLoop()             #   line  3
        qe.exec_()                            #   line  4




    def initUI(self):
        self.setWindowTitle(self.title)
        #self.setGeometry(self.left, self.top, self.width, self.height)
        self.m_view = AnnotationView()
        self.m_scene=AnnotationScene()
        self.setGeometry(300,300,800,600)
        btn = QPushButton("Convert!")
        btn.pressed.connect( self.buttonevent )
        self.m_view.setScene(self.m_scene)
        layout = QVBoxLayout()
        
        mainMenu = self.menuBar()

        fileMenu = mainMenu.addMenu('File')

        fileButton = QAction(QIcon('load.png'), 'Load', self)
        fileButton.setShortcut('Ctrl+L')
        fileButton.setStatusTip('Load image')
        fileButton.triggered.connect(self.load_image)
        fileMenu.addAction(fileButton)

        layout.addWidget(mainMenu)
        layout.addWidget(self.m_view)
        btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed)
        layout.addWidget(btn)
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def load_image(self):
        if self.m_scene.polygon_item is not None:
            print("clear last time")
            for it in self.m_scene.polygon_item.m_items:
                self.m_scene.removeItem(it)
            self.m_scene.removeItem(self.m_scene.polygon_item)
        root = Tk()
        root.withdraw()
        root.update()

        self.file_name= askopenfilename()
        root.destroy()

        if self.file_name.split(".")[-1] not in ["jpg","jpeg","png","tif","tiff"]:
            print("Please check your image format")
            return
        ori_img = iio.imread(self.file_name)
        self.ratio = ori_img.shape[0] / 500.0
        self.orig = ori_img.copy()
        image = imutils.resize(ori_img, height = 500)
        #image=cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        qformat=QtGui.QImage.Format_RGB888
        display_img = QtGui.QImage(image.data,
            image.shape[1],
            image.shape[0],
            image.strides[0],
            qformat)
        pixmap = QtGui.QPixmap.fromImage(display_img)
        self.m_scene.load_image(pixmap)
        self.m_view.fitInView(self.m_scene.image_item, QtCore.Qt.KeepAspectRatio)
        self.m_view.centerOn(self.m_scene.image_item)

        ret=FourCornerExtraction(image)
        if ret is None:
            print("Can not detect a paper!")
            return
        ret=ret.reshape(4,2)
        self.m_scene.setCurrentInstruction()
        for i in range(4):
            p=QtCore.QPointF(ret[i][0],ret[i][1])

            self.m_scene.polygon_item.addPoint(p)









    


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.resize(800,600)
    ex.show()
    sys.exit(app.exec_())