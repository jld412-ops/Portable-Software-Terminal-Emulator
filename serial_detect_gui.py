#Raspberry PI Portable Software Terminal Emulator by Jenierre Domingo
import subprocess
import os
from datetime import datetime
import serial
import time
import tkinter as tk
from tkinter import messagebox

#PORT = "/dev/ttyUSB0
BAUD = 9600 #Temporary loopback for GPIO Serial Ports

UNITS = {"2162": {"baud": 9600, "data_bits": 8, "parity": "N", "stop_bits": 1, "flow": "N"},
	 "2455": {"baud": 115200, "data_bits": 8, "parity": "N", "stop_bits": 1, "flow": "N"},
	 "2509": {"baud": 115200, "data_bits": 8, "parity": "N", "stop_bits": 1, "flow": "N"},
	 "2561": {"baud": 57600, "data_bits": 8, "parity": "N", "stop_bits": 1, "flow": "N"}, }

current_unit = None
putty_process = None
USE_USB_MODE = False
PORT = "/dev/serial0"
USB_PORT = "/dev/ttyUSB0"

def serial_loopback_detected():
	try:
		ser = serial.Serial(PORT, baudrate=BAUD, timeout=1)
		time.sleep(0.2)

		test_msg = b"PING\n"
		ser.write(test_msg)
		time.sleep(0.2)

		received = ser.readline()
		ser.close()

		return received == test_msg

	except Exception as e:
		print("Serial error:", e)
		return False

def clear_screen():
	for widget in root.winfo_children():
		widget.destroy()


def serial_connection_active():
	if USE_USB_MODE:
		return os.path.exists(USB_PORT)

	return serial_loopback_detected()

serial_was_connected = serial_connection_active()
disconnect_popup_shown = False

def monitor_serial_connection():
	global serial_was_connected, putty_process
	#GPIO LOOPBACK MODE, Don't test the serial port while PuTTY owns it
	if not USE_USB_MODE:
		if putty_process is not None and putty_process.poll() is None:
			root.after(3000, monitor_serial_connection)
			return

	connected = serial_connection_active()

	if not connected and serial_was_connected:
		serial_was_connected = False

		if putty_process is not None and putty_process.poll() is None:
			putty_process.terminate()
			putty_process = None

		root.lift()
		root.attributes("-topmost", True)
		root.update()
		messagebox.showwarning("Serial Disconnected", "Serial disconnected.\n\nReconnect serial cable.")
		root.attributes("-topmost", False)
		show_no_connection_screen()

	elif connected and not serial_was_connected:
		serial_was_connected = True
		root.lift()
		root.attributes("-topmost", True)
		root.update()

		messagebox.showinfo("Serial Connection Detected", f"Serial connection detected on {PORT}.")
		root.attributes("-topmost", False)
		show_unit_buttons()

	root.after(3000, monitor_serial_connection)

def choose_unit(unit):
	global current_unit
	current_unit = unit
	settings = UNITS[unit]

	clear_screen()
	
	tk.Label(root, text=f"Selected Unit: {unit}", font=("Arial", 26)).pack(pady=30)

	tk.Label(root, text=f"Port: {PORT}\nBaud: {settings['baud']}", font=("Arial", 18)).pack(pady=20)

	tk.Button(root, text="Start DSP Session", font=("Arial", 22), width=18, height=2, command=start_session).pack(pady=15)

	tk.Button(root, text="Switch Unit", font=("Arial", 22), width=18, height=2, command=show_unit_buttons).pack(pady=15)

	tk.Checkbutton(root, text="Save DSP report to txt file", variable=save_log_var, font=("Arial",18)).pack(pady=10)

	tk.Label(root, text="Report File Name:", font=("Arial",16)).pack(pady=5)

	tk.Entry(root, textvariable=filename_var, font=("Arial",18), width=30).pack(pady=10)

	filename_var.set(f"{unit}_DSP_Report")

def show_no_connection_screen():
	clear_screen()
	tk.Label(root, text="No serial connection detected", font=("Arial",24)).pack(pady=60)

	tk.Button(root, text="Retry", font=("Arial",22), width=15, height=2, command=retry_connection).pack(pady=20)

def retry_connection():
	global serial_was_connected

	if serial_connection_active():
		serial_was_connected = True

		messagebox.showinfo("Serial Connection Detected", f"Serial connection detected on {PORT}.")
		show_unit_buttons()
	else:
		serial_was_connected = False
		messagebox.showwarning("No Serial Connection", "No serial connection detected.\n\nPlease check the cable and try again.")
		show_no_connection_screen()

def show_unit_buttons():
	clear_screen()

	tk.Label(root, text="Select Unit", font=("Arial", 24)).pack(pady=30)

	for unit in UNITS:
		tk.Button(root, text=unit, font=("Arial", 22), width=15, height=2, command=lambda u=unit: choose_unit(u)).pack(pady=8)

def start_session():
	if current_unit is None:
		messagebox.showerror("Error", "No unit selected.")
		return

	settings = UNITS[current_unit]
	#Prompts DSP Session Process for USer
	messagebox.showinfo("Starting Session", f"Starting DSP session for {current_unit}\n\n"
		f"Unit: {current_unit}\n"
		f"Port: {PORT}\n"
		f"Baud Rate: {settings['baud']}\n"
		f"Data Bits: {settings['data_bits']}\n"
		f"Parity: {settings['parity']}\n"
		f"Stop Bits: {settings['stop_bits']}\n\n"

		f"Launching PuTTY...")

	print(f"Starting DSP session for {current_unit}")
	print(f"Using {PORT} at {UNITS[current_unit]['baud']} baud")

	serial_config = (
		f"{settings['baud']},"
		f"{settings['data_bits']},"
		f"{settings['parity']},"
		f"{settings['stop_bits']},"
		f"{settings['flow']}"
	)

	putty_command = [
		"putty",
		"-serial", PORT,
		"-sercfg", serial_config
	]

	if save_log_var.get():
		os.makedirs("reports", exist_ok=True)
		user_filename = filename_var.get().strip()
		if user_filename == "":
			timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
			user_filename = f"{current_unit}_DSP_Report_{timestamp}"
		if not user_filename.endswith(".txt"):
			user_filename += ".txt"

		log_file = f"reports/{user_filename}"
		putty_command.extend(["-sessionlog", log_file])
		print(f"Saving PuTTY log to: {log_file}")

	print(f"Launching PuTTY for {current_unit}")
	print(" ".join(putty_command))

	try:
		global putty_process
		putty_process = subprocess.Popen(putty_command)
	except Exception as e:
		messagebox.showerror("PuTTY Launch Error", str(e))

root = tk.Tk()
root.title("Portable DSP Emulator")
root.geometry("800x480")

save_log_var = tk.BooleanVar(value=True)
filename_var = tk.StringVar(value="")

print("Checking serial connection on /dev/serial0...")

if serial_connection_active():
	serial_was_connected = True
	root.lift()
	root.attributes("-topmost",True)
	root.update()
	messagebox.showinfo("Serial Connection Detected", f"Serial connection detected on {PORT}.")
	root.attributes("-topmost", False)
	show_unit_buttons()
else:
	serial_was_connected = False
	show_no_connection_screen()

root.after(3000, monitor_serial_connection)
root.mainloop()

