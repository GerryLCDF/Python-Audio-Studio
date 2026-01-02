import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import pyaudio
import wave
import threading
import numpy as np
import PyPDF2
from docx import Document
import time

class AudioStudioPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Audio Studio - Streamlined Edition")
        self.root.geometry("1150x770")
        self.root.configure(bg="#0a0a0a")

        # Configuración de Audio
        self.chunk, self.format, self.channels, self.rate = 1024, pyaudio.paInt16, 1, 44100
        self.p = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = False
        self.is_paused = False
        self.current_volume = 0
        
        # Pilas para Historial
        self.undo_stack = []
        self.redo_stack = []
        
        # Lógica de Reproducción
        self.audio_thread = None
        self.playback_active = False 
        
        # Variables de Zoom y Selección
        self.zoom_level = 50
        self.selection_start = None
        self.selection_end = None

        self.setup_ui()
        self.setup_shortcuts()
        self.main_loop()

    def setup_ui(self):
        # --- SIDEBAR ---
        sidebar = tk.Frame(self.root, bg="#151515", padx=20, pady=10)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        self.time_label = tk.Label(sidebar, text="00:00:00", bg="#151515", fg="#00ffcc", font=("Courier New", 24, "bold"))
        self.time_label.pack(pady=(10, 15))

        tk.Label(sidebar, text="MICRÓFONO", bg="#151515", fg="#888", font=("Arial", 8, "bold")).pack(anchor=tk.W)
        self.device_combo = ttk.Combobox(sidebar, values=self.get_devices(), width=30, state="readonly")
        if self.device_combo['values']: self.device_combo.current(0)
        self.device_combo.pack(pady=(5, 15))

        self.vu_canvas = tk.Canvas(sidebar, width=220, height=12, bg="#000", highlightthickness=0)
        self.vu_canvas.pack(pady=(0, 15))
        self.vu_bar = self.vu_canvas.create_rectangle(0, 0, 0, 12, fill="#00ffcc", outline="")

        # BOTONES CONSOLIDADOS
        self.btn_main_rec = self.create_btn(sidebar, "⏺ GRABAR", "#cc0000", self.toggle_recording)
        self.btn_save = self.create_btn(sidebar, "💾 GUARDAR", "#1b5e20", self.stop_and_save, state="disabled")
        
        tk.Frame(sidebar, height=2, bg="#333").pack(fill=tk.X, pady=15)

        self.btn_smart_play = self.create_btn(sidebar, "▶ PLAY (Espacio)", "#ff00ff", self.smart_play)
        self.btn_cut = self.create_btn(sidebar, "✂ CORTAR (Backspace)", "#0277bd", self.cut_selection)
        
        self.status_label = tk.Label(sidebar, text="ESTADO: LISTO", bg="#151515", fg="#00ffcc", font=("Arial", 8, "bold"))
        self.status_label.pack(side=tk.BOTTOM, pady=10)

        # --- ÁREA PRINCIPAL ---
        main_area = tk.Frame(self.root, bg="#0a0a0a", padx=15, pady=15)
        main_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        header = tk.Frame(main_area, bg="#0a0a0a")
        header.pack(fill=tk.X)
        tk.Label(header, text="GUION", bg="#0a0a0a", fg="white", font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        tk.Button(header, text="📂 ABRIR DOC", bg="#222", fg="white", font=("Arial", 8), command=self.import_file).pack(side=tk.RIGHT)

        self.txt_guion = scrolledtext.ScrolledText(main_area, bg="#121212", fg="#aaa", height=18, font=("Arial", 14), borderwidth=0, insertbackground="white")
        self.txt_guion.pack(fill=tk.BOTH, expand=True, pady=10)

        wave_container = tk.Frame(main_area, bg="#000", highlightthickness=1, highlightbackground="#222")
        wave_container.pack(fill=tk.X, pady=5)
        self.wave_canvas = tk.Canvas(wave_container, bg="#000", height=120, highlightthickness=0)
        self.wave_canvas.pack(side=tk.TOP, fill=tk.X)
        self.hbar = tk.Scrollbar(wave_container, orient=tk.HORIZONTAL, command=self.wave_canvas.xview)
        self.hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.wave_canvas.config(xscrollcommand=self.hbar.set)
        
        self.wave_canvas.bind("<ButtonPress-1>", self.on_click)
        self.wave_canvas.bind("<B1-Motion>", self.on_drag)
        self.wave_canvas.bind("<MouseWheel>", self.handle_mouse_wheel)

    def setup_shortcuts(self):
        self.root.bind("<BackSpace>", lambda e: self.cut_selection())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<space>", self.handle_space)

    def toggle_recording(self):
        """Lógica de botón único: Graba o Pausa"""
        if not self.is_recording:
            # Iniciar nueva grabación o reanudar
            if not self.frames: # Nueva grabación
                self.frames = []
                self.is_recording = True
                self.is_paused = False
                threading.Thread(target=self.record_loop, daemon=True).start()
            else: # Reanudar de pausa
                self.is_recording = True
                self.is_paused = False
            
            self.btn_main_rec.config(text="⏸ PAUSA", bg="#444")
            self.btn_save.config(state="normal")
            self.status_label.config(text="ESTADO: GRABANDO")
        else:
            # Pausar grabación
            self.is_recording = False
            self.is_paused = True
            self.btn_main_rec.config(text="⏺ GRABAR", bg="#cc0000")
            self.status_label.config(text="ESTADO: PAUSADO")
            self.current_volume = 0

    def stop_and_save(self):
        """Finaliza sesión y guarda archivo"""
        self.is_recording = False
        self.is_paused = False
        self.current_volume = 0
        path = filedialog.asksaveasfilename(defaultextension=".wav")
        if path:
            with wave.open(path, 'wb') as wf:
                wf.setnchannels(self.channels); wf.setsampwidth(self.p.get_sample_size(self.format))
                wf.setframerate(self.rate); wf.writeframes(b''.join(self.frames))
            # Resetear para nueva sesión si se desea
            self.frames = []
            self.update_timer()
            self.draw_waveform()
            self.btn_save.config(state="disabled")
            self.btn_main_rec.config(text="⏺ GRABAR", bg="#cc0000")
            self.status_label.config(text="ESTADO: GUARDADO")

    def handle_space(self, event):
        if self.root.focus_get() == self.txt_guion: return
        self.smart_play()

    def smart_play(self):
        if self.playback_active:
            self.playback_active = False
            return
        if not self.frames or self.is_recording: return

        if self.selection_start is not None and self.selection_end is not None:
            s = self.get_frame_index(min(self.selection_start, self.selection_end))
            e = self.get_frame_index(max(self.selection_start, self.selection_end))
            self._start_playback_thread(s, e)
        else:
            self._start_playback_thread(0, len(self.frames))

    def _start_playback_thread(self, s, e):
        self.playback_active = True
        threading.Thread(target=self._play_logic, args=(s, e), daemon=True).start()

    def _play_logic(self, start_idx, end_idx):
        try:
            stream = self.p.open(format=self.format, channels=self.channels, rate=self.rate, output=True)
            for i in range(start_idx, end_idx):
                if not self.playback_active: break
                stream.write(self.frames[i])
            stream.stop_stream(); stream.close()
        except: pass
        self.playback_active = False

    def draw_waveform(self):
        self.wave_canvas.delete("wave")
        if not self.frames: return
        audio_data = np.frombuffer(b''.join(self.frames), dtype=np.int16)
        h = self.wave_canvas.winfo_height()
        tw = max(int((len(audio_data) / self.rate) * self.zoom_level), self.wave_canvas.winfo_width())
        self.wave_canvas.config(scrollregion=(0, 0, tw, h))
        step = max(1, len(audio_data) // tw)
        resampled = np.abs(audio_data[::step])
        for x, val in enumerate(resampled[:tw]):
            nh = (val / 32768) * h * 0.8
            self.wave_canvas.create_line(x, h/2 - nh/2, x, h/2 + nh/2, fill="#00ffcc", tags="wave")

    def on_click(self, event):
        self.selection_start = self.wave_canvas.canvasx(event.x)
        self.selection_end = None
        self.wave_canvas.delete("select")

    def on_drag(self, event):
        self.selection_end = self.wave_canvas.canvasx(event.x)
        self.wave_canvas.delete("select")
        self.wave_canvas.create_rectangle(self.selection_start, 0, self.selection_end, 120, fill="#fb8c00", stipple="gray25", outline="", tags="select")

    def get_frame_index(self, cx):
        reg = self.wave_canvas.cget("scrollregion").split()
        if not reg: return 0
        return int((cx / float(reg[2])) * len(self.frames))

    def create_btn(self, p, t, c, cmd, state="normal"):
        btn = tk.Button(p, text=t, bg=c, fg="white", borderwidth=0, height=2, font=("Arial", 8, "bold"), command=cmd, state=state)
        btn.pack(fill=tk.X, pady=3); return btn

    def get_devices(self):
        return [f"{i}: {self.p.get_device_info_by_index(i)['name'][:25]}" for i in range(self.p.get_device_count()) if self.p.get_device_info_by_index(i)['maxInputChannels'] > 0]

    def update_timer(self):
        self.time_label.config(text=time.strftime('%H:%M:%S', time.gmtime(len(self.frames)*self.chunk/self.rate)))

    def handle_mouse_wheel(self, event):
        if event.state & 0x0004:
            self.zoom_level = min(800, max(10, self.zoom_level + (10 if event.delta > 0 else -10)))
            self.draw_waveform()
        else: self.wave_canvas.xview_scroll(int(-1*(event.delta/120)), "units")

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(list(self.frames)); self.frames = self.undo_stack.pop()
            self.draw_waveform(); self.update_timer()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(list(self.frames)); self.frames = self.redo_stack.pop()
            self.draw_waveform(); self.update_timer()

    def cut_selection(self):
        if not self.frames or self.selection_start is None or self.selection_end is None: return
        self.undo_stack.append(list(self.frames)); self.redo_stack.clear()
        s, e = self.get_frame_index(min(self.selection_start, self.selection_end)), self.get_frame_index(max(self.selection_start, self.selection_end))
        del self.frames[s:e]; self.selection_start = self.selection_end = None
        self.draw_waveform(); self.update_timer()

    def record_loop(self):
        try:
            stream = self.p.open(format=self.format, channels=self.channels, rate=self.rate, input=True, input_device_index=int(self.device_combo.get().split(":")[0]), frames_per_buffer=self.chunk)
            while True: # El loop vive mientras la app esté abierta, controlamos con flags
                if self.is_recording and not self.is_paused:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    self.current_volume = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
                    self.frames.append(data)
                elif not self.is_recording and not self.is_paused and not self.frames: # Sesión cerrada
                    break
                else: time.sleep(0.01)
            stream.stop_stream(); stream.close()
        except: self.is_recording = False

    def main_loop(self):
        vw = min(int((self.current_volume / 4000) * 220), 220)
        self.vu_canvas.coords(self.vu_bar, 0, 0, vw, 15)
        if self.is_recording and not self.is_paused:
            self.draw_waveform(); self.wave_canvas.xview_moveto(1.0); self.update_timer()
        self.root.after(100, self.main_loop)

    def import_file(self):
        p = filedialog.askopenfilename(filetypes=[("Documentos", "*.pdf *.docx")])
        if not p: return
        try:
            if p.endswith(".pdf"): self.txt_guion.delete(1.0, tk.END); self.txt_guion.insert(tk.END, "".join([page.extract_text() for page in PyPDF2.PdfReader(p).pages]))
            else: self.txt_guion.delete(1.0, tk.END); self.txt_guion.insert(tk.END, "\n".join([pa.text for pa in Document(p).paragraphs]))
        except: pass

if __name__ == "__main__":
    root = tk.Tk(); app = AudioStudioPro(root); root.mainloop()
