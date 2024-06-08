import pvrhino
import pvporcupine
from pvrhino import Rhino, Inference
from pvrecorder import PvRecorder
from dotenv import load_dotenv
import os
import time
import RPi.GPIO as GPIO

load_dotenv()

ACCESS_KEY = os.getenv("ACCESS_KEY")
CONTEXT_FILE_PATH_RHINO = os.getenv("CONTEXT_FILE_PATH_RHINO")
CONTEXT_FILE_PATH_PORCUPINE = os.getenv("CONTEXT_FILE_PATH_PORCUPINE")

availableLocations = {
	'bathroom': {
		'label': 'Red',
		'pin': 11,
	},
	'closet': {
		'label': 'Blue',
		'pin': 10,
	},
	'pantry': {
		'label': 'Green',
		'pin': 9,
	},
}

def ledSetUp():
	# declare pin standard
	GPIO.setmode(GPIO.BCM)
	# set pin mode for GPIO pins to OUTPUT
	for led in availableLocations.values():
		pin = led['pin']
		print(f"[!] led: {led['label']}, pin: {pin}")
		GPIO.setup(pin, GPIO.OUT)

def switchAllLights(state):
	print(f"[!] turning all lights {state}")
	value = GPIO.HIGH if state == "on" else GPIO.LOW
	for led in availableLocations.values():
                pin = led['pin']
                GPIO.output(pin, value)

def switchLightsInLocation(location, state):
	print(f"[!] turning {state} the lights in the {location}")
	if location in availableLocations:
		GPIO.output(availableLocations[location]['pin'], GPIO.HIGH if state == "on" else GPIO.LOW)

class Watchdog():
	def __init__(self, timeout=10):
	        self.timeout = timeout
	        self._t = None
	def _expire(self):
	        print("[!] Watchdog expired")
	        raise TimeoutError
	def check(self):
		if time.time() - self._t >= self.timeout:
			self._expire()
	def start(self):
		if self._t is None:
	        	self._t = time.time()
	def stop(self):
	    	if self._t is not None:
	        	self._t = None
	def refresh(self):
		if self._t is not None:
			self.stop()
			self.start()



def wakeUp(porcupine, audio_frame):
	keyword_index = porcupine.process(audio_frame)
	if keyword_index == 0:
		# detected 'Jarvis'
		return True
	return False
	
	
def executeCommands(rhino, recorder):
	watch_dog = Watchdog()
	watch_dog.start()
	try:
		while True:
			audio_frame = recorder.read()
			is_finalized = rhino.process(audio_frame)

			if is_finalized:
				inference = rhino.get_inference()

				if not inference.is_understood:
					print("Sorry, didn't understand the command")
					continue
				else:
					watch_dog.refresh()
					if "location" in inference.slots and "state" in inference.slots:
						switchLightsInLocation(inference.slots['location'], inference.slots['state'])
					elif "state" in inference.slots:
						 switchAllLights(inference.slots['state'])
			watch_dog.check()
	except TimeoutError:
		print("[!] stopped listening ...")
		print("[!] Say wakeup word to start listening again")
		return

def main():
	# Initialize LEDs
	ledSetUp()

	# Initialize AI models

	porcupine = pvporcupine.create(
		access_key=ACCESS_KEY,
		keyword_paths=[CONTEXT_FILE_PATH_PORCUPINE]
	)
	rhino = pvrhino.create(
		access_key=ACCESS_KEY,
		context_path=CONTEXT_FILE_PATH_RHINO
	)

	# Initialize and start recorder

	recorder = PvRecorder(frame_length=rhino.frame_length)
	recorder.get_available_devices()
	print(f"[!] selected device to record: {recorder.selected_device}")
	recorder.start()

	try:
		while True:
			audio_frame = recorder.read()
			if wakeUp(porcupine, audio_frame):
				print("[!] Listening for commands ... ")
				executeCommands(rhino, recorder)
		    

	except KeyboardInterrupt:
		print('[!] Ending process ...')
	finally:
		# cleaning process
		rhino.delete()
		porcupine.delete()
		recorder.delete()
		GPIO.cleanup()


if __name__ == "__main__":
    main()
