#import tkinter as tk


'''
window = tk.Tk()
window.title("My First Window")
#window.geometry("400x300")

window.focus_force()

screen_w = window.winfo_screenwidth()
screen_h = window.winfo_screenheight()
x = (screen_w // 2) - (400 // 2)
y = (screen_h // 2) - (300 // 2)
window.geometry(f"400x300+{x}+{y}")

window.mainloop()
'''

from vosk import Model, KaldiRecognizer
import sounddevice as sd
import queue
import json

q = queue.Queue()

model = Model("/Users/brandonmccurdy/Documents/Code Projects/vosk-model-small-en-us-0.15")
samplerate = 16000
rec = KaldiRecognizer(model, samplerate)

def callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(bytes(indata))

with sd.RawInputStream(samplerate=samplerate, blocksize=8000, dtype='int16',
                       channels=1, callback=callback):
    print("Listening... Speak into your microphone.")
    while True:
        data = q.get()
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            print("You said:", result.get("text", ""))