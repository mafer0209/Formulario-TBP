import sys
import time
import csv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QLineEdit, QRadioButton, QFormLayout, QInputDialog
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QGridLayout
from PyQt5.QtCore import QTimer, Qt
from PIDctrl4 import controlador
import pyfirmata2
from pyfirmata2 import PWM
from PIL import Image
from PyQt5.QtGui import QPixmap
import os

class RealTimeGraphApp(QMainWindow):
    def __init__(self): 
        super().__init__()
       
        self.graph_filename = 'graph.png'  # Nombre del archivo de gráfica
        self.csv_filename = 'data.csv' 
           
        self.setWindowTitle("SISTEMA TBP")
        self.setGeometry(100, 100, 500, 700)

        # Inicializar layout
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        self.layout = QVBoxLayout(main_widget)

        self.initUI()
        self.initArduino()
        self.initGraph()
        

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateGraph)
        self.tempo = 5000 #tiempo de ejecucion mS
        self.timer.start(self.tempo) #tiempo de actualizacion

        self.show()

        # Agregar botón para guardar datos en CSV
        self.save_button = QPushButton("Guardar datos en CSV")
        self.save_button.clicked.connect(self.saveDataToCSV)
        self.layout.addWidget(self.save_button)

        # Botón para abrir ventana emergente de configuración
        self.config_button = QPushButton("Configuración")
        self.config_button.clicked.connect(self.openConfigDialog)
        self.layout.addWidget(self.config_button)

        # Cargar configuración desde archivo
        self.loadConfig()

    def initUI(self):
        layout = QGridLayout()       
        form_layout = QFormLayout()

        self.mode_label = QLabel("Modo: Manual")
        form_layout.addRow(self.mode_label)
        self.mode_radio_auto = QRadioButton("Auto")
        self.mode_radio_auto.toggled.connect(lambda: self.changeMode("auto"))
        form_layout.addRow(self.mode_radio_auto)
        self.mode_radio_manual = QRadioButton("Manual")
        self.mode_radio_manual.toggled.connect(lambda: self.changeMode("manual"))
        form_layout.addRow(self.mode_radio_manual)
        self.op_label = QLabel("OP: 0.0")
        form_layout.addRow(self.op_label)
        self.op_input = QLineEdit()
        self.op_input.setPlaceholderText("Ingrese %OP (0-100)")
        self.op_input.setMaximumWidth(512)
        form_layout.addRow(self.op_input)
        self.setpoint_label = QLabel("Setpoint: 10.0")
        form_layout.addRow(self.setpoint_label)
        self.setpoint_input = QLineEdit()
        self.setpoint_input.setPlaceholderText("Ingresar Setpoint")
        self.setpoint_input.setMaximumWidth(512)
        form_layout.addRow(self.setpoint_input)

        self.op_input.setDisabled(True)  # Deshabilitar el campo de %OP por defecto
        self.setpoint_input.setDisabled(True)  # Deshabilitar el campo de Setpoint por defecto
    
        layout.addLayout(form_layout, 0, 0)  # Cuadros de texto en la columna 0
        self.time_label = QLabel("Tiempo: 0")  # Etiqueta para mostrar el tiempo
        form_layout.addRow(self.time_label)

        self.temperature_label = QLabel("Temperatura: 0.0 °C")  # Etiqueta para mostrar la temperatura
        form_layout.addRow(self.temperature_label)
        # Botones en la parte izquierda
        button_layout = QVBoxLayout()

        self.start_button = QPushButton("Enviar")
        self.start_button.clicked.connect(self.startControl)
        self.start_button.setFixedWidth(256)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Parar programa")
        self.stop_button.clicked.connect(self.stopControl)
        self.stop_button.setFixedWidth(256)
        button_layout.addWidget(self.stop_button)

        self.config_button = QPushButton("Configuración")
        self.config_button.clicked.connect(self.openConfigDialog)
        self.config_button.setFixedWidth(256)
        button_layout.addWidget(self.config_button)

        layout.addLayout(button_layout, 1, 0)  # Botones en la columna 1

        self.console_label = QLabel("Mensajes de consola")
        layout.addWidget(self.console_label, 2, 1)  # Mensajes de consola en la columna 0
        self.console_output = QLabel()
        layout.addWidget(self.console_output, 1, 1, 1, 2)
        

        self.graph_label = QLabel("Grafica en tiempo real:")
        form_layout.addRow(self.graph_label)

        # Agregar la creación del QLabel para mostrar la imagen del gráfico
        self.graph_image = QLabel()
        layout.addWidget(self.graph_image, 0, 1, 1, 3)  # Para mostrar la imagen del gráfico

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        


    def openConfigDialog(self):
        config_dialog = QDialog(self)
        config_dialog.setWindowTitle("Configuración")
        config_dialog.setGeometry(200, 200, 300, 150)

        layout = QFormLayout()

        kp_input = QLineEdit()
        Ti_input = QLineEdit()
        Td_input = QLineEdit()
        mm_input = QLineEdit()  
        ord_input = QLineEdit() 

        kp_input.setText(str(self.kp))
        Ti_input.setText(str(self.Ti))
        Td_input.setText(str(self.Td))
        mm_input.setText(str(self.mm))  # Establecer el valor actual de mm
        ord_input.setText(str(self.ord))

        layout.addRow("Valor de Kp:", kp_input)
        layout.addRow("Valor de Ti:", Ti_input)
        layout.addRow("Valor de Td:", Td_input)
        layout.addRow("Introducir pendiente:", mm_input)  # Etiqueta y cuadro de texto para mm
        layout.addRow("Introducir ordenada al origen:", ord_input)

        save_button = QPushButton("Guardar")
        save_button.clicked.connect(config_dialog.accept)

        layout.addRow(save_button)

        config_dialog.setLayout(layout)

        result = config_dialog.exec_()

        if result == QDialog.Accepted:
            self.kp = float(kp_input.text())
            self.Ti = float(Ti_input.text())
            self.Td = float(Td_input.text())
            self.mm = float(mm_input.text())  # Actualizar el valor de mm
            self.ord = float(ord_input.text())
            self.updateConsole("Configuración actualizada")
            self.saveConfig()

    def saveConfig(self):
        with open('config.txt', 'w') as config_file:
            config_file.write(f'Kp={self.kp}\n')
            config_file.write(f'Ti={self.Ti}\n')
            config_file.write(f'Td={self.Td}\n')
            config_file.write(f'pendiente={self.mm}\n')
            config_file.write(f'Ordenada al origen={self.ord}\n')

    def loadConfig(self):
        try:
            with open('config.txt', 'r') as config_file:
                for line in config_file:
                    key, value = line.strip().split('=')
                    if key == 'Kp':
                        self.kp = float(value)
                    elif key == 'Ti':
                        self.Ti = float(value)
                    elif key == 'Td':
                        self.Td = float(value)
                    elif key == 'pendiente':
                        self.mm = float(value)  # Cargar el valor de mm
                    elif key == 'Ordenada al origen':
                        self.ord = float(value)
        except FileNotFoundError:
            #VAlores por defecto
            self.kp = 0.4
            self.Ti = 2560
            self.Td = 0.0
            self.mm = 474.91  
            self.ord = -103.25

    def initArduino(self):
        self.DELAY = 0.5
        self.board = pyfirmata2.Arduino(pyfirmata2.Arduino.AUTODETECT)
        self.board.sp.baudrate = 57600
        print(self.board)
        
        self.board.samplingOn(5) #milisegundos
        time.sleep(self.DELAY)
        self.AnPin=self.board.analog[1]
        self.AnPin.enable_reporting()        
        self.pwmpin = self.board.get_pin(f'd:{9}:p')
        self.pwmpin.mode = PWM
        self.FanPin = self.board.digital[2]

    def initGraph(self):
        plt.ion()
        self.fig, self.ax = plt.subplots()
        self.line1, = self.ax.plot([], label='Temperatura PV')
        self.line2, = self.ax.plot([], label='Setpoint')
        self.ax.set_xlabel('Tiempo')
        self.ax.set_ylabel('Temperatura', color='tab:blue')
        self.ax.legend(loc='upper left')
        self.ax2 = self.ax.twinx()
        self.line3, = self.ax2.plot([], color='tab:red', label='OP')
        self.ax2.set_ylabel('Porcentaje OP', color='tab:red')
        self.ax2.legend(loc='upper right')
        self.PV_data = []
        self.OP_data = []
        self.SP_data = []
        self.tiempo = 0
        self.tiempo_data = []
        self.mode = 'manual'
        self.loadConfig() #con este metodo se cargan kp,ti,td,mm, ord
        #self.mm = 474.91
        #self.ord = -103.25
        self.tmax = self.mm + self.ord
        self.PID_crtl = controlador(self.kp, self.Ti, self.Td, self.tmax)
        self.op_max = self.PID_crtl.compute(self.ord, 1)
        self.op_min = 0
        self.rang_op = self.op_max - self.op_min
        self.SetPoint_PV = 10.0
        self.SetPointManual = 0
        self.PV = 0
        self.OP = 0
        self.last_N_PV_values = []
        self.PID_crtl = controlador(self.kp, self.Ti, self.Td, self.SetPoint_PV)

    def changeMode(self, mode):
        if mode == "auto":
            self.mode_label.setText("Modo: Auto")
            self.op_input.setDisabled(True)
            self.setpoint_input.setDisabled(False)
        else:
            self.mode_label.setText("Modo: Manual")
            self.op_input.setDisabled(False)
            self.setpoint_input.setDisabled(True)
            self.setpoint_input.setText(str(self.SetPointManual))
        self.mode = mode

    def startControl(self):
        if self.mode == "auto":
            setpoint = float(self.setpoint_input.text())
            if self.ord <= setpoint <= self.tmax:
                self.SetPoint_PV = setpoint
                self.PID_crtl.update_parameters(self.SetPoint_PV, self.kp, self.Ti, self.Td)
                self.setpoint_label.setText(f"Setpoint: {setpoint}")
            else:
                self.updateConsole("Setpoint debe estar entre {self.ord} y {self.tmax}.")
        elif self.mode == "manual":
            op = float(self.op_input.text())
            if 0 <= op <= 100:
                self.OP = op
                Nr = op / 100
                self.pwmpin.write(Nr)
                self.SetPointManual = self.SetPoint_PV
                self.op_label.setText(f"OP: {op}")
            else:
                self.updateConsole("OP debe estar en un rango entre 0 y 100.")
            if op < 5:
                self.FanPin.write(1)
            else:
                self.FanPin.write(0)



    def updateGraph(self):
        muestras=[]
        
        for _ in range(100):
            # Leer el pin analógico y agregar la muestra a la lista
            muestra = self.AnPin.read()
            muestras.append(muestra)
            if len(muestras) > 100:
                muestras.pop(0)
        #Promedio de las muestras
        prom_muestras= sum(muestras)/len(muestras)        
        self.PV = (prom_muestras * (self.tmax - self.ord)) + self.ord
        self.tiempo += (self.tempo/1000)
        
        if self.mode == 'auto':
            self.OP = self.PID_crtl.compute(self.PV, self.tiempo)
            salida_pwm = (self.OP - self.op_min) / self.rang_op
            self.pwmpin.write(max(0, min(salida_pwm, 1)))
            #print(f"salida pwm",salida_pwm)
            if (salida_pwm*100) < 10:
                self.FanPin.write(1)
            else:
                self.FanPin.write(0)
            
        self.last_N_PV_values.append(self.PV)
        
        if len(self.last_N_PV_values) > 50:
            self.last_N_PV_values.pop(0)
            
        PV_average = sum(self.last_N_PV_values) / len(self.last_N_PV_values)
        self.PV_data.append(PV_average)
        self.OP_data.append(self.OP)
        self.SP_data.append(self.SetPoint_PV)
        self.tiempo_data.append(self.tiempo)
        self.line1.set_data(self.tiempo_data, self.PV_data)
        self.line2.set_data(self.tiempo_data, self.SP_data)
        self.line3.set_data(self.tiempo_data, self.OP_data)
        self.ax.relim()
        self.ax.autoscale_view()
        self.ax2.relim()
        self.ax2.autoscale_view()
        self.fig.canvas.flush_events()
        self.showGraphImage()

        # Actualiza el valor de la etiqueta de tiempo
        self.time_label.setText(f"Tiempo: {self.tiempo}")

        # Actualiza el valor de la etiqueta de temperatura
        self.temperature_label.setText(f"Temperatura: {self.PV:.2f} °C")
        # Guardar automáticamente los datos en un archivo CSV
        self.saveDataToCSV()

    def showGraphImage(self):
        if self.graph_filename:
            self.fig.canvas.draw()
            buf = self.fig.canvas.buffer_rgba()
            width, height = self.fig.canvas.get_width_height()
            img = Image.frombytes('RGBA', (width, height), buf)
            img.save(self.graph_filename, "PNG")
            pixmap = QPixmap(self.graph_filename)
            self.graph_image.setPixmap(pixmap)
            self.graph_image.setAlignment(Qt.AlignCenter)

    def updateConsole(self, message):
        self.console_output.setText(message)

    def stopControl(self):
        self.timer.stop()
        self.updateConsole("Programa detenido")
        self.updateConsole("enfriando sistema...")
        self.FanPin.write(1)
         # Guardar los datos cuando se presiona el botón para detener el programa
        self.saveDataToCSV()
    
    def saveDataToCSV(self):
        data = zip(self.tiempo_data, self.OP_data, self.PV_data, self.SP_data)
        with open(self.csv_filename, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['Tiempo', 'Porcentaje OP', 'Temperatura(PV_average)', 'Setpoint'])
            writer.writerows(data)
        self.updateConsole(f"Datos guardados en {self.csv_filename}")

        # Llama a showGraphImage sin argumentos
        self.showGraphImage()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RealTimeGraphApp()
    sys.exit(app.exec_())
