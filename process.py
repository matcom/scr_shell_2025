import os
import signal
import time


# Crear un proceso hijo usando os.fork()
def create_process():
    pid = os.fork()

    if pid == 0:
        # Código del proceso hijo
        print(f"Soy el hijo (PID: {os.getpid()}), mi padre es PID: {os.getppid()}")
        os._exit(0)  # Termina el hijo
    else:
        # Código del proceso padre
        print(f"Soy el padre (PID: {os.getpid()}), hijo creado con PID: {pid}")


create_process()


# El padre espera a que el hijo termine usando os.wait()
def wait_for_child():
    pid = os.fork()

    if pid == 0:
        print(f"Hijo (PID: {os.getpid()}): Durmiendo 3 segundos...")
        time.sleep(3)
        os._exit(42)  # Código de salida 42
    else:
        print(f"Padre (PID: {os.getpid()}): Esperando al hijo...")
        child_pid, exit_code = os.wait()
        print(f"Hijo {child_pid} terminó con código: {exit_code >> 8}")


wait_for_child()


# Envía una señal **`SIGTERM`** o **`SIGKILL`** al hijo.
def destroy_process():
    pid = os.fork()

    if pid == 0:
        print(f"Hijo (PID: {os.getpid()}): Ejecutando tarea infinita...")
        while True:
            time.sleep(1)
    else:
        print(f"Padre (PID: {os.getpid()}): Terminando al hijo en 2 segundos...")
        time.sleep(2)
        os.kill(pid, signal.SIGTERM)  # Envía SIGTERM (elegante)
        # os.kill(pid, signal.SIGKILL)  # Fuerza terminación (SIGKILL)
        print("¡Hijo terminado!")


# Usar os.waitpid() con opciones para consultar el estado sin bloquear.


def check_status():
    pid = os.fork()

    if pid == 0:
        print(f"Hijo (PID: {os.getpid()}): Trabajando...")
        time.sleep(2)
        os._exit(0)
    else:
        while True:
            try:
                # WNOHANG: No bloquea, retorna inmediatamente
                child_pid, status = os.waitpid(pid, os.WNOHANG)
                if child_pid == 0:
                    print(f"Padre: Hijo aún en ejecución (PID: {pid})")
                else:
                    print(f"Padre: Hijo terminó con estado {status}")
                    break
                time.sleep(1)
            except OSError:
                print("Error: Proceso hijo no existe")
                break


# Envía **`SIGSTOP`** (pausar) y **`SIGCONT`** (reanudar).


def pause_process():
    pid = os.fork()

    if pid == 0:
        print(f"Hijo (PID: {os.getpid()}): Contando...")
        for i in range(1, 6):
            print(i)
            time.sleep(1)
        os._exit(0)
    else:
        time.sleep(2)
        print("\nPadre: Pausando al hijo...")
        os.kill(pid, signal.SIGSTOP)  # Pausa

        time.sleep(3)
        print("Padre: Reanudando al hijo...")
        os.kill(pid, signal.SIGCONT)  # Reanuda

        os.wait()  # Espera a que el hijo termine


### **Diagrama de Estados del Proceso con `fork()`**
# [*] --> Padre
# Padre --> Hijo: fork()
# Hijo --> Ejecutando
# Ejecutando --> Terminado: _exit()
# Ejecutando --> Pausado: SIGSTOP
# Pausado --> Ejecutando: SIGCONT

# ### **Consideraciones Clave**
# 1. **`fork()` solo en Unix/Linux**: No funciona en Windows (usa `multiprocessing` en su lugar).
# 2. **Recursos compartidos**: El hijo hereda una copia del espacio de memoria del padre.
# 3. **Zombies**: Si el padre no llama a `wait()`, el hijo queda en estado zombie hasta que el padre termine.
# 4. **Señales comunes**:
#    - `SIGTERM`: Terminación elegante (puede ser capturada).
#    - `SIGKILL`: Terminación forzosa (no puede ignorarse).
#    - `SIGSTOP`/`SIGCONT`: Pausar/reanudar.
