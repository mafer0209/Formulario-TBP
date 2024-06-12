#LA idea es crear un controlador PID cuyas ganancias estén en unidades reales, por
#Ejemplo °C/%OP para ganancia y que cuando este controlador sea llamado por el programa principal
#Sea este el que realice la normalizacion de la salida a través de pyfirmata2
class controlador:
    def __init__(self, kp, Ti, Td, setpoint):

        self.kp = kp  # Constante proporcional
        self.Ti = Ti  # Tiempo integral
        self.Td = Td  # Tiempo derivativo
        self.setpoint = setpoint  # Valor de referencia
        
        self.error_prev = 0
        self.integral = 0
        self.time_prev = None

    def compute(self, PV, time):
        PV1=[]   

        PV1.append(PV)
        if len(PV1) > 50:
            PV1.pop(0)
        PV1_prom=sum(PV1)/len(PV1) #filtro por promedio de PV

         #Calcular el eror   
        error = self.setpoint - PV1_prom
        
        error_percent = error #se usa error normal no porcentaje

        # Calcular el tiempo transcurrido desde la iteración anterior
        if self.time_prev is None:
            delta_time = 0.0
        else:
            delta_time = time - self.time_prev

        # Calcular el cambio en el error respecto al tiempo
        if delta_time > 0:
            delta_error = error_percent - self.error_prev
        else:
            delta_error = 0.0

        # Término proporcional
        proportional_term = self.kp * error_percent
        
        # Término integral
        #Integral por suma de Riemman
        self.integral += error_percent * delta_time   
        
        integral_term = (self.kp/self.Ti) * self.integral
        
        

        # Término derivativo usando el cambio en el error respecto al tiempo
        derivative_term = self.kp*self.Td*((delta_error)/(delta_time+1))

        # PID salida        
        OP = proportional_term + integral_term + derivative_term
        #anti wind-up
        if OP > 100:
            OP = 95
        elif OP < 0:
            OP = 0  

        # Actualizar el error previo y el tiempo para la siguiente iteración
        
                
        self.error_prev = error_percent
        self.integral = self.integral
        self.time_prev = time
        
        print(f"Kp,Ti,Td {self.kp,self.Ti,self.Td}")
        print(f"PID,OP {proportional_term,integral_term,derivative_term},{OP}")
        print(f"tiempo {time}")
        print(f"integral error,porcentaje error,delta time{self.integral, error_percent, delta_time}") 

        return OP
    
    def update_parameters(self, setpoint=None, kp=None, Ti=None, Td=None):
        if kp is not None:
            self.kp = kp
        if Ti is not None:
            self.Ti = Ti
        if Td is not None:
            self.Td = Td
        if setpoint is not None:
            self.setpoint = setpoint