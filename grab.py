import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import pyaudio
import wave
import threading
import numpy as np
import PyPDF2
from docx import Document

class AudioStudioFinalTouch:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Audio Studio - Edición Profesional")
        self.root.geometry("1150x750")
        self.root.configure(bg="#0a0a0a")

        # Configuración de Audio
        self.chunk, self.format, self.channels, self.rate = 1024, pyaudio.paInt16, 1, 44100
        self.p = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = False
        self.is_paused = False
        self.current_volume = 0
        
        # Lógica de Reproducción (Evitar múltiples sonidos)
        self.audio_thread = None
        self.stop_playback = False
        
        # Variables de Zoom
        self.zoom_level = 50
        self.selection_start = None
        self.selection_end = None

        self.setup_ui()
        self.main_loop()

    def setup_ui(self):
        # --- SIDEBAR ---
        sidebar = tk.Frame(self.root, bg="#151515", padx=20, pady=10)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(sidebar, text="MICRÓFONO", bg="#151515", fg="#888", font=("Arial", 8, "bold")).pack(anchor=tk.W)
        self.device_combo = ttk.Combobox(sidebar, values=self.get_devices(), width=30, state="readonly")
        self.device_combo.current(0)
        self.device_combo.pack(pady=(5, 15))

        self.vu_canvas = tk.Canvas(sidebar, width=220, height=12, bg="#000", highlightthickness=0)
        self.vu_canvas.pack(pady=(0, 15))
        self.vu_bar = self.vu_canvas.create_rectangle(0, 0, 0, 12, fill="#00ffcc", outline="")

        self.btn_rec = self.create_btn(sidebar, "⏺ EMPEZAR GRABAR", "#cc0000", self.start_recording)
        self.btn_pause = self.create_btn(sidebar, "⏸ PAUSAR / REANUDAR", "#333", self.pause_recording, state="disabled")
        self.btn_stop = self.create_btn(sidebar, "💾 FINALIZAR", "#1b5e20", self.stop_recording, state="disabled")
        
        tk.Frame(sidebar, height=2, bg="#333").pack(fill=tk.X, pady=15)

        tk.Label(sidebar, text="EDICIÓN", bg="#151515", fg="#888", font=("Arial", 8, "bold")).pack(anchor=tk.W)
        self.btn_play_all = self.create_btn(sidebar, "▶ ESCUCHAR TODO", "#4527a0", self.play_audio)
        self.btn_play_sel = self.create_btn(sidebar, "👂 ESCUCHAR SELECCIÓN", "#673ab7", self.play_selection)
        self.btn_cut = self.create_btn(sidebar, "✂ CORTAR SELECCIÓN", "#0277bd", self.cut_selection)
        
        tk.Label(sidebar, text="ZOOM: Ctrl + Rueda Ratón", bg="#151515", fg="#555", font=("Arial", 7)).pack(side=tk.BOTTOM, pady=5)
        self.status_label = tk.Label(sidebar, text="ESTADO: LISTO", bg="#151515", fg="#00ffcc", font=("Arial", 8, "bold"))
        self.status_label.pack(side=tk.BOTTOM, pady=10)

        # --- ÁREA PRINCIPAL ---
        main_area = tk.Frame(self.root, bg="#0a0a0a", padx=15, pady=15)
        main_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        header = tk.Frame(main_area, bg="#0a0a0a")
        header.pack(fill=tk.X)
        tk.Label(header, text="GUION", bg="#0a0a0a", fg="white", font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        tk.Button(header, text="📂 ABRIR DOC", bg="#222", fg="white", font=("Arial", 8), command=self.import_file).pack(side=tk.RIGHT)

        self.txt_guion = scrolledtext.ScrolledText(main_area, bg="#121212", fg="#aaa", height=18, font=("Arial", 12), borderwidth=0, insertbackground="white")
        self.txt_guion.pack(fill=tk.BOTH, expand=True, pady=10)

        # CANVAS DE ONDA CON ZOOM Y SCROLL
        wave_container = tk.Frame(main_area, bg="#000", highlightthickness=1, highlightbackground="#222")
        wave_container.pack(fill=tk.X, pady=5)

        self.wave_canvas = tk.Canvas(wave_container, bg="#000", height=120, highlightthickness=0)
        self.wave_canvas.pack(side=tk.TOP, fill=tk.X)

        self.hbar = tk.Scrollbar(wave_container, orient=tk.HORIZONTAL, command=self.wave_canvas.xview)
        self.hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.wave_canvas.config(xscrollcommand=self.hbar.set)
        
        # Eventos de Ratón y Touchpad
        self.wave_canvas.bind("<ButtonPress-1>", self.on_click)
        self.wave_canvas.bind("<B1-Motion>", self.on_drag)
        self.wave_canvas.bind("<MouseWheel>", self.handle_mouse_wheel) # Windows/macOS
        self.wave_canvas.bind("<Button-4>", self.handle_mouse_wheel)    # Linux scroll up
        self.wave_canvas.bind("<Button-5>", self.handle_mouse_wheel)    # Linux scroll down

    def create_btn(self, parent, text, color, cmd, state="normal"):
        btn = tk.Button(parent, text=text, bg=color, fg="white", borderwidth=0, height=2, font=("Arial", 8, "bold"), command=cmd, state=state, cursor="hand2")
        btn.pack(fill=tk.X, pady=3)
        return btn

    def get_devices(self):
        return [f"{i}: {self.p.get_device_info_by_index(i)['name'][:25]}" for i in range(self.p.get_device_count()) if self.p.get_device_info_by_index(i)['maxInputChannels'] > 0]

    def handle_mouse_wheel(self, event):
        # Detectar si se presiona Ctrl para Zoom
        if event.state & 0x0004: # 0x0004 es la máscara para la tecla Control
            if event.delta > 0 or event.num == 4: # Scroll Arriba
                self.zoom_level = min(800, self.zoom_level + 10)
            else: # Scroll Abajo
                self.zoom_level = max(10, self.zoom_level - 10)
            self.draw_waveform()
        else:
            # Scroll horizontal normal
            if event.delta > 0 or event.num == 4:
                self.wave_canvas.xview_scroll(-1, "units")
            else:
                self.wave_canvas.xview_scroll(1, "units")

    def draw_waveform(self):
        self.wave_canvas.delete("wave")
        if not self.frames: return
        
        audio_data = np.frombuffer(b''.join(self.frames), dtype=np.int16)
        h = self.wave_canvas.winfo_height()
        mid = h / 2
        
        total_seconds = len(audio_data) / self.rate
        total_width = int(total_seconds * self.zoom_level)
        total_width = max(total_width, self.wave_canvas.winfo_width())
        
        self.wave_canvas.config(scrollregion=(0, 0, total_width, h))
        
        step = len(audio_data) // total_width if len(audio_data) > total_width else 1
        resampled = np.abs(audio_data[::step])
        
        # Dibujo optimizado
        for x, val in enumerate(resampled):
            if x > total_width: break
            norm_h = (val / 32768) * h * 0.8
            self.wave_canvas.create_line(x, mid - norm_h/2, x, mid + norm_h/2, fill="#00ffcc", tags="wave")

    # --- REPRODUCCIÓN (SIN BUGS) ---
    def play_audio(self):
        self._start_playback_thread(0, len(self.frames))

    def play_selection(self):
        if not self.frames or self.selection_start is None: return
        s = self.get_frame_index(min(self.selection_start, self.selection_end))
        e = self.get_frame_index(max(self.selection_start, self.selection_end))
        self._start_playback_thread(s, e)

    def _start_playback_thread(self, s, e):
        # Si ya hay un hilo reproduciendo, lo ignoramos o lo detenemos
        if self.audio_thread and self.audio_thread.is_alive():
            self.status_label.config(text="YA EN REPRODUCCIÓN", fg="orange")
            return
        
        self.audio_thread = threading.Thread(target=self._play_logic, args=(s, e), daemon=True)
        self.audio_thread.start()

    def _play_logic(self, start_idx, end_idx):
        if start_idx >= end_idx: return
        self.status_label.config(text="REPRODUCIENDO...")
        try:
            stream = self.p.open(format=self.format, channels=self.channels, rate=self.rate, output=True)
            segment = self.frames[start_idx:end_idx]
            stream.write(b''.join(segment))
            stream.stop_stream()
            stream.close()
        except Exception as err:
            print(f"Error reproducción: {err}")
        self.status_label.config(text="ESTADO: LISTO", fg="#00ffcc")

    # --- OTROS MÉTODOS ---
    def get_frame_index(self, canvas_x):
        total_width = float(self.wave_canvas.cget("scrollregion").split(" ")[2])
        percent = canvas_x / total_width
        return int(percent * len(self.frames))

    def on_click(self, event):
        self.selection_start = self.wave_canvas.canvasx(event.x)
        self.wave_canvas.delete("select")

    def on_drag(self, event):
        self.selection_end = self.wave_canvas.canvasx(event.x)
        self.wave_canvas.delete("select")
        self.wave_canvas.create_rectangle(self.selection_start, 0, self.selection_end, 120, 
                                          fill="#fb8c00", stipple="gray25", outline="", tags="select")

    def cut_selection(self):
        if not self.frames or self.selection_start is None: return
        s = self.get_frame_index(min(self.selection_start, self.selection_end))
        e = self.get_frame_index(max(self.selection_start, self.selection_end))
        del self.frames[s:e]
        self.selection_start = self.selection_end = None
        self.wave_canvas.delete("select")
        self.draw_waveform()

    def start_recording(self):
        self.is_recording, self.is_paused, self.frames = True, False, []
        self.btn_rec.config(state="disabled"); self.btn_pause.config(state="normal"); self.btn_stop.config(state="normal")
        threading.Thread(target=self.record_loop, daemon=True).start()

    def record_loop(self):
        try:
            device_idx = int(self.device_combo.get().split(":")[0])
            stream = self.p.open(format=self.format, channels=self.channels, rate=self.rate, 
                                 input=True, input_device_index=device_idx, frames_per_buffer=self.chunk)
            while self.is_recording:
                data = stream.read(self.chunk, exception_on_overflow=False)
                audio_np = np.frombuffer(data, dtype=np.int16)
                self.current_volume = np.abs(audio_np).mean()
                if not self.is_paused: self.frames.append(data)
            stream.stop_stream(); stream.close()
        except: self.is_recording = False

    def main_loop(self):
        vu_width = min(int((self.current_volume / 4000) * 220), 220)
        self.vu_canvas.coords(self.vu_bar, 0, 0, vu_width, 15)
        if self.is_recording and not self.is_paused:
            self.draw_waveform()
            self.wave_canvas.xview_moveto(1.0)
        self.root.after(100, self.main_loop)

    def import_file(self):
        path = filedialog.askopenfilename(filetypes=[("Documentos", "*.pdf *.docx")])
        if not path: return
        text = ""
        try:
            if path.endswith(".pdf"):
                with open(path, "rb") as f:
                    pdf = PyPDF2.PdfReader(f)
                    text = "".join([p.extract_text() for p in pdf.pages])
            elif path.endswith(".docx"):
                doc = Document(path)
                text = "\n".join([p.text for p in doc.paragraphs])
            self.txt_guion.delete(1.0, tk.END); self.txt_guion.insert(tk.END, text)
        except: pass

    def pause_recording(self):
        self.is_paused = not self.is_paused
        self.btn_pause.config(text="▶ REANUDAR" if self.is_paused else "⏸ PAUSAR")
        if self.is_paused: self.draw_waveform()

    def stop_recording(self):
        self.is_recording = False
        path = filedialog.asksaveasfilename(defaultextension=".wav")
        if path:
            with wave.open(path, 'wb') as wf:
                wf.setnchannels(self.channels); wf.setsampwidth(self.p.get_sample_size(self.format))
                wf.setframerate(self.rate); wf.writeframes(b''.join(self.frames))
        self.btn_rec.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk(); app = AudioStudioFinalTouch(root); root.mainloop()